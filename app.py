# import pytz
import streamlit as st

if __name__ == "__main__":
    equity = st.Page("ui/equity.py", title="Stock")
    index = st.Page("ui/indices.py", title="指数")
    etf = st.Page("ui/etf.py", title="ETF")
    cron = st.Page("tools/cron.py", title="自动化行情同步任务")
    asset_manager = st.Page("tools/asset_manager.py", title="资产管理")

    pg = st.navigation(
        {
            "📈 量化投研 Dashboard": [equity, index, etf],
            "Tools": [cron, asset_manager],
        }
    )
    pg.run()
