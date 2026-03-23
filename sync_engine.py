import os

import pandas as pd
import pandas_ta as ta  # noqa
import streamlit as st
import yfinance as yf
from arcticdb.options import LibraryOptions
from dotenv import load_dotenv

from database.connections.arcticdb_conn import ArcticDBConnection

load_dotenv()

LIBRARY_NAME = os.getenv("LIBRARY_NAME")


class DataSyncEngine:
    def __init__(self):
        self.ac = st.connection("arcticdb", type=ArcticDBConnection)
        self.library_name = self._secrets.get("library")
        self.libraries = {
            "1m": f"{self.library_name}.min1",
            "1h": f"{self.library_name}.min60",
            "D": f"{self.library_name}",
        }
        self._ensure_libraries()

    def _ensure_libraries(self):
        for lib in self.libraries.values():
            if lib not in self.ac.list_libraries():
                self.ac.create_library(
                    lib, library_options=LibraryOptions(dynamic_schema=True)
                )

    def fetch_from_api(self, symbol, start_dt=None) -> pd.DataFrame:
        """
        这里对接你的数据源 (如 yfinance, AkShare, ccxt 等)
        模拟返回从 start_dt 至今的 DataFrame
        """
        # 示例：import yfinance as yf; return yf.download(...)
        ticker = yf.Ticker(symbol)
        hist_data = ticker.history(
            period="5d",
            interval="1m",
            auto_adjust=False,
        )
        return hist_data

    def sync_symbol(self, symbol) -> int:
        lib_1m = self.ac.get_library(self.libraries["1m"])

        # 1. 查找断点
        # if symbol in lib_1m.list_symbols():
        #     last_dt = lib_1m.get_description(symbol).date_range[1]
        #     # start_fetch = last_dt + timedelta(minutes=1)
        #     start_fetch = last_dt
        # else:
        #     start_fetch = datetime.now() - timedelta(
        #         days=7
        #     )  # 初次抓取最近一年

        # 2. 抓取最细粒度数据 (1min)
        new_data_1m = self.fetch_from_api(symbol)

        if new_data_1m is not None and not new_data_1m.empty:
            # 3. 写入 1min 库 (使用 append)
            if lib_1m.has_symbol(symbol):
                lib_1m.update(symbol, new_data_1m.sort_index())
            else:
                lib_1m.append(symbol, new_data_1m.sort_index())

            # 4. 优雅的级联更新：合成高频率数据并存储
            self._resample_and_store(symbol, new_data_1m)
            return new_data_1m.shape[0]
        return 0

    def _resample_and_store(self, symbol: str, df_1m: pd.DataFrame):
        """将 1m 数据合成 1h 和 Daily 并追加"""
        for tf, lib_name in [
            ("1h", self.libraries["1h"]),
            ("D", self.libraries["D"]),
        ]:
            resampled: pd.DataFrame = (
                df_1m.resample(tf)
                .agg(
                    {
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Adj Close": "last",
                        "Volume": "sum",
                        "Dividends": "sum",
                        "Stock Splits": "sum",
                    }
                )
                .dropna()
            )
            if tf == "D":
                resampled.index.name = "Date"

            if not resampled.empty:
                # 注意：这里用 update 比 append 更稳，因为 resample 可能会产生重叠的边界
                lib = self.ac.get_library(lib_name)
                metadata = {
                    "source": "Yahoo Finance",
                    "retrieval_date": pd.Timestamp.now(),
                }
                if lib.has_symbol(symbol):
                    try:
                        lib.update(
                            symbol, resampled.sort_index(), metadata=metadata
                        )
                    except Exception:
                        pass
                else:
                    lib.append(
                        symbol, resampled.sort_index(), metadata=metadata
                    )


if __name__ == "__main__":
    data_sync = DataSyncEngine()
    data_sync.sync_symbol("IBIT")
    # data_sync.sync_symbols()
