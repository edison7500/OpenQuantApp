import streamlit as st
import yfinance as yf
import pandas as pd
from fredapi import Fred

from api.fetch_news import fetch_and_analyze
from utils.human_readable import format_human_readable, format_percentage
from utils.human_readable import format_value, get_display_format
from database.connections.arcticdb_conn import ArcticDBConnection


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


def _fetch_fred_series_with_retry(
    fred: Fred, series_id: str, limit: int = 1, max_retries: int = 3
) -> pd.Series | None:
    """从 FRED 获取数据，带重试机制"""
    import time

    for attempt in range(max_retries):
        try:
            data = fred.get_series(series_id, limit=limit)
            if not data.empty:
                return data
            return None
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.5 * (attempt + 1))  # 递增延迟重试
    return None


@st.fragment
def macro_data_grid_fragment() -> None:
    """显示 FRED 宏观经济数据网格"""
    st.subheader("🌍 宏观数据 (Macroeconomic Data)")

    # FRED 系列 ID 映射
    metrics_map = {
        "联邦基金利率": {
            "series_id": "FEDFUNDS",
            "unit": "%",
            "description": "有效联邦基金利率",
        },
        "通胀率 (CPI)": {
            "series_id": "CPIAUCSL",
            "unit": "% YoY",
            "description": "消费者价格指数同比",
        },
        "美元指数": {
            "series_id": "DTWEXBGS",
            "unit": "",
            "description": "美元兑主要货币篮子",
        },
        "10 年期美债": {
            "series_id": "DGS10",
            "unit": "%",
            "description": "10 年期国债收益率",
        },
    }

    try:
        api_key = st.secrets["fred"]["api_key"]
        fred = Fred(api_key=api_key)

        display_data = []
        for label, config in metrics_map.items():
            series_id = config["series_id"]
            data = _fetch_fred_series_with_retry(fred, series_id, limit=1)
            if data is not None:
                value = data.iloc[-1]
                # CPI 需要计算同比变化
                if series_id == "CPIAUCSL":
                    cpi_data = _fetch_fred_series_with_retry(
                        fred, series_id, limit=13
                    )
                    if cpi_data is not None and len(cpi_data) >= 13:
                        current = cpi_data.iloc[-1]
                        year_ago = cpi_data.iloc[-13]
                        value = ((current - year_ago) / year_ago) * 100
                display_data.append(
                    (label, float(value), config["unit"], config["description"])
                )

        if not display_data:
            st.info("暂无宏观数据")

    except Exception as e:
        st.error(f"获取宏观数据失败：{e}")

    if display_data:
        # 使用 2x2 网格布局
        row1 = st.columns(2)
        row2 = st.columns(2)
        rows = [row1, row2]

        for i, (label, value, unit, desc) in enumerate(display_data[:4]):
            with rows[i // 2][i % 2]:
                with st.container(border=True):
                    st.caption(f"{label}")
                    st.metric(
                        label=desc,
                        value=f"{value:.2f}{unit}" if unit else f"{value:.2f}",
                    )
    else:
        st.info("暂无宏观数据")


@st.fragment
def financial_reports_sidebar_fragment(symbol: str) -> None:
    """在侧边栏显示关键财务指标"""
    st.divider()
    st.subheader("📊 财务报表 (Financial Reports)")

    ticker = yf.Ticker(symbol)

    try:
        # 使用 .info 获取更详细的财务指标
        info = ticker.info

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

    # 在财务报表下方显示宏观数据
    st.divider()
    macro_data_grid_fragment()


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
                        use_container_width=True,
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
    else:
        st.info("暫無新聞")
