import streamlit as st
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

if __name__ == "__main__":
    equity = st.Page("ui/equity.py", title="股票分析")
    crypto = st.Page("ui/crypto.py", title="Crypto 分析")
    index = st.Page("ui/indices.py", title="指数分析")
    etf = st.Page("ui/etf.py", title="ETF分析")
    future = st.Page("ui/future.py", title="期货分析")
    cron = st.Page("tools/cron.py", title="行情同步")
    notifier = st.Page("tools/telegram_bot.py", title="通知管理")
    asset_manager = st.Page("ui/admin/asset_manager.py", title="资产管理")

    pg = st.navigation(
        {
            "📈 量化投研 Dashboard": [
                equity,
                crypto,
                index,
                etf,
                future,
            ],
            "🛠️ 系统工具": [cron, notifier],
            "⚙️ 管理后台": [asset_manager],
        }
    )

    pg.run()
