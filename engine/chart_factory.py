import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots


class ChartFactory:
    """
    可视化工厂类：负责将指标和信号组装成 Plotly 图表
    """

    @staticmethod
    def _create_base(rows=2, heights=[0.7, 0.3]):
        """内部私有：创建标准画布结构"""
        return make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=heights,
        )

    @staticmethod
    def add_candlestick(fig, df, row=1, use_ha=False):
        """核心组件：绘制 K 线 (支持标准/Heikin-Ashi)"""
        if use_ha:
            # Use HA columns if available, otherwise fallback to standard
            open_col, high_col, low_col, close_col = (
                "HA_Open",
                "HA_High",
                "HA_Low",
                "HA_Close",
            )
            if "HA_Open" not in df.columns:
                # This should be handled by the caller, but for safety:
                return ChartFactory.add_candlestick(
                    fig, df, row=row, use_ha=False
                )
            name = "Heikin-Ashi K线"
        else:
            open_col, high_col, low_col, close_col = (
                "Open",
                "High",
                "Low",
                "Close",
            )
            name = "K线"

        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df[open_col],
                high=df[high_col],
                low=df[low_col],
                close=df[close_col],
                name=name,
            ),
            row=row,
            col=1,
        )

    @staticmethod
    def add_ma_signals(fig, df, row=1):
        """在 K 線圖上標註均線金叉與死叉"""
        # 金叉標註 (綠色圓點)
        buy_sig = df[df["MA_Cross_Buy"]]
        fig.add_trace(
            go.Scatter(
                x=buy_sig.index,
                y=buy_sig["sma_main"],
                mode="markers",
                name="均線金叉",
                marker=dict(
                    symbol="circle",
                    size=10,
                    color="#00FF7F",
                    line=dict(width=2, color="white"),
                ),
            ),
            row=row,
            col=1,
        )

        # 死叉標註 (紅色圓點)
        sell_sig = df[df["MA_Cross_Sell"]]
        fig.add_trace(
            go.Scatter(
                x=sell_sig.index,
                y=sell_sig["sma_main"],
                mode="markers",
                name="均線死叉",
                marker=dict(
                    symbol="circle",
                    size=10,
                    color="#FF4500",
                    line=dict(width=2, color="white"),
                ),
            ),
            row=row,
            col=1,
        )

    @staticmethod
    def add_signal_markers(fig, df, row=1):
        """核心组件：在主图标记买卖点"""
        # 买入信号 (金叉/突破)
        if "Buy_Signal" in df.columns:
            buy_df = df[df["Buy_Signal"]]
            fig.add_trace(
                go.Scatter(
                    x=buy_df.index,
                    y=buy_df["Low"] * 0.98,
                    mode="markers",
                    name="买入",
                    marker=dict(
                        symbol="triangle-up", size=12, color="#00ff00"
                    ),
                ),
                row=row,
                col=1,
            )

        # 卖出信号
        if "Sell_Signal" in df.columns:
            sell_df = df[df["Sell_Signal"]]
            fig.add_trace(
                go.Scatter(
                    x=sell_df.index,
                    y=sell_df["High"] * 1.02,
                    mode="markers",
                    name="卖出",
                    marker=dict(
                        symbol="triangle-down", size=12, color="#ff0000"
                    ),
                ),
                row=row,
                col=1,
            )

    @staticmethod
    def add_volume_analysis(fig, df, symbol) -> None:
        sig_df = df[df["breakout_signal"]]

        fig.add_trace(
            go.Scatter(
                x=sig_df.index,
                y=sig_df["Low"] * 0.98,  # 在最低价下方 2% 处标注
                mode="markers+text",
                name="爆量突破",
                marker=dict(
                    symbol="triangle-up",
                    size=12,
                    color="gold",
                    line=dict(width=2, color="darkorange"),
                ),
                text="💰",  # 也可以直接用 Emoji
                textposition="bottom center",
            ),
            row=1,
            col=1,
        )
        volume_colors = [
            "#26a69a" if close >= open_ else "#ef5350"
            for open_, close in zip(df["Open"], df["Close"], strict=False)
        ]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                marker_color=volume_colors,
                name="成交量",
            ),
            row=2,
            col=1,
        )

        # --- 副图：RVOL 柱状图 ---
        colors = ["#FFA500" if v > 2.0 else "#636EFA" for v in df["rvol"]]
        fig.add_trace(
            go.Bar(x=df.index, y=df["rvol"], marker_color=colors, name="RVOL"),
            row=3,
            col=1,
        )

        # 辅助线
        fig.add_hline(y=1.0, line_dash="dash", line_color="gray", row=3, col=1)
        fig.update_layout(
            title=f"{symbol} - 成交量 / RVOL 视图",
            template="plotly_white",
            xaxis_rangeslider_visible=False,
        )

    @staticmethod
    def add_trading_terminal(fig, df, symbol) -> None:
        # 识别并绘制 BAG (突破缺口 - 物理断层)
        for i in range(1, len(df)):
            # 看涨突破缺口：今日最低 > 昨日最高
            if df["Low"].iloc[i] > df["High"].iloc[i - 1]:
                fig.add_shape(
                    type="rect",
                    x0=df.index[i - 1],
                    x1=df.index[i],
                    y0=df["High"].iloc[i - 1],
                    y1=df["Low"].iloc[i],
                    fillcolor="gold",
                    opacity=0.5,
                    line_width=0,
                    name="BAG",
                )

        # 识别并绘制 FVG (公允价值缺口 - 三棒失衡)
        for i in range(2, len(df)):
            # 看涨 FVG: 第一根(i-2)的高 < 第三根(i)的低
            if df["High"].iloc[i - 2] < df["Low"].iloc[i]:
                # --- 修复逻辑开始 ---
                # 确保延伸的索引不会溢出数据边界
                end_idx_val = min(i + 5, len(df) - 1)
                # --- 修复逻辑结束 ---
                fig.add_shape(
                    type="rect",
                    x0=df.index[i - 2],
                    x1=df.index[end_idx_val],  # 使用安全后的索引
                    y0=df["High"].iloc[i - 2],
                    y1=df["Low"].iloc[i],
                    fillcolor="lightskyblue",
                    opacity=0.3,
                    line_width=0,
                    layer="below",
                )

    @staticmethod
    def add_drawdown(fig, df, symbol, row=2) -> None:
        # 计算回撤
        cumulative = df["Close"] / df["Close"].iloc[0]  # 归一化净值
        running_max = cumulative.cummax()
        drawdown = (cumulative / running_max - 1) * 100  # 转为百分比

        # fig = go.Figure()

        # 绘制回撤填充图 (Waterfall Style)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=drawdown,
                fill="tozeroy",  # 填充到 Y=0
                mode="lines",
                line=dict(color="red", width=0.5),
                fillcolor="rgba(255, 0, 0, 0.3)",  # 半透明红
                name="Drawdown %",
            ),
            row=row,
            col=1,
        )

    @staticmethod
    def add_atr(fig, df, row=2) -> None:
        """绘制可跨资产比较的 ATR 百分比。"""
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["atr_pct"],
                name="ATR %",
                line=dict(color="#FFB347", width=1.5),
            ),
            row=row,
            col=1,
        )

    @staticmethod
    def add_adx(fig, df, row=3) -> None:
        """绘制趋势强度及方向线。"""
        for column, name, color in (
            ("adx_main", "ADX", "#FFD700"),
            ("dmp_main", "+DI", "#26a69a"),
            ("dmn_main", "-DI", "#ef5350"),
        ):
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[column],
                    name=name,
                    line=dict(color=color, width=1.4),
                ),
                row=row,
                col=1,
            )
        fig.add_hline(
            y=25, line_dash="dash", line_color="gray", row=row, col=1
        )

    @staticmethod
    def add_relative_strength(fig, df, row=2) -> None:
        """绘制相对市场基准、起点为 100 的强弱曲线。"""
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["relative_strength"],
                name="相对强弱",
                line=dict(color="#7FDBFF", width=2),
            ),
            row=row,
            col=1,
        )
        fig.add_hline(
            y=100, line_dash="dash", line_color="gray", row=row, col=1
        )

    @staticmethod
    def add_bbands_volatility(fig, df, row=2):
        """组件：绘制 Bollinger Band Width (波动率深度)"""
        bbb_col = [c for c in df.columns if c.startswith("BBB_")][0]

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[bbb_col],
                name="BB Width",
                line=dict(color="#00D2FF", width=1.5),
            ),
            row=row,
            col=1,
        )

        # 添加基准线
        fig.add_hline(y=0, line_dash="dot", line_color="gray", row=row, col=1)

    @staticmethod
    def build_view(
        df: pd.DataFrame,
        symbol: str,
        view_type: str = "MACD",
        height: int = 600,
        use_ha: bool = False,
    ):
        """
        工厂入口：根据类型组装图表
        """
        # 1. 动态确定布局
        if view_type in ["RVOL", "DrawDown"]:
            rows = 3
            heights = [0.6, 0.2, 0.2]
        elif view_type in [
            "MACD",
            "RSI",
            "BBands",
            "RelativeStrength",
        ]:
            rows = 2
            heights = [0.7, 0.3]
        else:
            rows = 1
            heights = [1.0]
        if rows == 3:
            height = max(height, 720)

        fig = ChartFactory._create_base(rows=rows, heights=heights)
        ChartFactory.add_candlestick(fig, df, use_ha=use_ha)

        if view_type == "MACD":
            # 动态寻找 MACD 相关列
            hist = [c for c in df.columns if "MACDh" in c][0]
            line = [c for c in df.columns if "MACD_" in c][0]
            signal = [c for c in df.columns if "MACDs_" in c][0]

            ChartFactory.add_signal_markers(fig, df)

            fig.add_trace(
                go.Bar(x=df.index, y=df[hist], name="柱状图"), row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=df.index, y=df[line], name="MACD线"), row=2, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[signal],
                    name="Signal线",
                    line=dict(dash="dash"),
                ),
                row=2,
                col=1,
            )

        elif view_type == "RSI":
            # Row 2: RSI
            rsi_col = [c for c in df.columns if "RSI" in c][0]
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[rsi_col],
                    name="RSI",
                    line=dict(color="#FFD700", width=2),
                ),
                row=2,
                col=1,
            )

            # 添加 RSI 警戒线
            fig.add_hline(
                y=70, line_dash="dash", line_color="red", row=2, col=1
            )
            fig.add_hline(
                y=30, line_dash="dash", line_color="green", row=2, col=1
            )

        elif view_type == "RVOL":
            ChartFactory.add_volume_analysis(fig, df, symbol)

        elif view_type == "FVG & BAG":
            ChartFactory.add_trading_terminal(fig, df, symbol)

        elif view_type == "DrawDown":
            ChartFactory.add_atr(fig, df, row=2)
            ChartFactory.add_drawdown(fig, df, symbol, row=3)

        elif view_type == "RelativeStrength":
            ChartFactory.add_relative_strength(fig, df, row=2)

        elif view_type == "BBands":
            bb_u = [c for c in df.columns if c.startswith("BBU_")][0]
            bb_m = [c for c in df.columns if c.startswith("BBM_")][0]
            bb_l = [c for c in df.columns if c.startswith("BBL_")][0]

            # 绘制上中下轨
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[bb_u],
                    name="Upper Band",
                    line=dict(color="rgba(173, 216, 230, 0.8)", dash="dash"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[bb_m],
                    name="Middle Band",
                    line=dict(color="rgba(255, 165, 0, 0.8)", dash="dot"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[bb_l],
                    name="Lower Band",
                    line=dict(color="rgba(173, 216, 230, 0.8)", dash="dash"),
                    fill="tonexty",
                    fillcolor="rgba(173, 216, 230, 0.1)",
                ),
                row=1,
                col=1,
            )  # 添加通道填充色

            # 新增：绘制波动率深度 (BB Width)
            ChartFactory.add_bbands_volatility(fig, df, row=2)

        fig.update_layout(
            title=f"{symbol} - {view_type} 分析",
            xaxis_rangeslider_visible=False,
            height=height,
            template="plotly_dark",
        )
        return fig

    @staticmethod
    def build_advanced_view(
        df: pd.DataFrame,
        symbol: str,
        view_type: str = "MACD",
        include_osc=True,
        height: int = 600,
        use_ha: bool = False,
    ):
        rows = 3 if include_osc else 1
        heights = [0.6, 0.2, 0.2] if include_osc else [1.0]

        fig = ChartFactory._create_base(rows=rows, heights=heights)
        ChartFactory.add_candlestick(fig, df, use_ha=use_ha)

        # 保留两条不同周期均线，并加入成交成本参考。
        # SMA: 白色實線
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["sma_main"],
                name="SMA",
                line=dict(color="white", width=1.5),
            ),
            row=1,
            col=1,
        )
        # EMA: 金色虛線
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["ema_main"],
                name="EMA",
                line=dict(color="gold", width=1.5, dash="dot"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["vwap_main"],
                name="VWAP",
                line=dict(color="#E066FF", width=1, dash="dashdot"),
            ),
            row=1,
            col=1,
        )

        # 加入交叉信號標註
        ChartFactory.add_ma_signals(fig, df)

        if view_type == "MACD":
            # 动态寻找 MACD 相关列
            hist = [c for c in df.columns if "MACDh" in c][0]
            line = [c for c in df.columns if "MACD_" in c][0]
            signal = [c for c in df.columns if "MACDs_" in c][0]

            ChartFactory.add_signal_markers(fig, df)

            fig.add_trace(
                go.Bar(x=df.index, y=df[hist], name="柱状图"), row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=df.index, y=df[line], name="MACD线"), row=2, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[signal],
                    name="Signal线",
                    line=dict(dash="dash"),
                ),
                row=2,
                col=1,
            )
            if include_osc:
                ChartFactory.add_adx(fig, df, row=3)

        fig.update_layout(
            title=f"{symbol} - {view_type} 分析",
            xaxis_rangeslider_visible=False,
            height=height,
            template="plotly_dark",
        )

        return fig
