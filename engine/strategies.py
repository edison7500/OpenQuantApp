import pandas as pd


def identify_trading_signals(
    df: pd.DataFrame, rvol_threshold=2.0
) -> pd.DataFrame:
    """
    识别交易信号（MACD金叉/死叉、爆量突破）
    """
    # 动态获取 MACD 柱状图列名
    macd_cols = [c for c in df.columns if c.startswith("MACDh_")]
    if macd_cols:
        col = macd_cols[0]
        df["Buy_Signal"] = (df[col] > 0) & (df[col].shift(1) <= 0)  #
        df["Sell_Signal"] = (df[col] < 0) & (df[col].shift(1) >= 0)  #

    # 爆量信号
    df["pct_change"] = df["Close"].pct_change(fill_method=None)  #
    df["breakout_signal"] = (df["rvol"] > rvol_threshold) & (
        df["pct_change"] > 0.03
    )  #

    return df


def identify_fvg_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    FVG 缺口识别（向量化优化版）
    """
    # 逻辑：当前 Low > 两天前 High (看涨) 或 当前 High < 两天前 Low (看跌)
    bullish_mask = df["Low"] > df["High"].shift(2)  #
    bearish_mask = df["High"] < df["Low"].shift(2)  #

    df["fvg_type"] = 0  #
    # 使用 shift(-1) 标记在中间那根 K 线
    df.loc[bullish_mask.shift(-1).fillna(False), "fvg_type"] = 1  #
    df.loc[bearish_mask.shift(-1).fillna(False), "fvg_type"] = -1  #

    return df
