import datetime

import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

from database.resource import get_arctic_library, get_symbol_meta, get_symbols
from engine import calculate_drawdown, load_and_process_full_pipeline
from ui.components.analysis_tabs import render_analysis_tabs
from ui.components.fragments import (
    news_sidebar_fragment,
    symbolmeta_sidebar_fragment,
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
        page_title="Future/Option Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 侧边栏交互
    with st.sidebar:
        st.header("参数设置")

        # 尝试获取期货或期权标的
        portfolio_futures = get_symbols(asset_type="Futures") or []
        portfolio_options = get_symbols(asset_type="Option") or []
        portfolio = portfolio_futures + portfolio_options

        if not portfolio:
            st.warning("未找到期货或期权标的，请在后台添加。")
            st.stop()

        if (
            "symbol" not in st.session_state
            or st.session_state.symbol not in portfolio
        ):
            st.session_state.symbol = portfolio[0]

        symbol = st.selectbox(
            "选择分析标的",
            options=portfolio,
            key="symbol",
        )

        # 自动推断 asset_type
        current_meta = get_symbol_meta(symbol)
        asset_type = (
            current_meta.asset_type.lower() if current_meta else "futures"
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

        # 添加一个强制刷新按钮来清除缓存
        if st.button("🔄 强制刷新数据"):
            update_database(symbol)
            get_symbols.clear()
            load_and_process_full_pipeline.clear()
            calculate_drawdown.clear()

    col_main, col_news = st.columns([3, 1])

    with col_main:
        # --- 确保用户选择了完整的起始和结束时间 ---
        if symbol and len(date_selection) == 2:
            start_date, end_date = date_selection

            with st.spinner(f"正在从 ArcticDB 加载 {symbol} 的数据..."):
                hist = load_and_process_full_pipeline(
                    symbol,
                    start_date,
                    end_date,
                    asset_type=asset_type,
                    timeframe=timeframe,
                    rsi_length=rsi_length,
                )
            if not hist.empty:
                # --- Tabs 布局 ---
                render_analysis_tabs(hist, symbol)
        else:
            # 当用户刚点选了开始日期，还没点结束日期时，给出提示
            st.info("请选择一个完整的开始和结束日期范围。")

    with col_news:
        symbol_meta = get_symbol_meta(symbol)

        st.subheader(f"{symbol_meta.name} ({symbol_meta.symbol})")

        with st.spinner(f"正在加载 {symbol} 的数据..."):
            symbolmeta_sidebar_fragment(symbol)

        st.divider()  # 视觉分割线

        # --- 下方新闻动态区 ---
        st.caption("最新市场动态")
        with st.container(height=500):  # 开启滚动模式，确保不挤占 Meta 区
            news_sidebar_fragment(symbol)


if __name__ == "__main__":
    main()
