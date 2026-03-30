import datetime

import pandas as pd
import pandas_ta as ta  # noqa
import pytz
import streamlit as st
import yfinance as yf

import chart
from dash.components.fragments import (
    news_sidebar_fragment,
    symbolmeta_sidebar_fragment,
)
from database.resource import get_arctic_library, get_symbol_meta, get_symbols
from indicators import (
    calculate_drawdown,
    load_and_process_data_with_range,
    process_data_with_rvol,
)

# from pprint import pprint


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


# ==========================================
# 4. Streamlit UI 布局层
# ==========================================
def main():
    st.set_page_config(
        page_title="Stock Dashboard",
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
                (
                    tab_rvol,
                    tab_rsi,
                    tab_macd,
                    tab_bbands,
                    tab_drawdown,
                    tab_trading_terminal,
                ) = st.tabs(
                    [
                        "RVOL 视图",
                        "📊 RSI 指标",
                        "📈 MACD 指标",
                        "🌀 布林带通道",
                        "📉 风险回撤",
                        "核心策略视图",
                    ],
                    width="stretch",
                    # key="chart",
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
                with tab_trading_terminal:
                    fig_trading_terminal = chart.plot_trading_terminal(
                        hist, symbol
                    )
                    st.plotly_chart(
                        fig_trading_terminal,
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
