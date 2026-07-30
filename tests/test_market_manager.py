import datetime

import ccxt
import pandas as pd
import pytest

from api.market_manager import MarketDataError, MarketDataManager


class FakeExchange:
    has = {"fetchOHLCV": True}
    timeframes = {"1h": "1h", "1d": "1d"}

    def __init__(self, pages=None, error=None):
        self.pages = list(pages or [])
        self.error = error
        self.calls = []

    def load_markets(self):
        return {
            "BTC/USDT": {
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "spot": True,
                "type": "spot",
            }
        }

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self.calls.append((symbol, timeframe, since, limit))
        if self.error:
            raise self.error
        return self.pages.pop(0) if self.pages else []

    @staticmethod
    def parse_timeframe(timeframe):
        return {"1h": 3600, "1d": 86400}[timeframe]

    @staticmethod
    def milliseconds():
        return int(pd.Timestamp("2024-01-01 03:30:00Z").timestamp() * 1000)


def _ms(value):
    return int(pd.Timestamp(value).timestamp() * 1000)


def _candle(value, close):
    timestamp = _ms(value)
    return [timestamp, close - 1, close + 1, close - 2, close, 10]


def test_crypto_fetch_paginates_deduplicates_and_drops_open_candle():
    exchange = FakeExchange(
        pages=[
            [
                _candle("2024-01-01 00:00:00Z", 10),
                _candle("2024-01-01 01:00:00Z", 11),
                _candle("2024-01-01 02:00:00Z", 12),
            ],
            [
                _candle("2024-01-01 02:00:00Z", 13),
                _candle("2024-01-01 03:00:00Z", 14),
            ],
            [],
        ]
    )
    manager = MarketDataManager(exchange_instance=exchange)

    result = manager.fetch_data(
        "BTC/USDT",
        "Crypto",
        datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        datetime.datetime(2024, 1, 1, 4, tzinfo=datetime.timezone.utc),
        timeframe="1h",
    )

    assert list(result["Close"]) == [10, 11, 13]
    assert result.index.is_monotonic_increasing
    assert str(result.index.tz) == "UTC"
    assert len(exchange.calls) == 3


def test_unknown_timeframe_is_not_silently_changed_to_daily():
    manager = MarketDataManager(exchange_instance=FakeExchange())

    with pytest.raises(ValueError, match="不支持的周期"):
        manager.fetch_data(
            "BTC/USDT",
            "Crypto",
            datetime.datetime(2024, 1, 1),
            datetime.datetime(2024, 1, 2),
            timeframe="5m",
        )


def test_network_error_is_exposed_after_retries():
    manager = MarketDataManager(
        exchange_instance=FakeExchange(error=ccxt.NetworkError("offline")),
        max_retries=0,
    )

    with pytest.raises(MarketDataError, match="网络请求重试失败"):
        manager.fetch_data(
            "BTC/USDT",
            "Crypto",
            datetime.datetime(2024, 1, 1),
            datetime.datetime(2024, 1, 2),
            timeframe="1h",
        )


def test_non_spot_market_is_rejected():
    exchange = FakeExchange()
    exchange.load_markets = lambda: {
        "BTC/USDT": {
            "symbol": "BTC/USDT",
            "base": "BTC",
            "quote": "USDT",
            "spot": False,
            "type": "swap",
        }
    }
    manager = MarketDataManager(exchange_instance=exchange)

    with pytest.raises(ValueError, match="不是现货"):
        manager.inspect_crypto_market("BTC/USDT")


def test_ccxt_uses_proxy_environment_and_only_loads_spot_markets():
    exchange = MarketDataManager("binance").crypto_exchange

    assert exchange.session.trust_env is True
    assert exchange.options["fetchMarkets"]["types"] == ["spot"]


def test_currency_is_routed_to_yfinance(monkeypatch):
    manager = MarketDataManager()
    expected = MarketDataManager._empty_frame()
    calls = []

    def fetch_tradfi(symbol, start_date, end_date, timeframe):
        calls.append((symbol, timeframe))
        return expected

    monkeypatch.setattr(manager, "_fetch_tradfi", fetch_tradfi)
    result = manager.fetch_data(
        "JPY=X",
        "Currency",
        datetime.datetime(2024, 1, 1),
        datetime.datetime(2024, 1, 2),
        timeframe="D",
    )

    assert result is expected
    assert calls == [("JPY=X", "1d")]
