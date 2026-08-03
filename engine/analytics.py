import pandas as pd
import pandas_ta as ta  # noqa
import streamlit as st

from .strategies import identify_fvg_vectorized, identify_trading_signals


def calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算 Heikin-Ashi K线
    """
    df_ha = df.copy()

    # Close = (Open + High + Low + Close) / 4
    df_ha["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4

    # Open = (Previous HA_Open + Previous HA_Close) / 2
    # Since it's recursive, we use a loop or a specialized approach.
    # For efficiency in pandas, we can use a loop for the Open price.
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i - 1] + df_ha["HA_Close"].iloc[i - 1]) / 2)
    df_ha["HA_Open"] = ha_open

    # High = max(High, HA_Open, HA_Close)
    df_ha["HA_High"] = df_ha[["High", "HA_Open", "HA_Close"]].max(axis=1)

    # Low = min(Low, HA_Open, HA_Close)
    df_ha["HA_Low"] = df_ha[["Low", "HA_Open", "HA_Close"]].min(axis=1)

    return df_ha


# --- 1. 基础指标原子函数 (Atomic Functions) ---


def add_technical_indicators(
    df: pd.DataFrame,
    rsi_len: int = 14,
    bb_len: int = 20,
    sma_len: int = 20,
    ema_len: int = 50,
    atr_len: int = 14,
    adx_len: int = 14,
) -> pd.DataFrame:
    """纯计算：负责把常用技术指标挂载到 DF 上"""
    if df.empty:
        return df

    # 1. 趨勢指標 (與價格同量綱，用於主圖)
    df.ta.sma(length=sma_len, append=True)
    df.ta.ema(length=ema_len, append=True)
    df.ta.bbands(length=bb_len, std=2, append=True)

    # 2. 波動率、趋势强度与动量指标（不同量纲，用于副图）
    # pandas_ta.bbands 會生成 BBL, BBM, BBU, BBB, BBP
    df.ta.rsi(length=rsi_len, append=True)
    df.ta.macd(append=True)
    df.ta.atr(length=atr_len, append=True)
    df.ta.adx(length=adx_len, append=True)

    # pandas_ta 在历史长度不足时不会创建列；保留稳定 schema，让新标的
    # 至少可以展示 K 线，而不是因动态列查找失败导致整个页面报错。
    fallback_columns = {
        "SMA_": f"SMA_{sma_len}",
        "EMA_": f"EMA_{ema_len}",
        "BBL_": f"BBL_{bb_len}_2.0",
        "BBM_": f"BBM_{bb_len}_2.0",
        "BBU_": f"BBU_{bb_len}_2.0",
        "BBB_": f"BBB_{bb_len}_2.0",
        "RSI_": f"RSI_{rsi_len}",
        "MACD_": "MACD_12_26_9",
        "MACDh_": "MACDh_12_26_9",
        "MACDs_": "MACDs_12_26_9",
        "ATR": f"ATRr_{atr_len}",
        "ADX_": f"ADX_{adx_len}",
        "DMP_": f"DMP_{adx_len}",
        "DMN_": f"DMN_{adx_len}",
    }
    for prefix, column in fallback_columns.items():
        if not any(existing.startswith(prefix) for existing in df.columns):
            df[column] = float("nan")

    atr_col = next(c for c in df.columns if c.startswith("ATR"))
    adx_col = next(c for c in df.columns if c.startswith("ADX_"))
    dmp_col = next(c for c in df.columns if c.startswith("DMP_"))
    dmn_col = next(c for c in df.columns if c.startswith("DMN_"))
    df["atr_main"] = df[atr_col]
    df["atr_pct"] = (df["atr_main"] / df["Close"] * 100).where(
        df["Close"] != 0
    )
    df["adx_main"] = df[adx_col]
    df["dmp_main"] = df[dmp_col]
    df["dmn_main"] = df[dmn_col]

    return df


def add_volume_metrics(
    df: pd.DataFrame, length: int = 20, timeframe: str = "D"
) -> pd.DataFrame:
    """计算原始成交量、RVOL 与适合当前周期的 VWAP。"""
    df["avg_vol"] = df["Volume"].shift(1).rolling(window=length).mean()
    df["rvol"] = (df["Volume"] / df["avg_vol"]).where(df["avg_vol"] != 0)

    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    price_volume = typical_price * df["Volume"]
    if timeframe.lower() == "1h":
        sessions = pd.DatetimeIndex(df.index).normalize()
        cumulative_volume = df["Volume"].groupby(sessions).cumsum()
        cumulative_value = price_volume.groupby(sessions).cumsum()
        df["vwap_main"] = (cumulative_value / cumulative_volume).where(
            cumulative_volume != 0
        )
    else:
        rolling_volume = df["Volume"].rolling(length).sum()
        df["vwap_main"] = (
            price_volume.rolling(length).sum() / rolling_volume
        ).where(rolling_volume != 0)
    return df


def add_relative_strength(
    df: pd.DataFrame, benchmark_close: pd.Series | None, length: int = 20
) -> pd.DataFrame:
    """计算以 100 为起点的相对强弱线及其阶段变化。"""
    if benchmark_close is None or benchmark_close.empty:
        return df

    aligned_benchmark = benchmark_close.reindex(df.index).ffill()
    ratio = (df["Close"] / aligned_benchmark).where(aligned_benchmark != 0)
    first_valid = ratio.first_valid_index()
    if first_valid is None or ratio.loc[first_valid] == 0:
        return df

    df["relative_strength"] = ratio / ratio.loc[first_valid] * 100
    df["rs_change"] = (ratio / ratio.shift(length) - 1) * 100
    return df


# --- 2. 核心：流水线引擎 (The Engine / Pipeline) ---
class AnalyticsEngine:
    """
    虽然叫 Engine 类，但它本质上是一个 Namespace，
    负责组织流水线，支持多资产复用。
    """

    @staticmethod
    @st.cache_data(ttl=600)
    def process(
        df: pd.DataFrame,
        asset_type: str,
        include_signals: bool = False,
        **kwargs,
    ) -> pd.DataFrame:
        """
        统一入口：根据资产类型，灵活组合计算流程
        """
        if df.empty:
            return df

        # 1. 通用基础计算
        df = add_technical_indicators(
            df,
            rsi_len=kwargs.get("rsi_length", 14),
            sma_len=kwargs.get("sma_len", 20),
            ema_len=kwargs.get("ema_len", 50),
        )
        df = add_volume_metrics(
            df,
            length=kwargs.get("volume_length", 20),
            timeframe=kwargs.get("timeframe", "D"),
        )
        df = add_relative_strength(df, kwargs.get("benchmark_close"))

        # 標準化列名映射 (防止 pandas_ta 因參數不同導致列名變動)
        cols = df.columns
        df["sma_main"] = df[[c for c in cols if c.startswith("SMA_")][0]]
        df["ema_main"] = df[[c for c in cols if c.startswith("EMA_")][0]]

        # --- 自動標註金叉/死叉信號 ---
        # 金叉 (Golden Cross): SMA 從下方穿過 EMA
        df["MA_Cross_Buy"] = (df["sma_main"] > df["ema_main"]) & (
            df["sma_main"].shift(1) <= df["ema_main"].shift(1)
        )
        # 死叉 (Death Cross): SMA 從上方跌破 EMA
        df["MA_Cross_Sell"] = (df["sma_main"] < df["ema_main"]) & (
            df["sma_main"].shift(1) >= df["ema_main"].shift(1)
        )

        # 2. 资产特化逻辑 (按需扩展)
        if asset_type.lower() == "crypto":
            # 例如：加密货币可能需要额外的资金费率计算或波动率模型
            pass
        elif asset_type.lower() == "equity":
            # 例如：股票可能需要除权除息调整后的检查
            pass

        # 3. 信号流水线 (根据开关触发)
        if include_signals:
            df = identify_fvg_vectorized(df)
            df = identify_trading_signals(df)
        return df
