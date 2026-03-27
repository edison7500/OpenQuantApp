import streamlit as st

from database.connections.arcticdb_conn import ArcticDBConnection


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
