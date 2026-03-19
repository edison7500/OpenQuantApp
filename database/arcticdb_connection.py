# import os

# import streamlit as st
from arcticdb import Arctic
from streamlit.connections import BaseConnection
from dotenv import load_dotenv


load_dotenv()


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

    def get_library(self, library_name: str, create_if_missing=False):
        return self._instance.get_library(library_name, create_if_missing)
