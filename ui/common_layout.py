# ui/layouts.py
import streamlit as st

import ui.chart as chart

# from ui.charts import create_rsi_view, create_macd_view


def render_dashboard_tabs(df, symbol):
    tabs = st.tabs(["RVOL", "RSI", "MACD", "Risk", "Terminal"])

    # 建立配置映射，减少重复代码
    plot_map = {
        0: (chart.create_rvol_chart, "RVOL 视图"),
        1: (chart.create_rsi_view, "RSI 指标"),
        2: (chart.create_macd_view_with_signals, "MACD 指标"),
        # ...
    }

    for idx, (func, title) in plot_map.items():
        with tabs[idx]:
            fig = func(df, symbol)
            st.plotly_chart(fig, use_container_width=True)
