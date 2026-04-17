import streamlit as st

from engine import (
    calculate_drawdown,
)  # load_and_process_data_with_range,; process_data_with_rvol,
from engine.analytics import calculate_heikin_ashi
from engine.chart_factory import ChartFactory


def render_analysis_tabs(hist, symbol, use_ha=False):
    if hist.empty:
        st.warning(f"暫無 {symbol} 的數據。")
        return

    # 如果开启 Heikin-Ashi，预先计算 HA 价格列
    if use_ha:
        hist = calculate_heikin_ashi(hist)

    # --- 狀態管理：記住當前選中的 Tab ---
    state_key = f"active_tab_{symbol}"
    if state_key not in st.session_state:
        st.session_state[state_key] = "🌀 趨勢通道 (BBands)"

    # 標籤定義
    tabs_titles = [
        "🌀 趨勢通道 (BBands)",
        "📈 指數平滑動態 (MACD)",
        "📊 強弱指標 (RSI)",
        "📊 成交量分析 (RVOL)",
        "💻 策略執行終端",
        "📉 風險回撤分析",
    ]

    # 使用 segmented_control 替代 st.tabs 以保留狀態 (Streamlit 1.35+)
    selected_tab = st.segmented_control(
        "分析視圖",
        options=tabs_titles,
        key=state_key,
    )

    # 1. 趨勢通道 - 最優先看價格所處位置
    if selected_tab == "🌀 趨勢通道 (BBands)":
        fig_bbands = ChartFactory.build_view(
            hist, symbol, view_type="BBands", use_ha=use_ha
        )
        st.plotly_chart(
            fig_bbands,
            width="stretch",
            config={"displayModeBar": False},
        )

    # 2. MACD - 判斷中長期趨勢方向與金叉/死叉
    elif selected_tab == "📈 指數平滑動態 (MACD)":
        fig_macd = ChartFactory.build_advanced_view(
            hist, symbol, view_type="MACD", use_ha=use_ha
        )
        st.plotly_chart(
            fig_macd,
            width="stretch",
            config={"displayModeBar": False},
        )

    # 3. RSI - 判斷短期是否超買或超賣
    elif selected_tab == "📊 強弱指標 (RSI)":
        show_kdj = st.checkbox(
            "📈 显示 KDJ 指标", value=False, key=f"kdj_{symbol}"
        )
        fig_rsi = ChartFactory.build_view(
            hist, symbol, view_type="RSI", use_ha=use_ha, show_kdj=show_kdj
        )
        st.plotly_chart(
            fig_rsi, width="stretch", config={"displayModeBar": False}
        )

    # 4. RVOL - 驗證當前價格波動是否有成交量支持
    elif selected_tab == "📊 成交量分析 (RVOL)":
        fig = ChartFactory.build_view(hist, symbol, "ROVL", use_ha=use_ha)
        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False},
        )

    # 5. 交易終端 - 綜合所有訊號後的執行界面
    elif selected_tab == "💻 策略執行終端":
        # fig_trading_terminal = chart.plot_trading_terminal(hist, symbol)
        fig = ChartFactory.build_view(hist, symbol, "FVG & BAG", use_ha=use_ha)
        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False},
        )

    # 6. 風險回撤 - 最後檢查風險承受度
    elif selected_tab == "📉 風險回撤分析":
        drawdown_series = calculate_drawdown(
            hist["Close"].pct_change(fill_method=None)
        )
        max_dd, current_dd = (
            drawdown_series.min() * 100,
            drawdown_series.iloc[-1] * 100,
        )

        c1, c2 = st.columns(2)
        c1.metric("最大回撤", f"{max_dd:.2f}%")
        c2.metric("當前回撤", f"{current_dd:.2f}%")

        # fig_drawdown = chart.create_drawdown_chart(hist, symbol)
        fig = ChartFactory.build_view(hist, symbol, "DrawDown")
        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False},
        )
