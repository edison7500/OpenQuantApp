import datetime
import logging
from collections.abc import Callable, Iterable

import pandas as pd
import streamlit as st
from arcticdb.options import LibraryOptions
from dotenv import load_dotenv

from api.market_manager import MarketDataManager
from database.connections.arcticdb_conn import ArcticDBConnection
from database.manager import DatabaseManager
from database.models import SymbolMeta

load_dotenv()

logger = logging.getLogger(__name__)


class DataSyncEngine:
    """Synchronize public market OHLCV data into ArcticDB."""

    def __init__(
        self,
        connection=None,
        market_manager_factory: Callable[
            ..., MarketDataManager
        ] = MarketDataManager,
    ):
        self.ac = connection or st.connection(
            "arcticdb", type=ArcticDBConnection
        )
        self.market_manager_factory = market_manager_factory
        self.libraries = {
            "1m": f"{self.ac.library_name}.min1",
            "1h": f"{self.ac.library_name}.min60",
            "D": f"{self.ac.library_name}",
            "W": f"{self.ac.library_name}.week",
            "M": f"{self.ac.library_name}.month",
        }
        self._ensure_libraries()

    def _ensure_libraries(self):
        existing = set(self.ac.list_libraries())
        for library_name in self.libraries.values():
            if library_name not in existing:
                self.ac.create_library(
                    library_name,
                    library_options=LibraryOptions(dynamic_schema=True),
                )

    def sync_symbol(
        self,
        symbol_meta: SymbolMeta | str,
        timeframes: Iterable[str] | None = None,
    ) -> int:
        """Incrementally sync one symbol and return written row count."""
        meta = self._resolve_meta(symbol_meta)
        if timeframes is None:
            timeframes = ("1h", "D") if self._is_crypto(meta) else ("D",)

        if self._is_crypto(meta):
            manager = self.market_manager_factory(
                crypto_exchange=(meta.exchange or "binance").lower(),
                market_type=meta.market_type or "spot",
            )
        else:
            # Yahoo exchange codes (for example NMS/XNYS) are not CCXT IDs.
            manager = self.market_manager_factory()

        total_rows = 0
        for timeframe in timeframes:
            total_rows += self._sync_timeframe(meta, timeframe, manager)
        return total_rows

    def _sync_timeframe(
        self,
        meta: SymbolMeta,
        timeframe: str,
        manager: MarketDataManager,
    ) -> int:
        lib = self.ac.get_library(timeframe=timeframe)
        end_date = datetime.datetime.now(datetime.timezone.utc)
        start_date = self._get_start_date(lib, meta.symbol, timeframe, meta)

        data = manager.fetch_data(
            symbol=meta.symbol,
            asset_type=meta.asset_type,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            exclude_incomplete=True,
        )
        if data.empty:
            return 0

        metadata = {
            "source": (
                f"CCXT:{manager.exchange_id}"
                if self._is_crypto(meta)
                else "Yahoo Finance"
            ),
            "asset_type": meta.asset_type,
            "exchange": meta.exchange,
            "market_type": meta.market_type,
            "timeframe": timeframe,
            "retrieval_date": pd.Timestamp.now(tz="UTC"),
        }
        data = data[~data.index.duplicated(keep="last")].sort_index()
        if lib.has_symbol(meta.symbol):
            data = self._align_to_existing_schema(lib, meta.symbol, data)
            lib.update(meta.symbol, data, metadata=metadata)
        else:
            lib.write(meta.symbol, data, metadata=metadata)
        return len(data)

    @staticmethod
    def _align_to_existing_schema(lib, symbol: str, data: pd.DataFrame):
        """Adapt normalized OHLCV to an older ArcticDB stream schema."""
        existing = lib.tail(symbol, n=1).data
        if existing.empty:
            return data

        aligned = data.copy()
        for column in existing.columns:
            if column in aligned.columns:
                continue
            if column == "Adj Close" and "Close" in aligned.columns:
                aligned[column] = aligned["Close"]
            elif pd.api.types.is_integer_dtype(existing[column].dtype):
                aligned[column] = 0
            elif pd.api.types.is_bool_dtype(existing[column].dtype):
                aligned[column] = False
            elif pd.api.types.is_numeric_dtype(existing[column].dtype):
                aligned[column] = 0.0
            else:
                aligned[column] = None

        aligned = aligned.reindex(columns=existing.columns)
        for column, dtype in existing.dtypes.items():
            try:
                aligned[column] = aligned[column].astype(dtype)
            except (TypeError, ValueError):
                logger.warning(
                    "无法对齐字段 dtype：symbol=%s column=%s target=%s",
                    symbol,
                    column,
                    dtype,
                )

        if aligned.index.name != existing.index.name:
            logger.info(
                "对齐 ArcticDB 索引名：symbol=%s %s -> %s",
                symbol,
                aligned.index.name,
                existing.index.name,
            )
            aligned.index.name = existing.index.name
        return aligned

    def _get_start_date(self, lib, symbol: str, timeframe: str, meta):
        overlap = {
            "1m": datetime.timedelta(minutes=1),
            "1h": datetime.timedelta(hours=1),
            "D": datetime.timedelta(days=1),
        }[timeframe]
        if lib.has_symbol(symbol):
            last_date = pd.Timestamp(lib.get_description(symbol).date_range[1])
            if last_date.tzinfo is None:
                last_date = last_date.tz_localize("UTC")
            else:
                last_date = last_date.tz_convert("UTC")
            return (last_date - overlap).to_pydatetime()

        now = datetime.datetime.now(datetime.timezone.utc)
        if self._is_crypto(meta) and timeframe == "1h":
            return now - datetime.timedelta(days=180)
        if self._is_crypto(meta):
            return now - datetime.timedelta(days=365 * 5)
        return now - datetime.timedelta(days=365 * 20)

    @staticmethod
    def _is_crypto(meta: SymbolMeta) -> bool:
        return meta.asset_type.lower() == "crypto"

    @staticmethod
    def _resolve_meta(symbol_meta: SymbolMeta | str) -> SymbolMeta:
        if isinstance(symbol_meta, SymbolMeta):
            return symbol_meta
        meta = DatabaseManager().get_symbol_meta(symbol_meta)
        if meta is None:
            raise ValueError(f"找不到标的元数据: {symbol_meta}")
        return meta


if __name__ == "__main__":
    data_sync = DataSyncEngine()
    data_sync.sync_symbol("NET")
