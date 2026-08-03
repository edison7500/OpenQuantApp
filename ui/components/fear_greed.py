from __future__ import annotations

import streamlit as st

from api.fear_greed import FearGreedClient, FearGreedObservation

CLASSIFICATION_ZH = {
    "Extreme Fear": "极度恐惧",
    "Fear": "恐惧",
    "Neutral": "中性",
    "Greed": "贪婪",
    "Extreme Greed": "极度贪婪",
}


@st.cache_data(ttl=3600, show_spinner=False)
def load_fear_greed() -> FearGreedObservation:
    return FearGreedClient().get_latest()


def render_fear_greed(observation: FearGreedObservation) -> None:
    """Render a compact Bitcoin-market sentiment summary."""
    label = CLASSIFICATION_ZH.get(
        observation.classification, observation.classification
    )
    st.subheader("Crypto 恐惧与贪婪")
    st.metric(
        f"{label} · {observation.observation_date}",
        f"{observation.value} / 100",
    )
    st.progress(observation.value)
    st.caption(
        "Bitcoin 市场情绪；数据源："
        "[Alternative.me](https://alternative.me/crypto/fear-and-greed-index/)；"
        "每日更新。"
    )
