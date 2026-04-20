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
    df: pd.DataFrame, rsi_len=14, bb_len=20, sma_len=20, ema_len=50, wma_len=20
) -> pd.DataFrame:
    """纯计算：负责把常用技术指标挂载到 DF 上"""
    if df.empty:
        return df

    # 1. 趨勢指標 (與價格同量綱，用於主圖)
    df.ta.sma(length=sma_len, append=True)
    df.ta.ema(length=ema_len, append=True)
    df.ta.wma(length=wma_len, append=True)
    df.ta.bbands(length=bb_len, std=2, append=True)

    # 2. 波動率 & 動量指標 (不同量綱，用於副圖)
    # pandas_ta.bbands 會生成 BBL, BBM, BBU, BBB, BBP
    df.ta.rsi(length=rsi_len, append=True)
    df.ta.cci(length=rsi_len, append=True)
    df.ta.macd(append=True)

    # KDJ Calculation
    k_period = 9
    low_min = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    rsv = (df["Close"] - low_min) / (high_max - low_min) * 100

    df["K"] = rsv.ewm(com=2).mean()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]

    return df


def add_volume_metrics(df: pd.DataFrame, length=10) -> pd.DataFrame:
    """纯计算：RVOL 等成交量指标"""
    df["avg_vol"] = df["Volume"].shift(1).rolling(window=length).mean()
    df["rvol"] = (df["Volume"] / df["avg_vol"]).fillna(0)
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
        df = add_volume_metrics(df)

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
