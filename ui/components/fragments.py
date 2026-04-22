import pandas as pd
import streamlit as st
import yfinance as yf

from api.fetch_news import fetch_and_analyze
from database.connections.arcticdb_conn import ArcticDBConnection
from engine.llm_manager import llm_manager
from engine.macro_manager import get_macro_metrics
from utils.human_readable import (
    format_human_readable,
    format_percentage,
    format_value,
    get_display_format,
)


@st.fragment
def control_panel_sidebar_fragment(title: str) -> None:
    st.set_page_config(
        page_title=f"{title}",
        layout="wide",
        initial_sidebar_state="expanded",
    )


@st.fragment
def symbolmeta_sidebar_fragment(symbol: str) -> None:
    ticker = yf.Ticker(symbol)
    fast_info = ticker.fast_info

    # 从 ArcticDB 获取历史数据 (替代 ticker.history)
    hist = pd.DataFrame()
    try:
        ac = st.connection("arcticdb", type=ArcticDBConnection)
        lib = ac.get_library(timeframe="D")
        if lib.has_symbol(symbol):
            # 读取该 symbol 的所有数据
            full_hist = lib.read(symbol).data
            # 截取最近一个月的数据 (约 22 个交易日)
            hist = full_hist.tail(30)
    except Exception as e:
        st.error(f"ArcticDB 读取失败：{e}")

    # 如果 ArcticDB 没有数据，尝试用 yfinance 做最后的保底
    if hist.empty:
        try:
            hist = ticker.history(period="1mo")
        except Exception:
            hist = pd.DataFrame()

    m1, m2 = st.columns(2)

    try:
        val = fast_info["lastPrice"]
        fmt_cfg = get_display_format(ticker)

        # 计算涨跌幅 (当前价 vs 昨日收盘)
        delta_val = None
        if len(hist) >= 2:
            prev_close = hist["Close"].iloc[-2]
            delta_val = ((val - prev_close) / prev_close) * 100

        m1.metric(
            "当前价格",
            format_value(val, fmt_cfg),
            delta=format_percentage(delta_val)
            if delta_val is not None
            else None,
        )
    except (KeyError, IndexError):
        pass

    try:
        m2.metric("成交量", format_human_readable(fast_info["lastVolume"]))
    except (KeyError, IndexError):
        pass

    m3, m4 = st.columns(2)
    try:
        m3.metric("总市值", format_human_readable(fast_info["marketCap"]))

        # 计算波动率 (年化标准差)
        vol_str = "N/A"
        if len(hist) > 1:
            returns = hist["Close"].pct_change(fill_method=None).dropna()
            vol = returns.std() * (252**0.5) * 100
            vol_str = f"{vol:.2f}%"
        m4.metric("波动率", vol_str)
    except (KeyError, IndexError):
        pass


