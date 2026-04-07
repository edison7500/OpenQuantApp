import pandas as pd
import streamlit as st
import yfinance as yf

from database.resource import get_arctic_library, get_symbol_meta
from engine import (
    load_and_process_full_pipeline,
)
from ui.components.analysis_tabs import render_analysis_tabs
from ui.components.fragments import (
    news_grid_fragment,
    symbolmeta_sidebar_fragment,
)
from ui.components.sidebar import render_common_sidebar


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
        page_title="Index Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- 引入通用侧边栏 ---
    params = render_common_sidebar(asset_type="index")
    symbol = params["symbol"]
    date_selection = params["date_range"]
    timeframe = params["timeframe"]
    rsi_length = params["rsi_length"]

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
                    asset_type="index",
                    timeframe=timeframe,
                    rsi_length=rsi_length,
                )
            if not hist.empty:
                # --- Tabs 布局 ---
                render_analysis_tabs(hist, symbol)

                # --- 新增：主视图下方的 Grid 新闻区 ---
                news_grid_fragment(symbol)
        else:
            # 当用户刚点选了开始日期，还没点结束日期时，给出提示
            st.info("请选择一个完整的开始和结束日期范围。")

    with col_news:
        symbol_meta = get_symbol_meta(symbol)

        st.subheader(f"{symbol_meta.name} ({symbol_meta.symbol})")

        with st.spinner(f"正在加载 {symbol} 的数据..."):
            symbolmeta_sidebar_fragment(symbol)


if __name__ == "__main__":
    main()
