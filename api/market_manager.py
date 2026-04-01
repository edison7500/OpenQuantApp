import datetime

import ccxt
import pandas as pd
import yfinance as yf


class MarketDataManager:
    def __init__(self, crypto_exchange: str = "binance"):
        """
        初始化数据管理器。
        :param crypto_exchange: ccxt 支持的交易所 ID (例如: 'binance', 'okx', 'kraken')
        """
        # 动态初始化 ccxt 交易所实例
        try:
            exchange_class = getattr(ccxt, crypto_exchange)
            # 开启 rate limit 以防触发交易所反爬策略
            self.crypto_exchange = exchange_class({"enableRateLimit": True})
        except AttributeError:
            raise ValueError(f"ccxt 不支持该交易所: {crypto_exchange}")

    def fetch_data(
        self,
        symbol: str,
        asset_type: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str = "1d",
    ) -> pd.DataFrame:
        """
        统一的数据获取接口。无论底层是 yfinance 还是 ccxt，
        都返回带有 DatetimeIndex (UTC时区) 且列名为 [Open, High, Low, Close, Volume] 的标准化 DataFrame。
        """
        asset_type = asset_type.lower()

        if asset_type == "crypto":
            return self._fetch_crypto(symbol, start_date, end_date, timeframe)
        elif asset_type in ["equity", "etf", "index"]:
            return self._fetch_tradfi(symbol, start_date, end_date, timeframe)
        else:
            raise ValueError(f"不支持的资产类型: {asset_type}")

    def _fetch_tradfi(
        self,
        symbol: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str,
    ) -> pd.DataFrame:
        """
        使用 yfinance 获取传统金融数据 (股票、ETF、指数)
        """
        # 统一下游传入的周期与 yfinance 内部周期的映射
        yf_interval_map = {"1m": "1m", "1h": "1h", "1d": "1d", "D": "1d"}
        interval = yf_interval_map.get(timeframe, "1d")

        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval=interval,
            auto_adjust=False,
        )

        if df.empty:
            return df

        # 标准化 1: 仅保留核心的 OHLCV 列
        df = df[["Open", "High", "Low", "Close", "Volume"]]

        # 标准化 2: 统一时区到 UTC (传统金融时区可能因交易所而异)
        if df.index.tz is not None:
            df.index = df.index.tz_convert(datetime.timezone.utc)
        else:
            df.index = df.index.tz_localize(datetime.timezone.utc)

        return df

    def _fetch_crypto(
        self,
        symbol: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str,
    ) -> pd.DataFrame:
        """
        使用 ccxt 获取加密货币数据，内置了自动分页逻辑以应对长周期数据的获取
        """
        # 统一下游传入的周期与 ccxt 内部周期的映射
        ccxt_interval_map = {"1m": "1m", "1h": "1h", "1d": "1d", "D": "1d"}
        interval = ccxt_interval_map.get(timeframe, "1d")

        # ccxt 要求的时间戳是毫秒级的 UTC Unix Timestamp
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=datetime.timezone.utc)
        since_ms = int(start_date.timestamp() * 1000)

        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=datetime.timezone.utc)
        end_ms = int(end_date.timestamp() * 1000)

        all_ohlcv = []

        # CCXT 单次请求通常有 limit 限制 (例如 500 或 1000)，我们需要循环分页拉取
        while True:
            try:
                ohlcv = self.crypto_exchange.fetch_ohlcv(
                    symbol, timeframe=interval, since=since_ms, limit=1000
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # 获取本次请求的最后一条数据的时间戳
                last_timestamp = ohlcv[-1][0]

                # 如果最后一条数据已经到达或超过了我们需要的结束时间，跳出循环
                if last_timestamp >= end_ms:
                    break

                # 将下一次请求的起点设为最后一条时间戳 + 1 毫秒
                since_ms = last_timestamp + 1

            except Exception as e:
                # 生产环境中建议使用 logging 代替 print
                print(f"CCXT 获取 {symbol} 数据时出错: {e}")
                break

        if not all_ohlcv:
            return pd.DataFrame()

        # 转换为 DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"],
        )

        # 标准化: 将毫秒时间戳转为 UTC 的 DatetimeIndex
        df["Datetime"] = pd.to_datetime(df["Timestamp"], unit="ms", utc=True)
        df.set_index("Datetime", inplace=True)
        df.drop(columns=["Timestamp"], inplace=True)

        # 过滤掉超出 end_date 范围的数据（因为批量拉取可能会多拉出几根 K 线）
        df = df[df.index <= end_date]

        return df
