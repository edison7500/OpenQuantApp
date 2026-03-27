# import pytz
import streamlit as st

if __name__ == "__main__":
    equity = st.Page("dash/equity.py", title="Stock")
    index = st.Page("dash/index.py", title="指数")
    cron = st.Page("tools/cron.py", title="自动化行情同步任务")

    pg = st.navigation(
        {
            "📈 量化投研 Dashboard": [equity, index],
            "Tools": [cron],
        }
    )
    pg.run()
