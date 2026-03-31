from typing import Optional

import pandas as pd
import pandas_ta as ta  # noqa
import streamlit as st

from .strategies import identify_fvg_vectorized, identify_trading_signals


# --- 1. 基础指标原子函数 (Atomic Functions) ---
def add_technical_indicators(
    df: pd.DataFrame, rsi_len=14, bb_len=20
) -> pd.DataFrame:
    """纯计算：负责把常用技术指标挂载到 DF 上"""
    if df.empty:
        return df

    # 使用 pandas_ta 批量计算
    df.ta.rsi(length=rsi_len, append=True)
    df.ta.macd(append=True)
    df.ta.bbands(length=bb_len, std=2, append=True)
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
        df = add_technical_indicators(df, rsi_len=kwargs.get("rsi_length", 14))
        df = add_volume_metrics(df)

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
