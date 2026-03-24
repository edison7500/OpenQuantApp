# import pytz
import streamlit as st

if __name__ == "__main__":
    equity = st.Page("dash/equity.py", title="📈 量化投研 Dashboard")
    cron = st.Page("tools/cron.py", title="自动化行情同步任务")

    pg = st.navigation(
        {
            "Dashboard": [equity],
            "Tools": [cron],
        }
    )
    pg.run()
