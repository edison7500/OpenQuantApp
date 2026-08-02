from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import StringIO
from threading import Lock
from typing import Literal, NotRequired, Protocol, TypedDict

import httpx
import pandas as pd
import streamlit as st
from fredapi import Fred

logger = logging.getLogger(__name__)

CBOE_HISTORY_URL = (
    "https://cdn.cboe.com/api/global/us_indices/daily_prices/"
    "{series_id}_History.csv"
)


class MetricConfig(TypedDict):
    series_id: str
    unit: str
    icon: str
    calc: Literal["latest", "yoy", "growth_rate", "spread"]
    source: Literal["fred", "cboe"]
    compare_series_id: NotRequired[str]


@dataclass(frozen=True)
class MacroMetric:
    """A display-ready macro observation with provenance and as-of date."""

    label: str
    value: float
    unit: str
    icon: str
    observation_date: str
    source: str
    series_id: str


class SeriesSource(Protocol):
    name: str

    def get_series(self, series_id: str, limit: int) -> pd.Series:
        """Return up to ``limit`` valid observations in ascending order."""


class FredSeriesSource:
    name = "FRED"

    def __init__(self, fred: Fred) -> None:
        self._fred = fred

    def get_series(self, series_id: str, limit: int) -> pd.Series:
        # FRED defaults to ascending order, so a bare limit returns the oldest
        # observations. Request descending data explicitly, remove missing
        # releases, then restore chronological order for calculations.
        request_limit = max(limit * 2, limit + 5)
        data = self._fred.get_series(
            series_id,
            limit=request_limit,
            sort_order="desc",
        )
        if data is None:
            return pd.Series(dtype="float64")
        return data.dropna().sort_index().tail(limit)


class CboeCsvSeriesSource:
    name = "Cboe"

    def __init__(self) -> None:
        self._cache: dict[str, pd.Series] = {}
        self._lock = Lock()

    def get_series(self, series_id: str, limit: int) -> pd.Series:
        with self._lock:
            if series_id not in self._cache:
                self._cache[series_id] = self._download_series(series_id)
            data = self._cache[series_id]
        return data.tail(limit).copy()

    @staticmethod
    def _download_series(series_id: str) -> pd.Series:
        response = httpx.get(
            CBOE_HISTORY_URL.format(series_id=series_id),
            follow_redirects=True,
            timeout=15.0,
        )
        response.raise_for_status()
        frame = pd.read_csv(StringIO(response.text))
        value_column = series_id if series_id in frame else "CLOSE"
        if "DATE" not in frame or value_column not in frame:
            raise ValueError(f"Unexpected Cboe CSV schema for {series_id}")

        dates = pd.to_datetime(frame["DATE"], errors="coerce")
        values = pd.to_numeric(frame[value_column], errors="coerce")
        data = pd.Series(values.to_numpy(), index=dates, name=series_id)
        return data.loc[data.index.notna()].dropna().sort_index()


METRICS_MAP: dict[str, MetricConfig] = {
    "实际 GDP": {
        "series_id": "GDPC1",
        "unit": "% QoQ（年化）",
        "icon": "🏢",
        "calc": "growth_rate",
        "source": "fred",
    },
    "消费者价格指数（CPI）": {
        "series_id": "CPIAUCSL",
        "unit": "% YoY",
        "icon": "📊",
        "calc": "yoy",
        "source": "fred",
    },
    "核心 PCE 通胀": {
        "series_id": "PCEPILFE",
        "unit": "% YoY",
        "icon": "🎯",
        "calc": "yoy",
        "source": "fred",
    },
    "最终需求 PPI": {
        "series_id": "PPIFIS",
        "unit": "% YoY",
        "icon": "🏭",
        "calc": "yoy",
        "source": "fred",
    },
    "失业率": {
        "series_id": "UNRATE",
        "unit": "%",
        "icon": "👷",
        "calc": "latest",
        "source": "fred",
    },
    "有效联邦基金利率": {
        "series_id": "DFF",
        "unit": "%",
        "icon": "🏦",
        "calc": "latest",
        "source": "fred",
    },
    "广义美元指数": {
        "series_id": "DTWEXBGS",
        "unit": "",
        "icon": "💵",
        "calc": "latest",
        "source": "fred",
    },
    "10 年期美债": {
        "series_id": "DGS10",
        "unit": "%",
        "icon": "📈",
        "calc": "latest",
        "source": "fred",
    },
    "10Y-2Y 利差": {
        "series_id": "T10Y2Y",
        "unit": "%",
        "icon": "↔️",
        "calc": "latest",
        "source": "fred",
    },
    "金融压力指数": {
        "series_id": "STLFSI4",
        "unit": "",
        "icon": "🌡️",
        "calc": "latest",
        "source": "fred",
    },
    "VIX 指数隐含波动率": {
        "series_id": "VIX",
        "unit": "",
        "icon": "😱",
        "calc": "latest",
        "source": "cboe",
    },
    "VIXEQ 成分股隐含波动率": {
        "series_id": "VIXEQ",
        "unit": "",
        "icon": "🧩",
        "calc": "latest",
        "source": "cboe",
    },
    "VIXEQ-VIX 波动率差": {
        "series_id": "VIXEQ",
        "compare_series_id": "VIX",
        "unit": " 点",
        "icon": "🔀",
        "calc": "spread",
        "source": "cboe",
    },
}


