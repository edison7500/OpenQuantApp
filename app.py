# import pytz
import streamlit as st
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

if __name__ == "__main__":
    equity = st.Page("ui/equity.py", title="Stock")
    index = st.Page("ui/indices.py", title="Index")
    etf = st.Page("ui/etf.py", title="ETF")
    futuer = st.Page("ui/futuer.py", title="期货")
    cron = st.Page("tools/cron.py", title="自动化行情同步任务")
    asset_manager = st.Page("ui/admin/asset_manager.py", title="资产管理")

    pg = st.navigation(
        {
            "📈 量化投研 Dashboard": [equity, index, etf, futuer],
            "Tools": [cron],
            "Admin": [asset_manager],
        }
    )

    pg.run()
