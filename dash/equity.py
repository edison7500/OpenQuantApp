import datetime
from pprint import pprint
from typing import List

import pandas as pd
import pandas_ta as ta  # noqa
import pytz
import streamlit as st
import yfinance as yf
from sqlmodel import select

import chart
from api.fetch_news import fetch_and_analyze
from database.connections.arcticdb_conn import ArcticDBConnection
from database.models import SymbolMeta
from indicators import calculate_drawdown, load_and_process_data_with_range
from utils.human_readable import format_human_readable, format_percentage


# ==========================================
# 1. 数据库连接层 (全局缓存)
# ==========================================
@st.cache_resource
def get_arctic_library(timeframe: str = "D"):
    """Initialize and return ArcticDB connection"""
    ac = st.connection("arcticdb", type=ArcticDBConnection)
    lib = ac.get_library(timeframe, create_if_missing=True)
    return lib


@st.cache_resource
def get_sql_connection():
    conn = st.connection("quant_db", type="sql")
    return conn


@st.cache_data(ttl=3600)
def get_symbols() -> List[str]:
    # lib = get_arctic_library(LIBRARY_NAME)
    # portfolio = lib.list_symbols()
    # portfolio.sort()
    # return portfolio
    conn = get_sql_connection()
    with conn.session as session:
        statement = (
            select(SymbolMeta.symbol)
            .where(SymbolMeta.asset_type == "Equity")
            .order_by(SymbolMeta.symbol)
        )
        return session.execute(statement).scalars().all()


def get_symbol_meta(symbol: str) -> SymbolMeta:
    conn = get_sql_connection()
    with conn.session as session:
        statement = select(SymbolMeta).where(SymbolMeta.symbol == symbol)
        obj: SymbolMeta = session.execute(statement).scalars().first()

        return obj


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
    lib = get_arctic_library()
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


# def switch_tab(tab):
#     st.session_state.chart = tab


# def on_tab_change():
#     st.toast(f"You opened the {st.session_state.chart} tab.")


@st.fragment
def symbolmeta_sidebar_fragment(symbol: str):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    # pprint(info, indent=2)
    m1, m2 = st.columns(2)
    m1.metric(
        "当前价格",
        f"${info['currentPrice']}",
        # f"+{info['regularMarketChangePercent']:.2}%",
        delta=format_percentage(info["regularMarketChangePercent"]),
    )
    m2.metric("成交量", format_human_readable(info["volume"]))

    m3, m4 = st.columns(2)
    m3.metric("总市值", format_human_readable(info["marketCap"]))
    m4.metric("波动率", "1.24%")  # 示例


@st.fragment
def news_sidebar_fragment(symbol: str):
    st.subheader(f"📰 {symbol} 實時新聞")

    # 局部刷新按鈕
    if st.button("🔄 刷新新聞 (局部)"):
        st.cache_data.clear()  # 清除緩存以獲取最新
        # fragment 會自動處理局部重新渲染

    with st.spinner("讀取中..."):
        # df = get_cached_news(symbol)
        df = fetch_and_analyze(symbol)

    if not df.empty:
        # 限制顯示數量以適應側邊欄高度
        # for _, row in df.head(10).iterrows():
        #     with st.container(border=True):
        #         st.markdown(f"**{row['headline']}**")
        #         st.caption(
        #             f"{row['datetime'].strftime('%m-%d %H:%M')} | {row['source']}"
        #         )
        #         st.markdown(f"[閱讀原文]({row['url']})")
        # 情感分布小统计
        sentiment_counts = df["sentiment_label"].value_counts()
        st.caption("过去7天情感分布")
        st.bar_chart(sentiment_counts, horizontal=True, height=150)

        st.divider()

        # 新闻列表渲染
        for _, row in df.head(12).iterrows():
            with st.container(border=True):
                # 用不同颜色显示标签
                st.markdown(
                    f"**{row['sentiment_label']}** (得分: {row['sentiment_score']:.2f})"
                )
                st.markdown(f"**{row['headline']}**")
                st.caption(
                    f"{row['source']} | {row['datetime'].strftime('%Y-%m-%d')}"
                )
                st.link_button("查看全文", row["url"], icon="🔗")
    else:
        st.info("暫無新聞")


