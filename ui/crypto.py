import pandas as pd
import streamlit as st

from api.fear_greed import FearGreedError
from database.resource import get_arctic_library, get_symbol_meta
from engine import load_and_process_full_pipeline
from sync_engine import DataSyncEngine
from ui.components.analysis_tabs import render_analysis_tabs
from ui.components.etf_flows import render_btc_etf_flows
from ui.components.fear_greed import load_fear_greed, render_fear_greed
from ui.components.fragments import ai_analysis_sidebar_fragment
from ui.components.sidebar import render_common_sidebar
from utils.human_readable import format_human_readable


def _render_market_summary(symbol: str, timeframe: str) -> None:
    meta = get_symbol_meta(symbol)
    st.subheader(f"{meta.name} ({meta.symbol})")
    st.caption(
        f"CCXT · {(meta.exchange or 'binance').upper()} · "
        f"{(meta.market_type or 'spot').upper()}"
    )

    try:
        lib = get_arctic_library(timeframe)
        hist = lib.read(symbol).data.tail(2)
    except Exception:
        hist = pd.DataFrame()

    if hist.empty:
        st.info("尚无本地行情，请先执行同步。")
        return

    latest = hist.iloc[-1]
    delta = None
    if len(hist) > 1 and hist["Close"].iloc[-2]:
        delta = ((latest["Close"] / hist["Close"].iloc[-2]) - 1) * 100

    st.metric(
        "收盘价",
        f"{latest['Close']:,.6g} {meta.currency or ''}",
        delta=f"{delta:.2f}%" if delta is not None else None,
    )
    st.metric("成交量", format_human_readable(latest["Volume"]))
    col_high, col_low = st.columns(2)
    col_high.metric("最高", f"{latest['High']:,.6g}")
    col_low.metric("最低", f"{latest['Low']:,.6g}")


def main():
    st.set_page_config(
        page_title="Crypto Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    params = render_common_sidebar(asset_type="crypto")
    symbol = params["symbol"]
    date_selection = params["date_range"]
    timeframe = params["timeframe"]
    rsi_length = params["rsi_length"]

    fear_greed = None
    fear_greed_error = None
    try:
        fear_greed = load_fear_greed()
    except FearGreedError as exc:
        fear_greed_error = str(exc)

    with st.sidebar:
        if st.button("⬇️ 同步当前 Crypto 行情", type="primary"):
            meta = get_symbol_meta(symbol)
            with st.spinner(
                f"正在从 {(meta.exchange or 'binance').upper()} 同步..."
            ):
                try:
                    rows = DataSyncEngine().sync_symbol(meta)
                    load_and_process_full_pipeline.clear()
                    get_arctic_library.clear()
                    st.success(f"同步完成，处理 {rows} 行数据")
                except Exception as exc:
                    st.error(f"同步失败：{exc}")

    col_main, col_summary = st.columns([3, 1])
    hist = pd.DataFrame()
    with col_main:
        if symbol and len(date_selection) == 2:
            start_date, end_date = date_selection
            with st.spinner(f"正在从 ArcticDB 加载 {symbol}..."):
                hist = load_and_process_full_pipeline(
                    symbol,
                    start_date,
                    end_date,
                    asset_type="crypto",
                    timeframe=timeframe,
                    rsi_length=rsi_length,
                )
            if hist.empty:
                st.info("所选时间范围暂无数据，请先同步行情。")
            else:
                render_analysis_tabs(
                    hist,
                    symbol,
                    use_ha=params["use_ha"],
                )
        else:
            st.info("请选择完整的开始和结束日期范围。")

        if symbol.upper().startswith("BTC/"):
            render_btc_etf_flows()

    with col_summary:
        _render_market_summary(symbol, timeframe)
        if fear_greed is not None:
            render_fear_greed(fear_greed)
        elif fear_greed_error:
            st.warning(f"贪婪指数暂不可用：{fear_greed_error}")
        ai_analysis_sidebar_fragment(
            symbol,
            hist,
            asset_type="crypto",
            market_sentiment=fear_greed,
        )


if __name__ == "__main__":
    main()
