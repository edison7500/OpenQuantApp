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
    def add_candlestick(fig, df, row=1):
        """核心组件：绘制 K 线"""
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="K线",
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
    def build_view(df: pd.DataFrame, symbol: str, view_type: str = "MACD"):
        """
        工厂入口：根据类型组装图表
        """
        fig = ChartFactory._create_base()
        ChartFactory.add_candlestick(fig, df)
        ChartFactory.add_signal_markers(fig, df)

        if view_type == "MACD":
            # 动态寻找 MACD 相关列
            hist = [c for c in df.columns if "MACDh" in c][0]
            line = [c for c in df.columns if "MACD_" in c][0]

            fig.add_trace(
                go.Bar(x=df.index, y=df[hist], name="柱状图"), row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=df.index, y=df[line], name="MACD线"), row=2, col=1
            )

        elif view_type == "RSI":
            rsi_col = [c for c in df.columns if "RSI" in c][0]
            fig.add_trace(
                go.Scatter(x=df.index, y=df[rsi_col], name="RSI"), row=2, col=1
            )
            # 添加 70/30 警戒线
            fig.add_hline(
                y=70, line_dash="dash", line_color="red", row=2, col=1
            )
            fig.add_hline(
                y=30, line_dash="dash", line_color="green", row=2, col=1
            )

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
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[bb_m],
                    name="Middle Band",
                    line=dict(color="rgba(255, 165, 0, 0.8)", dash="dot"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[bb_l],
                    name="Lower Band",
                    line=dict(color="rgba(173, 216, 230, 0.8)", dash="dash"),
                    fill="tonexty",
                    fillcolor="rgba(173, 216, 230, 0.1)",
                )
            )  # 添加通道填充色

        fig.update_layout(
            title=f"{symbol} - {view_type} 分析",
            xaxis_rangeslider_visible=False,
            height=800,
            template="plotly_dark",
        )
        return fig
