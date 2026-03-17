import datetime
import os
from typing import List

import pandas as pd
import pandas_ta as ta  # noqa
import pytz
import streamlit as st
import yfinance as yf
from arcticdb import Arctic
from dotenv import load_dotenv

import chart

load_dotenv()


DB_PATH = os.getenv("DB_PATH")
LIBRARY_NAME = os.getenv("LIBRARY_NAME")


# ==========================================
# 1. 数据库连接层 (全局缓存)
# ==========================================
@st.cache_resource
def get_arctic_library(library_name):
    """Initialize and return ArcticDB connection"""
    ac = Arctic(DB_PATH)
    lib = ac.get_library(library_name, create_if_missing=True)
    return lib


@st.cache_data(ttl=3600)
def get_symbols() -> List:
    lib = get_arctic_library(LIBRARY_NAME)
    portfolio = lib.list_symbols()
    portfolio.sort()
    return portfolio


@st.cache_data(ttl=3600)
def load_and_process_data_with_range(
    symbol, start_date, end_date, rsi_length=14
):
    """
    带时间范围的高效数据拉取与指标计算
    """
    lib = get_arctic_library(LIBRARY_NAME)  # 沿用之前的数据库连接函数

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


def update_database(symbol: str):
    lib = get_arctic_library(LIBRARY_NAME)
    ticker = yf.Ticker(symbol)

    metadata = {
        "source": "Yahoo Finance",
        "retrieval_date": pd.Timestamp.now(),
    }
    if lib.has_symbol(symbol):
        result = lib.read(symbol)
        new_data = ticker.history(period="1mo", auto_adjust=False)
        combined = pd.concat([result.data, new_data])
        filtered = combined[~combined.index.duplicated(keep="last")]
        lib.update(symbol, filtered.sort_index(), metadata=metadata)
    else:
        hist_data = ticker.history(period="5y", auto_adjust=False)
        if not hist_data.empty:
            lib.write(symbol, hist_data, metadata=metadata)


# ==========================================
# 4. Streamlit UI 布局层
# ==========================================
def main():
    st.set_page_config(
        page_title="Quant Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("📈 量化投研 Dashboard")

    # 侧边栏交互
    with st.sidebar:
        st.header("参数设置")
        # symbol = st.text_input("输入标的代码", value="AAPL")
        portfolio = get_symbols()
        symbol = st.selectbox("选择分析标的", options=portfolio, index=0)

        # --- 新增：日期范围选择器 ---
        now = datetime.datetime.now(tz=pytz.UTC)
        default_start = now - datetime.timedelta(days=180)  # 默认看过去半年

        # date_input 允许传入一个 tuple 来选择区间
        date_selection = st.date_input(
            "选择时间范围",
            value=(default_start, now),
            max_value=now + datetime.timedelta(days=1),
        )
        rsi_length = st.slider("RSI 周期", min_value=5, max_value=30, value=14)

        # 添加一个强制刷新按钮来清除缓存
        if st.button("🔄 强制刷新数据"):
            update_database(symbol.upper())
            load_and_process_data_with_range.clear()

    # col_main, col_right = st.columns([7, 3])
    # --- 确保用户选择了完整的起始和结束时间 ---
    if symbol and len(date_selection) == 2:
        start_date, end_date = date_selection

        symbol = symbol.upper()
        with st.spinner(f"正在从 ArcticDB 加载 {symbol} 的数据..."):
            # hist = load_and_process_data(symbol, rsi_length)
            hist = load_and_process_data_with_range(
                symbol, start_date, end_date, rsi_length
            )
        if not hist.empty:
            # --- Tabs 布局 ---
            tab_rvol, tab_rsi, tab_macd, tab_bbands, tab_drawdown = st.tabs(
                [
                    "RVOL 视图",
                    "📊 RSI 指标",
                    "📈 MACD 指标",
                    "🌀 布林带通道",
                    "📉 风险回撤",
                ]
            )
            with tab_rvol:
                current_price = hist["Close"].iloc[-1]
                st.metric("当前价格 (Current Price)", f"${current_price:.2f}")

                hist = process_data_with_rvol(hist)
                fig = chart.create_rvol_chart(hist, symbol)
                st.plotly_chart(
                    fig, width="stretch", config={"displayModeBar": False}
                )

            with tab_rsi:
                fig_rsi = chart.create_rsi_view(hist, symbol)
                st.plotly_chart(
                    fig_rsi, width="stretch", config={"displayModeBar": False}
                )

            with tab_macd:
                # fig_macd = chart.create_macd_view(hist, symbol)
                fig_macd = chart.create_macd_view_with_signals(hist, symbol)
                st.plotly_chart(
                    fig_macd, width="stretch", config={"displayModeBar": False}
                )

            with tab_bbands:
                fig_bbands = chart.create_bbands_view(hist, symbol)
                st.plotly_chart(
                    fig_bbands,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            with tab_drawdown:
                st.subheader("策略风险分析")
                # 计算关键指标
                drawdown_series = calculate_drawdown(
                    hist["Close"].pct_change(fill_method=None)
                )  # 示例使用收盘价
                max_dd = drawdown_series.min() * 100
                current_dd = drawdown_series.iloc[-1] * 100

                # 用 Streamlit Metrics 显示最大回撤
                st.metric("最大回撤 (Max Drawdown)", f"{max_dd:.2f}%")
                st.metric("当前回撤 (Current Drawdown)", f"{current_dd:.2f}%")

                fig_drawdown = chart.create_drawdown_chart(hist, symbol)
                st.plotly_chart(
                    fig_drawdown,
                    width="stretch",
                    config={"displayModeBar": False},
                )
    else:
        # 当用户刚点选了开始日期，还没点结束日期时，给出提示
        st.info("请选择一个完整的开始和结束日期范围。")


main()
