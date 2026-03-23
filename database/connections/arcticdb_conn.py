from typing import List

from arcticdb import Arctic
from streamlit.connections import BaseConnection


class ArcticDBConnection(BaseConnection[Arctic]):
    """ArcticDB 链接管理器"""

    def _connect(self, **kwargs) -> Arctic:
        # 优先从 kwargs 获取，其次从 st.secrets 获取
        uri = (
            kwargs.get("uri")
            or self._secrets.get("uri")
            or "lmdb://./arctic_db"
        )
        return Arctic(uri)

    def cursor(self) -> Arctic:
        return self._instance

    def get_library(self, timeframe: str = "D", create_if_missing=False):
        library_name = self._secrets.get("library")
        libraries = {
            "1m": f"{library_name}.min1",
            "1h": f"{library_name}.min60",
            "D": f"{library_name}",
        }
        return self._instance.get_library(
            libraries[timeframe], create_if_missing
        )

    def list_libraries(self) -> List[str]:
        return self._instance.list_libraries()
