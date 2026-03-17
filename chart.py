import plotly.graph_objs as go
from plotly.subplots import make_subplots


def create_base_figure():
    """创建一个通用的带副图的画布基础结构"""
    return make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
    )


def add_candlestick(fig, df):
    """通用的 K 线绘制函数"""
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K线",
        ),
        row=1,
        col=1,
    )
    return fig


def create_rvol_chart(df, symbol):
    # 創建兩個子圖：上方 K 線 (佔 70%)，下方 RVOL (佔 30%)
    fig = create_base_figure()

    # --- 1. 主图：K 线 ---
    add_candlestick(fig, df)

    # --- 2. 标注爆量突破信号 (💰 或 箭头) ---
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

    # --- 3. 副图：RVOL 柱状图 ---
    colors = ["#FFA500" if v > 2.0 else "#636EFA" for v in df["rvol"]]
    fig.add_trace(
        go.Bar(x=df.index, y=df["rvol"], marker_color=colors, name="RVOL"),
        row=2,
        col=1,
    )

    # 辅助线
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", row=2, col=1)
    fig.add_hline(y=2.0, line_dash="dot", line_color="red", row=2, col=1)

    fig.update_layout(
        title=f"{symbol} - ROVL 视图",
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        height=800,
    )
    return fig


# --- 视图 1：RSI 图表 ---
def create_rsi_view(df, symbol):
    fig = create_base_figure()
    add_candlestick(fig, df)

    rsi_col = [c for c in df.columns if "RSI" in c][0]
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[rsi_col], name="RSI", line=dict(color="royalblue")
        ),
        row=2,
        col=1,
    )

    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hrect(
        y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0, row=2, col=1
    )

    fig.update_layout(
        title=f"{symbol} - RSI 视图",
        xaxis_rangeslider_visible=False,
        height=600,
    )
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    return fig


# --- 视图 2：MACD 图表 ---
def create_macd_view(df, symbol):
    fig = create_base_figure()
    add_candlestick(fig, df)

    # 动态获取 MACD 列名
    macd_line = [c for c in df.columns if c.startswith("MACD_")][0]
    macd_signal = [c for c in df.columns if c.startswith("MACDs_")][0]
    macd_hist = [c for c in df.columns if c.startswith("MACDh_")][0]

    # 绘制 MACD 线和信号线
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[macd_line], name="MACD", line=dict(color="blue")
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[macd_signal],
            name="Signal",
            line=dict(color="orange"),
        ),
        row=2,
        col=1,
    )

    # 绘制 MACD 柱状图 (用颜色区分正负)
    colors = ["green" if val >= 0 else "red" for val in df[macd_hist]]
    fig.add_trace(
        go.Bar(
            x=df.index, y=df[macd_hist], name="Histogram", marker_color=colors
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=f"{symbol} - MACD 视图",
        xaxis_rangeslider_visible=False,
        height=600,
    )
    return fig


# --- 视图 3：布林带图表 (只有主图) ---
def create_bbands_view(df, symbol):
    # 布林带不需要副图，直接画在一张图上
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K线",
        )
    )

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
        title=f"{symbol} - 布林带视图",
        xaxis_rangeslider_visible=False,
        height=600,
    )
    return fig


def create_macd_view_with_signals(df, symbol):
    """生成带有买卖点信号的 MACD 视图"""
    # fig = make_subplots(
    #     rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3]
    # )
    fig = create_base_figure()
    add_candlestick(fig, df)

    # ==========================================
    # 2. 绘制买卖点信号 (精华部分)
    # ==========================================
    # 提取买点数据，y 轴位置设为最低价的 0.99 倍，稍微错开以免重叠
    buy_dates = df[df["Buy_Signal"]].index
    buy_prices = df.loc[df["Buy_Signal"], "Low"] * 0.99

    fig.add_trace(
        go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode="markers",
            marker=dict(
                symbol="triangle-up",
                size=12,
                color="green",
                line=dict(width=1, color="darkgreen"),
            ),
            name="买入 (金叉)",
        ),
        row=1,
        col=1,
    )

    # 提取卖点数据，y 轴位置设为最高价的 1.01 倍
    sell_dates = df[df["Sell_Signal"]].index
    sell_prices = df.loc[df["Sell_Signal"], "High"] * 1.01

    fig.add_trace(
        go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode="markers",
            marker=dict(
                symbol="triangle-down",
                size=12,
                color="red",
                line=dict(width=1, color="darkred"),
            ),
            name="卖出 (死叉)",
        ),
        row=1,
        col=1,
    )

    # ==========================================
    # 3. 绘制下方的 MACD 指标 (与之前逻辑相同)
    # ==========================================
    macd_line = [c for c in df.columns if c.startswith("MACD_")][0]
    macd_signal = [c for c in df.columns if c.startswith("MACDs_")][0]
    macd_hist = [c for c in df.columns if c.startswith("MACDh_")][0]

    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[macd_line], name="MACD", line=dict(color="blue")
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[macd_signal],
            name="Signal",
            line=dict(color="orange"),
        ),
        row=2,
        col=1,
    )

    colors = ["green" if val >= 0 else "red" for val in df[macd_hist]]
    fig.add_trace(
        go.Bar(
            x=df.index, y=df[macd_hist], name="Histogram", marker_color=colors
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=f"{symbol} - 策略信号视图",
        xaxis_rangeslider_visible=False,
        height=700,
    )
    return fig


def create_drawdown_chart(df, symbol):
    # 假设 df['close'] 是价格，我们简单以价格回撤为例
    # 如果是策略回撤，请替换为策略累计净值

    # 计算回撤
    cumulative = df["Close"] / df["Close"].iloc[0]  # 归一化净值
    running_max = cumulative.cummax()
    drawdown = (cumulative / running_max - 1) * 100  # 转为百分比

    fig = go.Figure()
    # fig = create_base_figure()
    # add_candlestick(fig, df)

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
    )

    fig.update_layout(
        title=f"{symbol} 历史回撤 (Waterfall Chart)",
        yaxis_title="回撤幅度 (%)",
        template="plotly_white",
        yaxis_range=[drawdown.min() * 1.1, 0],  # 纵坐标反向，从 0 向下
        xaxis_rangeslider_visible=False,
        height=400,
    )

    return fig
