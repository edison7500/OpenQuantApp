from types import SimpleNamespace

import pandas as pd

from database.models import SymbolMeta
from sync_engine import DataSyncEngine


class FakeLibrary:
    def __init__(self):
        self.data = {}
        self.metadata = {}

    def has_symbol(self, symbol):
        return symbol in self.data

    def write(self, symbol, data, metadata=None):
        self.data[symbol] = data
        self.metadata[symbol] = metadata

    def update(self, symbol, data, metadata=None):
        current = self.data.get(symbol, pd.DataFrame())
        combined = pd.concat([current, data])
        self.data[symbol] = combined[
            ~combined.index.duplicated(keep="last")
        ].sort_index()
        self.metadata[symbol] = metadata

    def get_description(self, symbol):
        index = self.data[symbol].index
        return SimpleNamespace(date_range=(index.min(), index.max()))

    def tail(self, symbol, n=1):
        return SimpleNamespace(data=self.data[symbol].tail(n))


class FakeConnection:
    library_name = "test"

    def __init__(self):
        self.libraries = {
            "1m": FakeLibrary(),
            "1h": FakeLibrary(),
            "D": FakeLibrary(),
            "W": FakeLibrary(),
            "M": FakeLibrary(),
        }

    def list_libraries(self):
        return [
            "test.min1",
            "test.min60",
            "test",
            "test.week",
            "test.month",
        ]

    def create_library(self, *_args, **_kwargs):
        raise AssertionError("libraries already exist")

    def get_library(self, timeframe="D"):
        return self.libraries[timeframe]


class FakeMarketManager:
    exchange_id = "binance"

    def fetch_data(self, **kwargs):
        start = pd.Timestamp(kwargs["start_date"])
        index = pd.DatetimeIndex([start], name="Datetime")
        return pd.DataFrame(
            {
                "Open": [1.0],
                "High": [2.0],
                "Low": [0.5],
                "Close": [1.5],
                "Volume": [10.0],
            },
            index=index,
        )


def test_crypto_sync_writes_hourly_and_daily_libraries():
    connection = FakeConnection()
    manager = FakeMarketManager()
    engine = DataSyncEngine(
        connection=connection,
        market_manager_factory=lambda **_kwargs: manager,
    )
    meta = SymbolMeta(
        symbol="BTC/USDT",
        name="BTC/USDT",
        asset_type="Crypto",
        exchange="binance",
        market_type="spot",
        currency="USDT",
    )

    rows = engine.sync_symbol(meta)

    assert rows == 2
    assert connection.libraries["1h"].has_symbol("BTC/USDT")
    assert connection.libraries["D"].has_symbol("BTC/USDT")
    assert (
        connection.libraries["D"].metadata["BTC/USDT"]["source"]
        == "CCXT:binance"
    )


def test_equity_exchange_code_is_not_passed_to_ccxt():
    connection = FakeConnection()
    manager = FakeMarketManager()
    factory_calls = []

    def factory(**kwargs):
        factory_calls.append(kwargs)
        return manager

    engine = DataSyncEngine(
        connection=connection,
        market_manager_factory=factory,
    )
    meta = SymbolMeta(
        symbol="SPCX",
        name="SPCX",
        asset_type="Equity",
        exchange="NMS",
        currency="USD",
    )

    rows = engine.sync_symbol(meta)

    assert rows == 1
    assert factory_calls == [{}]
    assert connection.libraries["D"].has_symbol("SPCX")
    assert (
        connection.libraries["D"].metadata["SPCX"]["source"] == "Yahoo Finance"
    )


def test_existing_yfinance_schema_is_preserved_during_update():
    connection = FakeConnection()
    daily = connection.libraries["D"]
    daily.data["AAPL"] = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [101.0],
            "Low": [99.0],
            "Close": [100.5],
            "Adj Close": [100.25],
            "Volume": [1000],
            "Dividends": [0.0],
            "Stock Splits": [0.0],
        },
        index=pd.DatetimeIndex(
            ["2024-01-02T00:00:00Z"],
            name="Date",
        ),
    )
    manager = FakeMarketManager()
    engine = DataSyncEngine(
        connection=connection,
        market_manager_factory=lambda: manager,
    )
    meta = SymbolMeta(
        symbol="AAPL",
        name="Apple",
        asset_type="Equity",
        exchange="NMS",
        currency="USD",
    )

    rows = engine.sync_symbol(meta)
    result = daily.data["AAPL"]

    assert rows == 1
    assert result.index.name == "Date"
    assert list(result.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
        "Dividends",
        "Stock Splits",
    ]
    new_row = result.iloc[0]
    assert new_row["Adj Close"] == new_row["Close"]
    assert new_row["Dividends"] == 0.0
    assert new_row["Stock Splits"] == 0.0
