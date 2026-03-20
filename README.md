# 📈 Modern Quant Research & Trading Dashboard

这是一个基于 Python 的现代量化投研系统方案。它集成了高性能时序数据库 ArcticDB、关系型数据库，并利用 Streamlit 与 Plotly 构建了交互式实时监控面板。系统内置了基于 APScheduler 的后台同步与策略扫描引擎，支持通过 Telegram 进行风险与机会预警。

## 🚀 技术栈特性

- ⚡️ 极速环境管理: 使用 uv 替代 pip，实现秒级的依赖安装与环境锁定。
- 🗄️ 高性能时序存储: 采用 ArcticDB，专为 Pandas 优化的 C++ 底层存储，处理百万级数据无压力。
- 🤖 无人值守同步: 集成 APScheduler，支持多时间尺度（1m/1h/Daily）的增量数据抓取与自动重采样。
- 📈 深度技术分析: 基于 pandas_ta 计算 RSI、RVOL（相对成交量）及爆量突破信号。
- 📱 实时风险预警: 通过 Telegram Bot 推送超买超卖、爆量突破及最大回撤（Drawdown）预警。

---

## 🏗 核心架构图

### 🛠 快速开始

1. 克隆项目

```.bash
git clone https://github.com/edison7500/OpenQuantApp.git
cd OpenQuantApp
```

2.  环境初始化 (使用 uv)
确保你已安装 uv。如果未安装，请执行 ```curl -LsSf https://astral.sh/uv/install.sh | sh```.

```.bash
# 同步依赖并创建虚拟环境
uv sync
```

3. 配置 Secrets
在 .streamlit/secrets.toml 中填入你的凭证：
```
[telegram]
token = "YOUR_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"

[database]
arctic_uri = "lmdb://./market_data" # ArcticDB 依赖 Mongo
```

4. 使用 Docker Compose 一键启动
```
docker-compose up -d --build
```

---

## 功能模块展示

1. 多指标联动看板
    - K线主图: 支持爆量突破（Breakout）信号的自动标注 💰。
    - RSI 视图: 带有 70/30 超买超卖基准线与背景填充。
    - RVOL 视图: 实时监控相对成交量，识别机构异常放量行为。

2. 风险监控
    - Waterfall Drawdown: 实时计算策略回撤瀑布图。
    - 风险熔断: 当回撤超过预设阈值（如 -5%）时，Telegram 立即报警。

---

## ⚠️ 免责声明

本系统仅用于技术研究与量化分析工具展示，不构成任何投资建议。入市有风险，投资需谨慎。
