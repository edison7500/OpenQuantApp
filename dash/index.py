import pandas as pd
import streamlit as st
from typing import List

from sqlmodel import select

from database.models import SymbolMeta
from database.resource import get_arctic_library, get_sql_connection
from indicators import calculate_drawdown, load_and_process_data_with_range


@st.cache_data(ttl=3600)
def get_symbols(asset_type: str = "Index") -> List[SymbolMeta]:
    conn = get_sql_connection()
    with conn.session as session:
        statement = (
            select(SymbolMeta.symbol)
            .where(SymbolMeta.asset_type == asset_type)
            .order_by(SymbolMeta.symbol)
        )
        return session.execute(statement).scalars().all()


def main():
    st.set_page_config(
        page_title="Index Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )
