from typing import Optional, List
import streamlit as st

from database.connections.arcticdb_conn import ArcticDBConnection
from database.manager import DatabaseManager


# ==========================================
# 1. 数据库连接层 (全局缓存)
# ==========================================
@st.cache_resource
def get_arctic_library(timeframe: str = "D"):
    """Initialize and return ArcticDB connection"""
    ac = st.connection("arcticdb", type=ArcticDBConnection)
    lib = ac.get_library(timeframe, create_if_missing=True)
    return lib


@st.cache_resource
def get_sql_connection():
    conn = st.connection("quant_db", type="sql")
    return conn


@st.cache_data(ttl=3600)
def get_symbols(asset_type: str = "Equity") -> Optional[List]:
    symbols = DatabaseManager(conn=get_sql_connection()).get_active_symbols(
        asset_type
    )

    return symbols


@st.cache_data(ttl=3600)
def get_symbol_meta(symbol: str):
    symbol_meta = DatabaseManager(conn=get_sql_connection()).get_symbol_meta(
        symbol
    )
    return symbol_meta