# ==========================================
# 4. Streamlit UI 布局层
# ==========================================
def main():
    st.set_page_config(
        page_title="Quant Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # st.title("📈 量化投研 Dashboard")

    # 侧边栏交互
    with st.sidebar:
        st.header("参数设置")

        portfolio = get_symbols()
        if "symbol" not in st.session_state:
            st.session_state.setdefault("symbol", portfolio[0])

        symbol = st.selectbox(
            "选择分析标的",
            options=portfolio,
            key="symbol",
        )

        # --- 新增：日期范围选择器 ---
        now = datetime.datetime.now(tz=pytz.UTC)
        default_start = now - datetime.timedelta(days=180)  # 默认看过去半年

        # date_input 允许传入一个 tuple 来选择区间
        date_selection = st.date_input(
            "选择时间范围",
            value=(default_start, now),
            max_value=now + datetime.timedelta(days=1),
        )

        timeframe = st.select_slider(
            "TimeFrame",
            options=[
                "1m",
                "1h",
                "D",
            ],
            value="D",
        )

        rsi_length = st.slider("RSI 周期", min_value=5, max_value=30, value=14)

        # auto_refresh = st.toggle("开启自动刷新", value=False)

        # 添加一个强制刷新按钮来清除缓存
        if st.button("🔄 强制刷新数据"):
            update_database(symbol)
            get_symbols.clear()
            load_and_process_data_with_range.clear()
            calculate_drawdown.clear()

    col_main, col_news = st.columns([3, 1])

    with col_main:
        # --- 确保用户选择了完整的起始和结束时间 ---
        if symbol and len(date_selection) == 2:
            start_date, end_date = date_selection

            with st.spinner(f"正在从 ArcticDB 加载 {symbol} 的数据..."):
                # hist = load_and_process_data(symbol, rsi_length)
                hist = load_and_process_data_with_range(
                    symbol, start_date, end_date, timeframe, rsi_length
                )
            if not hist.empty:
                # --- Tabs 布局 ---
                tab_rvol, tab_rsi, tab_macd, tab_bbands, tab_drawdown = (
                    st.tabs(
                        [
                            "RVOL 视图",
                            "📊 RSI 指标",
                            "📈 MACD 指标",
                            "🌀 布林带通道",
                            "📉 风险回撤",
                        ],
                        width="stretch",
                        # key="chart",
                    )
                )
                with tab_rvol:
                    # current_price = hist["Close"].iloc[-1]
                    # # st.metric("当前价格 (Current Price)", f"${current_price:.2f}")
                    # tab_rvol.metric(
                    #     "当前价格 (Current Price)", f"${current_price:.2f}"
                    # )

                    hist = process_data_with_rvol(hist)
                    fig = chart.create_rvol_chart(hist, symbol)
                    st.plotly_chart(
                        fig, width="stretch", config={"displayModeBar": False}
                    )

                with tab_rsi:
                    fig_rsi = chart.create_rsi_view(hist, symbol)
                    st.plotly_chart(
                        fig_rsi,
                        width="stretch",
                        config={"displayModeBar": False},
                    )

                with tab_macd:
                    # fig_macd = chart.create_macd_view(hist, symbol)
                    fig_macd = chart.create_macd_view_with_signals(
                        hist, symbol
                    )
                    st.plotly_chart(
                        fig_macd,
                        width="stretch",
                        config={"displayModeBar": False},
                    )

                with tab_bbands:
                    fig_bbands = chart.create_bbands_view(hist, symbol)
                    st.plotly_chart(
                        fig_bbands,
                        width="stretch",
                        config={"displayModeBar": False},
                    )

                with tab_drawdown:
                    # 计算关键指标
                    drawdown_series = calculate_drawdown(
                        hist["Close"].pct_change(fill_method=None)
                    )  # 示例使用收盘价
                    max_dd = drawdown_series.min() * 100
                    current_dd = drawdown_series.iloc[-1] * 100

                    tab_drawdown.subheader("策略风险分析")
                    # 用 Streamlit Metrics 显示最大回撤
                    tab_drawdown.metric(
                        "最大回撤 (Max Drawdown)", f"{max_dd:.2f}%"
                    )
                    tab_drawdown.metric(
                        "当前回撤 (Current Drawdown)", f"{current_dd:.2f}%"
                    )

                    fig_drawdown = chart.create_drawdown_chart(hist, symbol)
                    st.plotly_chart(
                        fig_drawdown,
                        width="stretch",
                        config={"displayModeBar": False},
                    )
        else:
            # 当用户刚点选了开始日期，还没点结束日期时，给出提示
            st.info("请选择一个完整的开始和结束日期范围。")

    with col_news:
        symbol_meta = get_symbol_meta(symbol)

        # st.markdown(f"### {symbol_meta.name} 的详情")
        st.subheader(f"{symbol_meta.name} ({symbol_meta.symbol})")

        with st.spinner(f"正在加载 {symbol} 的数据..."):
            symbolmeta_sidebar_fragment(symbol)

            # st.caption("最后更新: 2026-03-24 10:00")
        st.divider()  # 视觉分割线

        # --- 下方新闻动态区 ---
        st.caption("最新市场动态")
        with st.container(height=500):  # 开启滚动模式，确保不挤占 Meta 区
            news_sidebar_fragment(symbol)


main()
