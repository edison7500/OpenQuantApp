import datetime
import logging
import os
import time
from pathlib import Path
from typing import Any

import ccxt
import pandas as pd
import yfinance as yf

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "market_data.log"

logger = logging.getLogger("market-data")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


class MarketDataError(RuntimeError):
    """Raised when a market data provider cannot return valid data."""


class MarketDataManager:
    """Fetch and normalize public OHLCV data from yfinance or CCXT."""

    _YFINANCE_ASSET_TYPES = {
        "equity",
        "etf",
        "index",
        "currency",
        "futures",
        "option",
        "mutual fund",
    }
    _TIMEFRAME_MAP = {
        "1m": "1m",
        "1h": "1h",
        "1d": "1d",
        "D": "1d",
    }

    def __init__(
        self,
        crypto_exchange: str = "binance",
        market_type: str = "spot",
        exchange_instance: Any | None = None,
        max_pages: int = 500,
        max_retries: int = 3,
    ):
        self.exchange_id = crypto_exchange.lower()
        self.market_type = market_type.lower()
        self.max_pages = max_pages
        self.max_retries = max_retries
        self._exchange = exchange_instance

        if self.market_type != "spot":
            raise ValueError("第一阶段仅支持 CCXT 现货市场")

    @property
    def crypto_exchange(self):
        """Lazily create one exchange instance so its rate limiter is reused."""
        if self._exchange is None:
            if self.exchange_id not in ccxt.exchanges:
                raise ValueError(f"ccxt 不支持该交易所: {self.exchange_id}")
            exchange_class = getattr(ccxt, self.exchange_id)
            self._exchange = exchange_class(
                {
                    "enableRateLimit": True,
                    "timeout": 20_000,
                    # CCXT defaults this to False. Enable the user's
                    # HTTP(S)_PROXY environment (for example ClashX).
                    "requests_trust_env": True,
                    "options": {
                        "defaultType": self.market_type,
                        # CCXT otherwise loads derivatives endpoints too.
                        "fetchMarkets": {"types": [self.market_type]},
                    },
                }
            )
        return self._exchange

    @classmethod
    def _normalize_timeframe(cls, timeframe: str) -> str:
        try:
            return cls._TIMEFRAME_MAP[timeframe]
        except KeyError as exc:
            supported = ", ".join(cls._TIMEFRAME_MAP)
            raise ValueError(
                f"不支持的周期 {timeframe!r}，可用周期: {supported}"
            ) from exc

    @staticmethod
    def _to_utc(value: datetime.datetime) -> datetime.datetime:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")
        return timestamp.to_pydatetime()

    def inspect_crypto_market(self, symbol: str) -> dict[str, Any]:
        """Validate a public spot market and return normalized metadata."""
        exchange = self.crypto_exchange
        started_at = time.monotonic()
        proxy_enabled = any(
            os.environ.get(name)
            for name in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
            )
        )
        logger.info(
            "Loading markets exchange=%s type=%s symbol=%s proxy=%s",
            self.exchange_id,
            self.market_type,
            symbol.upper(),
            "configured" if proxy_enabled else "not-configured",
        )
        try:
            markets = exchange.load_markets()
        except ccxt.BaseError as exc:
            logger.exception(
                "Market loading failed exchange=%s error_type=%s",
                self.exchange_id,
                type(exc).__name__,
            )
            raise MarketDataError(
                f"{self.exchange_id} 市场列表加载失败"
                f" ({type(exc).__name__}): {exc}"
            ) from exc

        market = markets.get(symbol.upper())
        if market is None:
            logger.warning(
                "Spot symbol not found exchange=%s symbol=%s",
                self.exchange_id,
                symbol.upper(),
            )
            raise ValueError(
                f"{self.exchange_id} 不存在现货交易对 {symbol.upper()}"
            )
        if not market.get("spot", market.get("type") == "spot"):
            logger.warning(
                "Non-spot symbol rejected exchange=%s symbol=%s",
                self.exchange_id,
                symbol.upper(),
            )
            raise ValueError(f"{symbol.upper()} 不是现货交易对")

        logger.info(
            "Markets loaded exchange=%s count=%s elapsed=%.3fs",
            self.exchange_id,
            len(markets),
            time.monotonic() - started_at,
        )
        return {
            "symbol": market["symbol"],
            "name": f"{market['base']}/{market['quote']}",
            "asset_type": "Crypto",
            "exchange": self.exchange_id,
            "market_type": "spot",
            "currency": market["quote"],
        }

    def fetch_data(
        self,
        symbol: str,
        asset_type: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str = "1d",
        exclude_incomplete: bool = True,
    ) -> pd.DataFrame:
        """Return UTC-indexed OHLCV columns for all supported providers."""
        start_date = self._to_utc(start_date)
        end_date = self._to_utc(end_date)
        if start_date >= end_date:
            raise ValueError("start_date 必须早于 end_date")

        interval = self._normalize_timeframe(timeframe)
        asset_type = asset_type.lower()
        if asset_type == "crypto":
            logger.info(
                "Fetching OHLCV exchange=%s symbol=%s timeframe=%s "
                "start=%s end=%s",
                self.exchange_id,
                symbol,
                interval,
                start_date.isoformat(),
                end_date.isoformat(),
            )
            frame = self._fetch_crypto(
                symbol,
                start_date,
                end_date,
                interval,
                exclude_incomplete=exclude_incomplete,
            )
            logger.info(
                "OHLCV fetched exchange=%s symbol=%s timeframe=%s rows=%s",
                self.exchange_id,
                symbol,
                interval,
                len(frame),
            )
            return frame
        if asset_type in self._YFINANCE_ASSET_TYPES:
            return self._fetch_tradfi(symbol, start_date, end_date, interval)
        raise ValueError(f"不支持的资产类型: {asset_type}")

    def _fetch_tradfi(
        self,
        symbol: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str,
    ) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval=timeframe,
            auto_adjust=False,
        )
        if df.empty:
            return self._empty_frame()

        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = set(required).difference(df.columns)
        if missing:
            raise MarketDataError(
                f"Yahoo Finance 返回缺少字段: {sorted(missing)}"
            )

        optional = [
            column
            for column in ("Adj Close", "Dividends", "Stock Splits")
            if column in df.columns
        ]
        df = df[required + optional].copy()
        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = "Datetime"
        return self._clean_frame(df, start_date, end_date)

    def _fetch_crypto(
        self,
        symbol: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str,
        exclude_incomplete: bool,
    ) -> pd.DataFrame:
        exchange = self.crypto_exchange
        market = self.inspect_crypto_market(symbol)

        if not exchange.has.get("fetchOHLCV"):
            raise MarketDataError(f"{self.exchange_id} 不支持 fetch_ohlcv")
        if exchange.timeframes and timeframe not in exchange.timeframes:
            raise ValueError(f"{self.exchange_id} 不支持 {timeframe} K 线")

        since_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        timeframe_ms = int(exchange.parse_timeframe(timeframe) * 1000)
        rows: list[list[float]] = []

        for _ in range(self.max_pages):
            page = self._fetch_ohlcv_page(
                market["symbol"], timeframe, since_ms
            )
            if not page:
                break

            last_timestamp = int(page[-1][0])
            if last_timestamp < since_ms:
                raise MarketDataError(
                    "CCXT 分页时间戳没有前进，已停止以避免死循环"
                )

            rows.extend(page)
            if last_timestamp >= end_ms:
                break
            since_ms = last_timestamp + 1
        else:
            raise MarketDataError(f"CCXT 分页超过上限 {self.max_pages} 页")

        if not rows:
            return self._empty_frame()

        df = pd.DataFrame(
            rows,
            columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"],
        )
        df["Datetime"] = pd.to_datetime(
            df.pop("Timestamp"), unit="ms", utc=True
        )
        df.set_index("Datetime", inplace=True)

        if exclude_incomplete:
            now_ms = int(exchange.milliseconds())
            closed_before_ms = min(end_ms, now_ms)
            close_times = df.index.view("int64") // 1_000_000 + timeframe_ms
            df = df[close_times <= closed_before_ms]

        return self._clean_frame(df, start_date, end_date)

    def _fetch_ohlcv_page(
        self, symbol: str, timeframe: str, since_ms: int
    ) -> list[list[float]]:
        for attempt in range(self.max_retries + 1):
            try:
                return self.crypto_exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    since=since_ms,
                    limit=1000,
                )
            except (
                ccxt.NetworkError,
                ccxt.RequestTimeout,
                ccxt.RateLimitExceeded,
            ) as exc:
                if attempt >= self.max_retries:
                    logger.exception(
                        "OHLCV retries exhausted exchange=%s symbol=%s "
                        "timeframe=%s error_type=%s",
                        self.exchange_id,
                        symbol,
                        timeframe,
                        type(exc).__name__,
                    )
                    raise MarketDataError(
                        f"CCXT 网络请求重试失败: {exc}"
                    ) from exc
                logger.warning(
                    "Retrying OHLCV exchange=%s symbol=%s timeframe=%s "
                    "attempt=%s error_type=%s",
                    self.exchange_id,
                    symbol,
                    timeframe,
                    attempt + 1,
                    type(exc).__name__,
                )
                time.sleep(min(2**attempt, 8))
            except ccxt.BaseError as exc:
                logger.exception(
                    "OHLCV request failed exchange=%s symbol=%s "
                    "timeframe=%s error_type=%s",
                    self.exchange_id,
                    symbol,
                    timeframe,
                    type(exc).__name__,
                )
                raise MarketDataError(f"CCXT 请求失败: {exc}") from exc
        return []

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        frame = pd.DataFrame(
            columns=["Open", "High", "Low", "Close", "Volume"]
        )
        frame.index = pd.DatetimeIndex([], tz="UTC", name="Datetime")
        return frame

    @staticmethod
    def _clean_frame(
        df: pd.DataFrame,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> pd.DataFrame:
        df = df[~df.index.duplicated(keep="last")].sort_index()
        return df.loc[(df.index >= start_date) & (df.index <= end_date)]
