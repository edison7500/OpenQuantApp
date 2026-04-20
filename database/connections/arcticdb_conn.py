from functools import cached_property
from typing import List

from arcticdb import Arctic
from streamlit.connections import BaseConnection


class ArcticDBConnection(BaseConnection[Arctic]):
    """ArcticDB 链接管理器"""

    def _connect(self, **kwargs) -> Arctic:
        # 优先从 kwargs 获取，其次从 st.secrets 获取
        uri = (
            kwargs.get("url")
            or self._secrets.get("url")
            or "lmdb://./arctic_db"
        )
        return Arctic(uri)

    @cached_property
    def library_name(self) -> str:
        _library_name = self._secrets.get("library")
        assert _library_name is not None
        return _library_name

    def cursor(self) -> Arctic:
        return self._instance

    def create_library(self, lib, library_options):
        self._instance.create_library(
            lib,
            library_options,
        )

    def get_library(self, timeframe: str = "D", create_if_missing=False):
        # library_name = self._secrets.get("library")
        libraries = {
            "1m": f"{self.library_name}.min1",
            "1h": f"{self.library_name}.min60",
            "D": f"{self.library_name}",
            "W": f"{self.library_name}.week",
            "M": f"{self.library_name}.month",
        }
        return self._instance.get_library(
            libraries[timeframe], create_if_missing
        )

    def list_libraries(self) -> List[str]:
        return self._instance.list_libraries()
