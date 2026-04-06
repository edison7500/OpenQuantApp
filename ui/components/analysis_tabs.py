import streamlit as st

from engine.chart_factory import ChartFactory
from engine import (  # load_and_process_data_with_range,; process_data_with_rvol,
    calculate_drawdown,
)


def render_analysis_tabs(hist, symbol):
    if hist.empty:
        st.warning(f"暫無 {symbol} 的數據。")
        return

    # --- 重新排序後的標籤 ---
    # 1. 趨勢 (BBands) -> 2. 動能 (MACD/RSI) -> 3. 成交量 (RVOL) -> 4. 綜合 (Terminal/Risk)
    tabs_titles = [
        "🌀 趨勢通道 (BBands)",
        "📈 指數平滑動態 (MACD)",
        "📊 強弱指標 (RSI)",
        "📊 成交量分析 (RVOL)",
        "💻 策略執行終端",
        "📉 風險回撤分析",
    ]

    tabs = st.tabs(tabs_titles)

    # 1. 趨勢通道 - 最優先看價格所處位置
    with tabs[0]:
        fig_bbands = ChartFactory.build_view(hist, symbol, view_type="BBands")
        st.plotly_chart(
            fig_bbands,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # 2. MACD - 判斷中長期趨勢方向與金叉/死叉
    with tabs[1]:
        fig_macd = ChartFactory.build_advanced_view(
            hist, symbol, view_type="MACD"
        )
        st.plotly_chart(
            fig_macd,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # 3. RSI - 判斷短期是否超買或超賣
    with tabs[2]:
        fig_rsi = ChartFactory.build_view(hist, symbol, view_type="RSI")
        st.plotly_chart(
            fig_rsi, use_container_width=True, config={"displayModeBar": False}
        )

    # 4. RVOL - 驗證當前價格波動是否有成交量支持
    with tabs[3]:
        fig = ChartFactory.build_view(hist, symbol, "ROVL")
        st.plotly_chart(
            fig, use_container_width=True, config={"displayModeBar": False}
        )

    # 5. 交易終端 - 綜合所有訊號後的執行界面
    with tabs[4]:
        # fig_trading_terminal = chart.plot_trading_terminal(hist, symbol)
        fig = ChartFactory.build_view(hist, symbol, "FVG & BAG")
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # 6. 風險回撤 - 最後檢查風險承受度
    with tabs[5]:
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
            use_container_width=True,
            config={"displayModeBar": False},
        )
