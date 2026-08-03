import numpy as np
import pandas as pd
import pytest

from engine import WARMUP_DAYS, get_benchmark_symbol
from engine.analytics import (
    add_relative_strength,
    add_technical_indicators,
    add_volume_metrics,
)
from engine.chart_factory import ChartFactory


@pytest.fixture
def ohlcv() -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=180, freq="D", tz="UTC")
    close = np.linspace(100, 150, len(index)) + np.sin(
        np.arange(len(index)) / 5
    )
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": np.arange(len(index), dtype=float) + 1_000,
        },
        index=index,
    )


def test_core_indicators_cover_volatility_and_trend_strength(ohlcv):
    result = add_technical_indicators(ohlcv.copy())

    expected = {"atr_main", "atr_pct", "adx_main", "dmp_main", "dmn_main"}
    assert expected <= set(result.columns)
    assert result["atr_pct"].dropna().iloc[-1] > 0
    assert not any(column.startswith("WMA_") for column in result.columns)
    assert not any(column.startswith("CCI_") for column in result.columns)


def test_short_history_keeps_a_stable_indicator_schema(ohlcv):
    result = add_technical_indicators(ohlcv.head(5).copy())

    expected = {
        "atr_main",
        "adx_main",
        "SMA_20",
        "EMA_50",
        "MACDs_12_26_9",
        "BBU_20_2.0",
    }
    assert expected <= set(result.columns)


def test_daily_and_intraday_vwap_use_the_expected_window(ohlcv):
    daily = add_volume_metrics(ohlcv.copy(), length=20, timeframe="D")
    assert daily["vwap_main"].iloc[:19].isna().all()
    assert daily["vwap_main"].iloc[19:].notna().all()

    hourly = ohlcv.iloc[:48].copy()
    hourly.index = pd.date_range(
        "2025-01-01", periods=len(hourly), freq="h", tz="UTC"
    )
    intraday = add_volume_metrics(hourly, length=20, timeframe="1h")
    first_typical_price = (
        intraday["High"].iloc[24]
        + intraday["Low"].iloc[24]
        + intraday["Close"].iloc[24]
    ) / 3
    assert intraday["vwap_main"].iloc[24] == pytest.approx(first_typical_price)


def test_relative_strength_is_normalized_and_optional(ohlcv):
    benchmark = pd.Series(np.linspace(100, 125, len(ohlcv)), index=ohlcv.index)
    result = add_relative_strength(ohlcv.copy(), benchmark)

    assert result["relative_strength"].iloc[0] == pytest.approx(100)
    assert result["relative_strength"].iloc[-1] > 100
    assert (
        "relative_strength"
        not in add_relative_strength(ohlcv.copy(), None).columns
    )


def test_benchmark_mapping_and_warmup_are_asset_aware():
    assert get_benchmark_symbol("AAPL", "equity") == "SPY"
    assert get_benchmark_symbol("ETH/USDT", "crypto") == "BTC/USDT"
    assert get_benchmark_symbol("SPY", "ETF") is None
    assert get_benchmark_symbol("GC=F", "futures") is None
    assert WARMUP_DAYS["M"] > WARMUP_DAYS["W"] > WARMUP_DAYS["D"]


def test_macd_chart_includes_signal_and_only_risk_chart_includes_atr(ohlcv):
    result = add_technical_indicators(ohlcv.copy())
    result = add_volume_metrics(result)
    result["Buy_Signal"] = False
    result["Sell_Signal"] = False

    macd = ChartFactory.build_view(result, "TEST", "MACD")
    rsi = ChartFactory.build_view(result, "TEST", "RSI")
    risk = ChartFactory.build_view(result, "TEST", "DrawDown")

    assert "Signal线" in {trace.name for trace in macd.data}
    assert "ATR %" not in {trace.name for trace in rsi.data}
    assert "ATR %" in {trace.name for trace in risk.data}
