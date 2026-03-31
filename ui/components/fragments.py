from pprint import pprint

import streamlit as st
import yfinance as yf

from api.fetch_news import fetch_and_analyze
from utils.human_readable import format_human_readable  # format_percentage,
from utils.human_readable import format_value, get_display_format


@st.fragment
def control_panel_sidebar_fragment(title: str) -> None:
    st.set_page_config(
        page_title=f"{title}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # # 侧边栏交互
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
    #         load_and_process_data_with_range.clear()
    #         calculate_drawdown.clear()


@st.fragment
def symbolmeta_sidebar_fragment(symbol: str) -> None:
    ticker = yf.Ticker(symbol)
    info = ticker.fast_info
    m1, m2 = st.columns(2)
    try:
        val = info["lastPrice"]
        fmt_cfg = get_display_format(ticker)
        print(fmt_cfg)
        m1.metric(
            "当前价格",
            format_value(val, fmt_cfg),
            # f"+{info['regularMarketChangePercent']:.2}%",
            # delta=format_percentage(info["regularMarketChangePercent"]),
        )
    except KeyError:
        pass
    m2.metric("成交量", format_human_readable(info["lastVolume"]))

    m3, m4 = st.columns(2)
    try:
        m3.metric("总市值", format_human_readable(info["marketCap"]))
        m4.metric("波动率", "1.24%")  # 示例
    except KeyError:
        pass


@st.fragment
def news_sidebar_fragment(symbol: str) -> None:
    st.subheader(f"📰 {symbol} 實時新聞")

    # 局部刷新按鈕
    if st.button("🔄 刷新新聞 (局部)"):
        st.cache_data.clear()  # 清除緩存以獲取最新
        # fragment 會自動處理局部重新渲染

    with st.spinner("讀取中..."):
        # df = get_cached_news(symbol)
        df = fetch_and_analyze(symbol)

    if not df.empty:
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
