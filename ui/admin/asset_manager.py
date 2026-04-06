import streamlit as st
import yfinance as yf
from datetime import datetime

from database.manager import DatabaseManager
from database.models import SymbolMeta


def main():
    st.set_page_config(
        page_title="资产管理",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.title("资产管理")

    # 初始化数据库管理器
    db_manager = DatabaseManager()

    # 侧边栏：添加新资产
    with st.sidebar:
        st.header("添加新资产")

        # 使用 session_state 存储获取到的资产信息
        if "pending_asset" not in st.session_state:
            st.session_state.pending_asset = None

        symbol_input = (
            st.text_input(
                "代码 (Symbol)",
                placeholder="例如：AAPL, QQQ, SPY",
                key="symbol_input",
            )
            .strip()
            .upper()
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("获取信息", width="stretch"):
                if not symbol_input:
                    st.error("请输入资产代码")
                else:
                    with st.spinner("正在从 Yahoo Finance 获取信息..."):
                        try:
                            ticker = yf.Ticker(symbol_input)
                            info = ticker.info

                            if not info:
                                st.error(
                                    "无法获取该资产信息，请检查代码是否正确"
                                )
                            else:
                                # 存储到 session_state
                                st.session_state.pending_asset = {
                                    "symbol": symbol_input,
                                    "name": info.get("displayName")
                                    or info.get("shortName", ""),
                                    "asset_type": info.get(
                                        "typeDisp", "Equity"
                                    ),
                                    "sector": info.get("sector"),
                                    "industry": info.get("industry"),
                                    "exchange": info.get("exchange"),
                                    "currency": info.get("currency", "USD"),
                                }
                                st.success("找到资产信息")
                        except Exception as e:
                            st.error(f"获取信息失败：{str(e)}")

        with col2:
            if st.button("清空", use_container_width=True):
                st.session_state.pending_asset = None
                st.rerun()

        # 显示预览和确认添加
        if st.session_state.pending_asset:
            asset = st.session_state.pending_asset
            st.divider()
            st.markdown("**资产信息预览**")
            st.json(
                {
                    "代码": asset["symbol"],
                    "名称": asset["name"],
                    "资产类型": asset["asset_type"],
                    "板块": asset["sector"] or "-",
                    "行业": asset["industry"] or "-",
                    "交易所": asset["exchange"] or "-",
                    "货币": asset["currency"],
                }
            )

            if st.button("确认添加", type="primary", use_container_width=True):
                try:
                    new_symbol = SymbolMeta(
                        symbol=asset["symbol"],
                        name=asset["name"],
                        asset_type=asset["asset_type"],
                        sector=asset["sector"],
                        industry=asset["industry"],
                        exchange=asset["exchange"],
                        currency=asset["currency"],
                        is_active=True,
                        updated_at=datetime.now(),
                    )
                    db_manager.create_symbol_meta(new_symbol)
                    st.success(f"资产 {asset['symbol']} 添加成功！")
                    st.session_state.pending_asset = None
                    st.rerun()
                except Exception as e:
                    st.error(f"添加失败：{str(e)}")

    # 主区域：搜索和表格
    col_search, col_filter = st.columns([3, 1])

    with col_search:
        search_query = st.text_input(
            "搜索",
            placeholder="输入代码或名称进行搜索...",
            label_visibility="collapsed",
        )

    with col_filter:
        asset_type_filter = st.selectbox(
            "资产类型筛选",
            options=["全部", "Equity", "ETF", "Index", "Crypto"],
            index=0,
        )

    # 获取数据
    all_assets = db_manager.get_all_symbolmetas()

    if all_assets:
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "代码": a.symbol,
                    "名称": a.name,
                    "资产类型": a.asset_type,
                    "板块": a.sector or "-",
                    "行业": a.industry or "-",
                    "交易所": a.exchange or "-",
                    "货币": a.currency or "-",
                    "状态": "活跃" if a.is_active else "非活跃",
                    "更新时间": a.updated_at.strftime("%Y-%m-%d %H:%M")
                    if a.updated_at
                    else "-",
                }
                for a in all_assets
            ]
        )

        # 筛选
        if search_query:
            query = search_query.upper()
            df = df[
                df["代码"].str.contains(query, case=False)
                | df["名称"].str.contains(query, case=False)
            ]

        if asset_type_filter != "全部":
            df = df[df["资产类型"] == asset_type_filter]

        # 显示表格
        st.subheader(f"资产列表 ({len(df)} 条)")

        if not df.empty:
            # 使用 session_state 存储选择状态
            if "delete_selection" not in st.session_state:
                st.session_state.delete_selection = []

            # 添加删除列
            df_display = df.copy()
            df_display["删除"] = [False] * len(df_display)

            # 显示带复选框的表格
            edited_df = st.data_editor(
                df_display,
                use_container_width=True,
                height=400,
                column_config={
                    "删除": st.column_config.CheckboxColumn(
                        "删除",
                        help="勾选要删除的资产",
                        default=False,
                    ),
                },
                disabled=[col for col in df.columns if col != "删除"],
                key="asset_table",
            )

            # 底部操作区
            st.divider()
            col1, col2 = st.columns([1, 3])

            with col1:
                selected_for_delete = edited_df[edited_df["删除"]][
                    "代码"
                ].tolist()
                st.write(
                    f"已选择 **{len(selected_for_delete)}** 个资产进行删除"
                )

            with col2:
                if st.button(
                    "💾 保存更改", type="primary", use_container_width=True
                ):
                    if selected_for_delete:
                        try:
                            for sym in selected_for_delete:
                                db_manager.delete_symbol(sym)
                            st.success(
                                f"已删除 {len(selected_for_delete)} 个资产"
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除失败：{str(e)}")
                    else:
                        st.info("没有选择要删除的资产")
        else:
            st.info("暂无匹配的资产数据")
    else:
        st.info("暂无资产数据，请在侧边栏添加新资产。")


if __name__ == "__main__":
    main()
