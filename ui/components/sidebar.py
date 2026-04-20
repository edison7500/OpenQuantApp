import datetime

import pytz
import streamlit as st

from database.resource import get_symbols
from engine import calculate_drawdown, load_and_process_full_pipeline


def render_common_sidebar(asset_type="equity") -> dict:
    """
    通用側邊欄：處理符號選擇、日期、週期等參數。
    回傳一個包含所有設定的字典。
    """
    with st.sidebar:
        st.header(f"{asset_type.upper()} 參數設置")

        # 1. 獲取標的列表 (可根據 asset_type 過濾)
        # 注意: get_symbols 默認是 "Equity"，所以需要傳入對應的 asset_type
        # 這裡做一個簡單的轉換，確保首字母大寫以符合 database/resource.py 的預期
        if asset_type.lower() == "etf":
            portfolio = get_symbols(asset_type="ETF")
            #     portfolio_f = get_symbols(asset_type="Futures") or []
            #     portfolio_o = get_symbols(asset_type="Option") or []
            #     portfolio = portfolio_f + portfolio_o
        else:
            db_asset_type = asset_type.capitalize()
            portfolio = get_symbols(asset_type=db_asset_type)

        if not portfolio:
            st.error(f"無法獲取 {asset_type} 的標的列表")
            st.stop()

        symbol = st.selectbox(
            "選擇分析標的", options=portfolio, key=f"{asset_type}_symbol"
        )

        # 2. 日期範圍
        now = datetime.datetime.now(tz=pytz.UTC)
        default_start = now - datetime.timedelta(days=180)
        date_selection = st.date_input(
            "選擇時間範圍",
            value=(default_start, now),
            max_value=now + datetime.timedelta(days=1),
            key=f"{asset_type}_date",
        )

        # 3. 技術參數
        tf_display = ["日线", "周线", "月线"]
        tf_keys = ["D", "W", "M"]
        tf_selection = st.select_slider(
            "TimeFrame", options=tf_display, value="日线"
        )
        timeframe = tf_keys[tf_display.index(tf_selection)]

        rsi_length = st.slider("RSI 週期", min_value=5, max_value=30, value=14)

        # --- 圖表視覺化選項 ---
        st.markdown("---")
        st.subheader("視覺化設置")
        use_ha = st.checkbox("🕯️ 使用 Heikin-Ashi K线", value=False)

        # 4. 數據維護按鈕
        if st.button("🔄 強制刷新數據"):
            # 這裡調用你原本的 clear 邏輯
            get_symbols.clear()
            load_and_process_full_pipeline.clear()
            calculate_drawdown.clear()
            st.rerun()

        # 確保回傳完整的選擇
        return {
            "symbol": symbol,
            "date_range": date_selection,
            "timeframe": timeframe,
            "rsi_length": rsi_length,
            "use_ha": use_ha,
        }
