import pandas as pd
import streamlit as st
import yfinance as yf

from database.resource import get_arctic_library, get_symbol_meta
from engine import (
    load_and_process_full_pipeline,
)  # load_and_process_data_with_range,; process_data_with_rvol,; calculate_drawdown,
from engine.llm_manager import llm_manager
from engine.macro_manager import get_macro_metrics
from api.fetch_news import fetch_and_analyze
from ui.components.analysis_tabs import render_analysis_tabs
from ui.components.fragments import (
    news_grid_fragment,
    symbolmeta_sidebar_fragment,
    financial_reports_sidebar_fragment,
    macro_data_marquee_fragment,
)
from ui.components.sidebar import render_common_sidebar

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

    # --- 引入通用侧边栏 ---
    params = render_common_sidebar(asset_type="equity")
    symbol = params["symbol"]
    date_selection = params["date_range"]
    timeframe = params["timeframe"]
    rsi_length = params["rsi_length"]

    # 侧边栏交互 (原代码已注释，以便于 debug)
    # with st.sidebar:
    #     st.header("参数设置")

    #     portfolio = get_symbols()
    #     if "symbol" not in st.session_state:
    #         st.session_state.setdefault("symbol", portfolio[0])

    #     symbol = st.selectbox(
    #         "选择分析标的",
    #         options=portfolio,
    #         key="symbol",
    #     )

    #     # --- 新增：日期范围选择器 ---
    #     now = datetime.datetime.now(tz=pytz.UTC)
    #     default_start = now - datetime.timedelta(days=180)  # 默认看过去半年

    #     # date_input 允许传入一个 tuple 来选择区间
    #     date_selection = st.date_input(
    #         "选择时间范围",
    #         value=(default_start, now),
    #         max_value=now + datetime.timedelta(days=1),
    #     )

    #     timeframe = st.select_slider(
    #         "TimeFrame",
    #         options=[
    #             "1m",
    #             "1h",
    #             "D",
    #         ],
    #         value="D",
    #     )

    #     rsi_length = st.slider("RSI 周期", min_value=5, max_value=30, value=14)

    #     # auto_refresh = st.toggle("开启自动刷新", value=False)

    #     # 添加一个强制刷新按钮来清除缓存
    #     if st.button("🔄 强制刷新数据"):
    #         update_database(symbol)
    #         get_symbols.clear()
    #         # load_and_process_data_with_range.clear()
    #         load_and_process_full_pipeline.clear()
    #         calculate_drawdown.clear()

    col_main, col_news = st.columns([3, 1])

    with col_main:
        # --- 宏观经济数据磁贴 (主视觉区顶部) ---
        macro_data_marquee_fragment()

        # --- 确保用户选择了完整的起始和结束时间 ---
        if symbol and len(date_selection) == 2:
            start_date, end_date = date_selection

            with st.spinner(f"正在从 ArcticDB 加载 {symbol} 的数据..."):
                # hist = load_and_process_data(symbol, rsi_length)
                hist = load_and_process_full_pipeline(
                    symbol,
                    start_date,
                    end_date,
                    asset_type="equity",
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

        # st.subheader(f"### {symbol_meta.name} 的详情")
        st.subheader(f"{symbol_meta.name} ({symbol_meta.symbol})")

        with st.spinner(f"正在加载 {symbol} 的数据..."):
            symbolmeta_sidebar_fragment(symbol)
            financial_reports_sidebar_fragment(symbol)

        st.divider()
        st.subheader("🤖 AI 智能推理")
        
        if st.button("🚀 生成量化分析报告", key=f"ai_analyze_{symbol}"):
            with st.spinner("AI 正在综合财务、新闻及宏观数据推理中..."):
                try:
                    # 1. 准备技术指标数据 (从 main 作用域的 hist 获取)
                    tech_data = None
                    if 'hist' in locals() and not hist.empty:
                        tech_data = hist

                    # 2. 准备财务数据 (模拟从 financial_reports_sidebar_fragment 提取)
                    # 实际上应该在 fragments 中提供一个获取数据的方法，
                    # 这里我们直接调用 yfinance 获取关键指标
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    financial_data = {
                        "ROE": info.get("returnOnEquity"),
                        "D/E Ratio": info.get("debtToEquity"),
                        "Profit Margin": info.get("profitMargins"),
                        "Op. Margin": info.get("operatingMargins"),
                        "Div. Yield": info.get("dividendYield"),
                        "Trailing EPS": info.get("trailingEps"),
                        "Forward EPS": info.get("forwardEps"),
                    }

                    # 3. 准备最新新闻摘要
                    news_df = fetch_and_analyze(symbol)

                    # 4. 准备宏观数据
                    macro_metrics = get_macro_metrics()

                    # 调用 LLM 管理器进行分析
                    analysis_result = llm_manager.analyze_symbol(
                        symbol=symbol,
                        technical_data=tech_data,
                        financial_data=financial_data,
                        news_data=news_df,
                        macro_data=macro_metrics
                    )
                    st.markdown(f"**分析结论：**\n\n{analysis_result}")
                except Exception as e:
                    st.error(f"AI 分析失败：{e}")
        else:
            st.info("点击按钮生成基于多维数据的 AI 推理结论")


if __name__ == "__main__":
    main()