@st.fragment
def macro_data_marquee_fragment() -> None:
    """显示 FRED 宏观经济数据跑马灯 - 优化版"""

    # 1. 获取数据
    display_data = get_macro_metrics()

    if not display_data:
        # 如果没有数据，可以选择静默退出或显示占位
        return

    # 2. 构造 HTML 列表 (使用列表推导式性能更佳)
    items_list = [
        f'<div class="macro-item">{icon} <b>{label}</b>: {value:.2f}{unit or ""}</div>'
        for label, value, unit, icon in display_data
    ]

    # 合并内容
    single_set_html = "".join(items_list)
    # 为了保证长短不一的数据都能实现平滑循环，重复2次配合 CSS transform
    marquee_content = single_set_html * 2

    # 3. 渲染 Markdown
    st.markdown(
        f"""
        <style>
        /* 容器样式 */
        .macro-marquee-container {{
            width: 100%;
            overflow: hidden;
            background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
            border-radius: 8px;
            padding: 12px 0;
            margin-bottom: 20px;
            border: 1px solid var(--border-color, rgba(0, 0, 0, 0.1));
            display: flex;
            position: relative;
        }}

        /* 轨道样式 */
        .macro-marquee-track {{
            display: flex;
            white-space: nowrap;
            width: max-content;
            animation: marquee 40s linear infinite; /* 增加到40s，阅读更舒适 */
        }}

        /* 悬停暂停动画 */
        .macro-marquee-container:hover .macro-marquee-track {{
            animation-play-state: paused;
        }}

        /* 单个数据项样式 */
        .macro-item {{
            display: flex;
            align-items: center;
            padding: 0 30px;
            font-size: 0.9rem;
            color: var(--text-color);
            font-family: sans-serif;
        }}

        .macro-item b {{
            margin-left: 4px;
            margin-right: 2px;
        }}

        /* 关键帧：平滑循环的关键是平移 -50% */
        @keyframes marquee {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(-50%); }}
        }}
        </style>

        <div class="macro-marquee-container">
            <div class="macro-marquee-track">
                {marquee_content}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# @st.fragment
# def macro_data_marquee_fragment() -> None:
#     """显示 FRED 宏观经济数据跑马灯 - 用于主视觉区顶部"""
#     display_data = get_macro_metrics()

#     if display_data:
#         # 构建跑马灯内容
#         items_html = ""
#         for label, value, unit, icon in display_data:
#             val_str = f"{value:.2f}{unit}" if unit else f"{value:.2f}"
#             items_html += f'<span class="macro-item">{icon} <b>{label}</b>: {val_str}</span>'

#         # 为了实现无缝循环，内容需要重复
#         marquee_content = items_html * 3

#         st.markdown(
#             f"""
#             <style>
#             .macro-marquee-container {{
#                 width: 100%;
#                 overflow: hidden;
#                 background: rgba(0, 0, 0, 0.05);
#                 border-radius: 10px;
#                 padding: 10px 0;
#                 margin-bottom: 20px;
#                 border: 1px solid rgba(0, 0, 0, 0.1);
#                 display: flex;
#             }}
#             .macro-marquee-track {{
#                 display: flex;
#                 white-space: nowrap;
#                 animation: marquee 30s linear infinite;
#             }}
#             .macro-item {{
#                 display: inline-block;
#                 padding: 0 30px;
#                 font-size: 14px;
#                 color: #31333F;
#             }}
#             @keyframes marquee {{
#                 0% {{ transform: translateX(0); }}
#                 100% {{ transform: translateX(-33.33%); }}
#             }}
#             </style>
#             <div class="macro-marquee-container">
#                 <div class="macro-marquee-track">
#                     {marquee_content}
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )


# @st.cache_data(ttl=3600)
def get_ticker_info(_symbol: str) -> dict:
    """Fetch and cache ticker info from yfinance."""
    ticker = yf.Ticker(_symbol)
    return ticker.info


@st.fragment
def financial_reports_sidebar_fragment(symbol: str) -> None:
    """在侧边栏显示关键财务指标"""
    st.divider()
    st.subheader("📊 财务报表 (Financial Reports)")

    try:
        # 使用缓存的函数获取更详细的财务指标
        info = get_ticker_info(symbol)

        # 定义要显示的指标映射 (Label: key_in_info)

        # 定义要显示的指标映射 (Label: key_in_info)
        metrics_map = {
            "ROE": "returnOnEquity",
            "D/E Ratio": "debtToEquity",
            "Profit Margin": "profitMargins",
            "Op. Margin": "operatingMargins",
            "Div. Yield": "dividendYield",
            "Trailing EPS": "trailingEps",
            "Forward EPS": "forwardEps",
        }

        # 准备要显示的指标列表
        display_metrics = []
        for label, key in metrics_map.items():
            if key in info and info[key] is not None:
                val = info[key]
                # 格式化数值
                if isinstance(val, float):
                    if label in [
                        "ROE",
                        "Profit Margin",
                        "Op. Margin",
                        "Div. Yield",
                    ]:
                        formatted_val = f"{val * 100:.2f}%"
                    elif label == "D/E Ratio":
                        formatted_val = f"{val:.2f}"
                    else:
                        formatted_val = f"{val:.2f}"
                else:
                    formatted_val = str(val)
                display_metrics.append((label, formatted_val))

        if display_metrics:
            # 使用两列布局显示指标
            cols = st.columns(2)
            for i, (label, val) in enumerate(display_metrics):
                cols[i % 2].metric(label, val)
        else:
            st.info("暂无详细财务指标")

    except Exception as e:
        st.error(f"无法加载财务报表：{e}")