def _fetch_single_metric(
    data_source: SeriesSource,
    label: str,
    config: MetricConfig,
) -> MacroMetric | None:
    series_id = config["series_id"]
    calc_type = config["calc"]
    fetch_limit = 13 if calc_type == "yoy" else 5

    try:
        data = data_source.get_series(series_id, fetch_limit)
        if data.empty:
            return None

        observation_date: pd.Timestamp
        if calc_type == "yoy":
            if len(data) < 13 or data.iloc[-13] == 0:
                return None
            value = ((data.iloc[-1] / data.iloc[-13]) - 1) * 100
            observation_date = pd.Timestamp(data.index[-1])
        elif calc_type == "growth_rate":
            if len(data) < 2 or data.iloc[-2] == 0:
                return None
            value = ((data.iloc[-1] / data.iloc[-2]) ** 4 - 1) * 100
            observation_date = pd.Timestamp(data.index[-1])
        elif calc_type == "spread":
            compare_id = config.get("compare_series_id")
            if not compare_id:
                return None
            comparison = data_source.get_series(compare_id, fetch_limit)
            aligned = pd.concat(
                [data.rename("primary"), comparison.rename("comparison")],
                axis=1,
                join="inner",
            ).dropna()
            if aligned.empty:
                return None
            value = (
                aligned.iloc[-1]["primary"] - aligned.iloc[-1]["comparison"]
            )
            observation_date = pd.Timestamp(aligned.index[-1])
        else:
            value = data.iloc[-1]
            observation_date = pd.Timestamp(data.index[-1])

        return MacroMetric(
            label=label,
            value=float(value),
            unit=config["unit"],
            icon=config["icon"],
            observation_date=observation_date.date().isoformat(),
            source=data_source.name,
            series_id=(
                f"{series_id}-{config['compare_series_id']}"
                if calc_type == "spread"
                else series_id
            ),
        )
    except Exception:
        logger.warning(
            "Failed to fetch macro metric %s from %s",
            series_id,
            data_source.name,
            exc_info=True,
        )
        return None


@st.cache_data(ttl=3600)
def get_macro_metrics() -> list[MacroMetric]:
    """Fetch FRED and Cboe macro/market-risk metrics concurrently."""
    if "fred" not in st.secrets or "api_key" not in st.secrets["fred"]:
        st.error("未找到 FRED API Key。请在 .streamlit/secrets.toml 中配置。")
        return []

    try:
        sources: dict[str, SeriesSource] = {
            "fred": FredSeriesSource(
                Fred(api_key=st.secrets["fred"]["api_key"])
            ),
            "cboe": CboeCsvSeriesSource(),
        }

        with ThreadPoolExecutor(max_workers=len(METRICS_MAP)) as executor:
            futures = [
                executor.submit(
                    _fetch_single_metric,
                    sources[config["source"]],
                    label,
                    config,
                )
                for label, config in METRICS_MAP.items()
            ]
            return [
                result for future in futures if (result := future.result())
            ]
    except Exception as exc:
        logger.exception("Unexpected error while fetching macro metrics")
        st.error(f"获取宏观数据时发生意外错误: {exc}")
        return []
