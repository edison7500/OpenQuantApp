import datetime

import pandas as pd
import pandas_ta as ta  # noqa
import streamlit as st

from database.connections.arcticdb_conn import ArcticDBConnection


@st.cache_data(ttl=3600)
def load_and_process_data_with_range(
    symbol, start_date, end_date, timeframe="D", rsi_length=14
):
    """
    带时间范围的高效数据拉取与指标计算
    """
    ac = st.connection("arcticdb", type=ArcticDBConnection)
    lib = ac.get_library(timeframe)  # 沿用之前的数据库连接函数

    # 1. 计算缓冲期 (Buffer)
    # 假设周末/节假日停盘，往前推 rsi_length * 2 天作为缓冲，确保指标能在 start_date 算出来
    buffer_days = rsi_length * 2
    fetch_start = start_date - datetime.timedelta(days=buffer_days)

    try:
        # 2. 核心：使用 ArcticDB 的 date_range 过滤
        # 这会让 ArcticDB 只从底层存储下载该时间段的 Chunks，极大节省网络和内存
        # 注意将 date 转换为 datetime，以匹配数据库索引
        query_start = pd.to_datetime(fetch_start).tz_localize("UTC")
        query_end = pd.to_datetime(end_date).tz_localize("UTC")

        item = lib.read(symbol, date_range=(query_start, query_end))
        df = item.data
    except Exception as e:  # noqa
        return pd.DataFrame()

    if df.empty:
        return df

    # --- 核心：批量计算技术指标 ---
    # 1. RSI
    df.ta.rsi(length=14, append=True)

    # 2. MACD (默认参数: fast=12, slow=26, signal=9)
    # 这会生成类似 MACD_12_26_9, MACDh_12_26_9 (柱状图), MACDs_12_26_9 (信号线) 的列
    df.ta.macd(append=True)

    # 3. 布林带 Bollinger Bands (默认参数: length=5, std=2)
    # 这会生成 BBL_5_2.0 (下轨), BBM_5_2.0 (中轨), BBU_5_2.0 (上轨)
    df.ta.bbands(length=20, std=2, append=True)

    # 动态获取 MACD 柱状图的列名 (pandas_ta 生成的通常带参数后缀)
    macd_hist_col = [c for c in df.columns if c.startswith("MACDh_")][0]

    # 计算金叉 (Golden Cross) 和死叉 (Death Cross)
    # 使用 shift(1) 获取前一天的值，这是一种非常地道的 pandas 写法
    df["Buy_Signal"] = (df[macd_hist_col] > 0) & (
        df[macd_hist_col].shift(1) <= 0
    )
    df["Sell_Signal"] = (df[macd_hist_col] < 0) & (
        df[macd_hist_col].shift(1) >= 0
    )

    # 4. 截断数据：计算完毕后，把缓冲期的数据丢掉，只保留用户真正想看的部分
    # 确保图表的 X 轴完全贴合用户的选择
    mask = (
        df.index.tz_convert("UTC")
        >= pd.to_datetime(start_date).tz_localize("UTC")
    ) & (
        df.index.tz_convert("UTC")
        <= pd.to_datetime(end_date).tz_localize("UTC")
    )
    df_final = df.loc[mask]

    return df_final


@st.cache_data(ttl=300)
def calculate_drawdown(strategy_returns_series):
    """
    输入：策略收益率序列 (Returns)
    输出：回撤百分比序列
    """
    # 1. 计算累计净值 (Cumulative Returns)
    cumulative = (1 + strategy_returns_series).cumprod()

    # 2. 计算历史最高滚动净值 (Running Maximum)
    running_max = cumulative.cummax()

    # 3. 计算回撤 (当前净值 / 历史最高 - 1)
    drawdown = (cumulative / running_max) - 1

    return drawdown


def add_breakout_signals(df, rvol_threshold=2.0, price_change_threshold=0.03):
    """
    识别爆量突破信号
    """
    # 计算当日涨幅
    df["pct_change"] = df["Close"].pct_change(fill_method=None)

    # 定义突破信号：RVOL 达标 且 涨幅达标
    df["breakout_signal"] = (df["rvol"] > rvol_threshold) & (
        df["pct_change"] > price_change_threshold
    )

    return df


@st.cache_data(ttl=300)
def process_data_with_rvol(df, length=10):
    """
    使用 pandas_ta 和原生 pandas 計算 RVOL
    """
    # 確保數據按時間排序
    df = df.sort_index()

    # 計算過去 N 期的平均成交量 (不包含當前這根)
    df["avg_vol"] = df["Volume"].shift(1).rolling(window=length).mean()

    # 計算 RVOL
    df["rvol"] = df["Volume"] / df["avg_vol"]

    # 處理空值 (前 N 期沒有足夠數據)
    df["rvol"] = df["rvol"].fillna(0)

    df = add_breakout_signals(df)

    return df


def identify_fvg(df):
    # 初始化缺口列
    df["fvg_top"] = None
    df["fvg_bottom"] = None
    df["fvg_type"] = 0  # 1 为看涨, -1 为看跌

    for i in range(2, len(df)):
        # 看涨 FVG 逻辑
        if df["low"].iloc[i] > df["high"].iloc[i - 2]:
            df.at[df.index[i - 1], "fvg_type"] = 1
            df.at[df.index[i - 1], "fvg_top"] = df["low"].iloc[i]
            df.at[df.index[i - 1], "fvg_bottom"] = df["high"].iloc[i - 2]

        # 看跌 FVG 逻辑
        elif df["high"].iloc[i] < df["low"].iloc[i - 2]:
            df.at[df.index[i - 1], "fvg_type"] = -1
            df.at[df.index[i - 1], "fvg_top"] = df["low"].iloc[i - 2]
            df.at[df.index[i - 1], "fvg_bottom"] = df["high"].iloc[i]

    return df