@st.fragment
def news_grid_fragment(symbol: str) -> None:
    """在主视图下方以 3 栏 Grid 形式展示新闻"""
    st.markdown("---")
    st.subheader(f"📰 {symbol} 市场动态 (3 栏视图)")

    # 局部刷新按钮
    if st.button("🔄 刷新新闻", key="refresh_grid_news"):
        st.cache_data.clear()

    with st.spinner("正在获取最新资讯..."):
        df = fetch_and_analyze(symbol)

    if not df.empty:
        # 情感分布小统计 (放在最上面一行)
        sentiment_counts = df["sentiment_label"].value_counts()
        st.caption("过去 7 天情感分布趋势")
        st.bar_chart(sentiment_counts, horizontal=True, height=120)

        st.divider()

        # 使用 columns 实现 3 栏 Grid
        cols = st.columns(3)
        for i, (_, row) in enumerate(df.head(12).iterrows()):
            # 轮流放入 3 个列中
            with cols[i % 3]:
                with st.container(border=True, height=280):
                    # 情感标签
                    label_color = {
                        "Positive": "green",
                        "Neutral": "gray",
                        "Negative": "red",
                    }.get(row["sentiment_label"], "blue")

                    st.markdown(
                        f":{label_color}[**{row['sentiment_label']}**] (得分：{row['sentiment_score']:.2f})"
                    )
                    st.markdown(
                        f"**{row['headline'][:80]}...**"
                        if len(row["headline"]) > 80
                        else f"**{row['headline']}**"
                    )
                    st.caption(
                        f"{row['source']} | {row['datetime'].strftime('%Y-%m-%d')}"
                    )
                    st.link_button(
                        "阅读原文",
                        row["url"],
                        icon="🔗",
                        width="stretch",
                    )
    else:
        st.info("暂无新闻资讯")


@st.fragment
def news_sidebar_fragment(symbol: str) -> None:
    st.subheader(f"📰 {symbol} 實時新聞")

    # 局部刷新按鈕
    if st.button("🔄 刷新新聞 (局部)"):
        st.cache_data.clear()  # 清除緩存以獲取最新

    with st.spinner("讀取中..."):
        df = fetch_and_analyze(symbol)

    if not df.empty:
        # 情感分布小统计
        sentiment_counts = df["sentiment_label"].value_counts()
        st.caption("过去 7 天情感分布")
        st.bar_chart(sentiment_counts, horizontal=True, height=150)

        st.divider()

        # 新闻列表渲染
        for _, row in df.head(12).iterrows():
            with st.container(border=True):
                st.markdown(
                    f"**{row['sentiment_label']}** (得分：{row['sentiment_score']:.2f})"
                )
                st.markdown(f"**{row['headline']}**")
                st.caption(
                    f"{row['source']} | {row['datetime'].strftime('%Y-%m-%d')}"
                )
                st.link_button("查看全文", row["url"], icon="🔗")


@st.fragment
def ai_analysis_sidebar_fragment(symbol: str, hist: pd.DataFrame) -> None:
    """在右侧边栏显示 AI 智能分析报告"""
    st.divider()
    st.subheader("🤖 AI 智能推理")

    if st.button("🚀 生成量化分析报告", key=f"ai_analyze_{symbol}"):
        with st.spinner("AI 正在综合财务、新闻及宏观数据推理中..."):
            try:
                # 1. 准备技术指标数据
                tech_data = hist if not hist.empty else None

                # 2. 准备财务数据 (使用缓存函数)
                info = get_ticker_info(symbol)
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
                    macro_data=macro_metrics,
                )
                st.markdown(f"**分析结论：**\n\n{analysis_result}")
            except Exception as e:
                st.error(f"AI 分析失败：{e}")
    else:
        st.info("点击按钮生成基于多维数据的 AI 推理结论")
