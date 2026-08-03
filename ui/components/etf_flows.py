from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from api.sosovalue import SoSoValueClient, SoSoValueError
from utils.human_readable import format_human_readable


@st.cache_data(ttl=3600, show_spinner=False)
def _load_btc_etf_flows(api_key: str):
    return SoSoValueClient(api_key).get_historical_inflows("us-btc-spot")


def _format_usd(value: float) -> str:
    if not math.isfinite(value):
        return "N/A"
    sign = "-" if value < 0 else ""
    return f"{sign}${format_human_readable(abs(value))}"


def render_btc_etf_flows() -> None:
    """Render recent US spot-BTC ETF aggregate flows when configured."""
    st.divider()
    st.subheader("美国现货 BTC ETF")
    api_key = st.secrets.get("sosovalue", {}).get("api_key", "")
    if not api_key:
        st.info("配置 [sosovalue].api_key 后可查看 ETF 资金流。")
        return

    try:
        flows = _load_btc_etf_flows(api_key)
    except (SoSoValueError, ValueError) as exc:
        st.warning(f"ETF 资金流暂不可用：{exc}")
        return

    if flows.empty:
        st.info("SoSoValue 暂无 ETF 资金流数据。")
        return

    recent = flows.tail(30)
    latest = flows.iloc[-1]
    latest_date = flows.index[-1].date().isoformat()
    col_daily, col_cumulative = st.columns(2)
    col_daily.metric(
        f"当日净流入 · {latest_date}",
        _format_usd(latest["NetInflowUSD"]),
    )
    col_cumulative.metric(
        "累计净流入",
        _format_usd(latest["CumulativeNetInflowUSD"]),
    )

    colors = [
        "#16a34a" if value >= 0 else "#dc2626"
        for value in recent["NetInflowUSD"]
    ]
    figure = go.Figure(
        go.Bar(
            x=recent.index,
            y=recent["NetInflowUSD"],
            marker_color=colors,
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(
        height=300,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        yaxis_title="USD",
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption("最近 30 个交易日；数据源：SoSoValue，通常于美股收盘后更新。")
