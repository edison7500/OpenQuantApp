from __future__ import annotations

import pandas as pd
import pytest

from engine.macro_manager import (
    CboeCsvSeriesSource,
    FredSeriesSource,
    METRICS_MAP,
    MetricConfig,
    _fetch_single_metric,
)


class FakeFred:
    def __init__(self, data: pd.Series) -> None:
        self.data = data
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_series(self, series_id: str, **kwargs) -> pd.Series:
        self.calls.append((series_id, kwargs))
        return self.data


class FakeSource:
    name = "Test"

    def __init__(self, series: dict[str, pd.Series]) -> None:
        self.series = series

    def get_series(self, series_id: str, limit: int) -> pd.Series:
        return self.series[series_id].dropna().sort_index().tail(limit)


def make_config(
    *,
    series_id: str = "TEST",
    calc: str = "latest",
    compare_series_id: str | None = None,
) -> MetricConfig:
    config: MetricConfig = {
        "series_id": series_id,
        "unit": "%",
        "icon": "📊",
        "calc": calc,
        "source": "fred",
    }
    if compare_series_id:
        config["compare_series_id"] = compare_series_id
    return config


def test_fred_source_explicitly_requests_latest_observations():
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    descending = pd.Series(
        [5.0, float("nan"), 3.0, 2.0, 1.0],
        index=dates[::-1],
    )
    fred = FakeFred(descending)

    result = FredSeriesSource(fred).get_series("TEST", limit=3)

    assert fred.calls == [("TEST", {"limit": 8, "sort_order": "desc"})]
    assert result.index.is_monotonic_increasing
    assert result.tolist() == [2.0, 3.0, 5.0]


def test_yoy_uses_latest_thirteen_valid_months():
    dates = pd.date_range("2025-01-01", periods=13, freq="MS")
    source = FakeSource(
        {"TEST": pd.Series([100.0] * 12 + [110.0], index=dates)}
    )

    result = _fetch_single_metric(source, "同比测试", make_config(calc="yoy"))

    assert result is not None
    assert result.value == pytest.approx(10.0)
    assert result.observation_date == "2026-01-01"


def test_yoy_does_not_mislabel_level_when_history_is_short():
    dates = pd.date_range("2025-01-01", periods=12, freq="MS")
    source = FakeSource(
        {"TEST": pd.Series(range(100, 112), index=dates, dtype=float)}
    )

    result = _fetch_single_metric(source, "同比测试", make_config(calc="yoy"))

    assert result is None


def test_growth_rate_is_quarter_over_quarter_annualized():
    dates = pd.date_range("2025-01-01", periods=2, freq="QS")
    source = FakeSource({"TEST": pd.Series([100.0, 101.0], index=dates)})

    result = _fetch_single_metric(
        source, "GDP", make_config(calc="growth_rate")
    )

    assert result is not None
    assert result.value == pytest.approx((1.01**4 - 1) * 100)


@pytest.mark.parametrize(
    ("series_id", "csv_text", "expected"),
    [
        (
            "VIXEQ",
            "DATE,VIXEQ\n07/30/2026,46.27\n07/31/2026,44.42\n",
            44.42,
        ),
        (
            "VIX",
            (
                "DATE,OPEN,HIGH,LOW,CLOSE\n"
                "07/30/2026,17.0,17.5,16.8,17.09\n"
                "07/31/2026,16.2,16.4,16.0,16.15\n"
            ),
            16.15,
        ),
    ],
)
def test_cboe_csv_source_parses_and_caches_official_schema(
    monkeypatch, series_id, csv_text, expected
):
    class FakeResponse:
        text = csv_text

        @staticmethod
        def raise_for_status() -> None:
            return None

    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse()

    monkeypatch.setattr("engine.macro_manager.httpx.get", fake_get)
    source = CboeCsvSeriesSource()

    first = source.get_series(series_id, 1)
    second = source.get_series(series_id, 2)

    assert len(calls) == 1
    assert first.iloc[-1] == pytest.approx(expected)
    assert second.index[-1].date().isoformat() == "2026-07-31"


def test_vixeq_spread_uses_same_date_for_both_cboe_series():
    dates = pd.to_datetime(["2026-07-30", "2026-07-31"])
    source = FakeSource(
        {
            "VIXEQ": pd.Series([46.27, 44.42], index=dates),
            "VIX": pd.Series([17.09, 16.15], index=dates),
        }
    )
    config = make_config(
        series_id="VIXEQ",
        calc="spread",
        compare_series_id="VIX",
    )

    result = _fetch_single_metric(source, "波动率差", config)

    assert result is not None
    assert result.value == pytest.approx(28.27)
    assert result.observation_date == "2026-07-31"
    assert result.series_id == "VIXEQ-VIX"


def test_metric_set_covers_macro_regime_and_vixeq():
    series_ids = {config["series_id"] for config in METRICS_MAP.values()}

    assert {"UNRATE", "T10Y2Y", "STLFSI4", "VIXEQ"} <= series_ids
    assert METRICS_MAP["最终需求 PPI"]["series_id"] == "PPIFIS"
    assert METRICS_MAP["有效联邦基金利率"]["series_id"] == "DFF"
