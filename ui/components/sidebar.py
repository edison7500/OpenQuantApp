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
        db_asset_type = asset_type.capitalize()
        portfolio = get_symbols(asset_type=db_asset_type)
        if not portfolio:
            st.error("無法獲取標的列表")
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
        timeframe = st.select_slider(
            "TimeFrame", options=["1m", "1h", "D"], value="D"
        )
        rsi_length = st.slider("RSI 週期", min_value=5, max_value=30, value=14)

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
        }
