# 📈 Modern Quant Research & Trading Dashboard

一个基于 Python 构建的现代化量化投研系统，集成了高性能时序数据库 ArcticDB、关系型数据库，并通过 Streamlit 与 Plotly 构建交互式实时监控面板。系统内置基于 APScheduler 的后台同步与策略扫描引擎，支持通过 Telegram 进行风险与机会预警。

## 🚀 核心特性

- ⚡️ **极速环境管理**: 使用 `uv` 替代 pip，实现秒级的依赖安装与环境锁定
- 🗄️ **高性能时序存储**: 采用 ArcticDB，专为 Pandas 优化的 C++ 底层存储，轻松处理百万级数据
- 🤖 **无人值守同步**: 集成 APScheduler，支持多时间尺度（1m/1h/Daily）的增量数据抓取与自动重采样
- 🪙 **Crypto 公共行情**: 通过 CCXT 接入 Binance/OKX 现货 1h 与 Daily OHLCV，无需 API Key
- 🧠 **AI 深度分析**: 支持 Gemini、OpenAI、OpenAI 兼容 LLM 及 Ollama，基于量化、基本面与宏观数据生成平衡的投资研究报告
- 📈 **深度技术分析**: 基于 `pandas_ta` 计算 RSI、RVOL（相对成交量）及爆量突破信号
- 📱 **实时风险预警**: 通过 Telegram Bot 推送超买超卖、爆量突破及最大回撤（Drawdown）预警
- 🐳 **Docker 支持**: 一键容器化部署，开箱即用

## 🏗 技术架构

```.shell
quant-app/
├── app.py              # Main Streamlit entry point (navigation)
├── sync_engine.py      # Data synchronization engine (yfinance/CCXT -> ArcticDB)
├── config.py           # Financial formatting configuration
├── db_manage.py        # CLI tool for metadata database management
├── database/           # Database layer
│   ├── models.py       # SQLModel definitions (SymbolMeta, MarketNews, SyncTaskLog)
│   ├── manager.py      # DatabaseManager for SQL operations
│   ├── resource.py     # Resource management for database connections
│   ├── manage/         # Specialized database managers (News, Symbol)
│   └── connections/    # Custom Streamlit connection types (ArcticDB)
├── engine/             # Analysis engine
│   ├── analytics.py    # AnalyticsEngine: technical indicators pipeline (pandas_ta)
│   ├── strategies.py   # Signal identification (FVG, MACD, breakouts)
│   └── chart_factory.py # Plotly chart builder
├── ui/                 # Streamlit UI layer
│   ├── equity.py       # Equity analysis page
│   ├── crypto.py       # CCXT spot crypto analysis page
│   ├── indices.py      # Indices analysis page
│   ├── etf.py          # ETF analysis page
│   ├── future.py       # Futures analysis page
│   ├── admin/          # Admin tools (Asset Manager)
│   └── components/     # Reusable UI components (Sidebar, Tabs, Fragments)
├── api/                # Market data APIs (Finnhub, News)
│   ├── fetch_news.py   # Finnhub news integration
│   └── market_manager.py # Market data retrieval logic
├── utils/              # Utility functions
│   └── human_readable.py # Formatting utilities for financial data
├── tools/              # Automation tools (Cron/Scheduler)
└── notifier/           # Telegram bot integration
```

## 📦 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/edison7500/OpenQuantApp.git
cd OpenQuantApp
```

### 2. 环境初始化 (使用 uv)

确保你已安装 `uv`。如果未安装，请执行：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

同步依赖并创建虚拟环境：

```bash
uv sync
```

### 3. 配置 Secrets

在 secrets.toml 中填入你的凭证：

```toml
[telegram]
token = "YOUR_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"

[llm]
provider = "gemini"
model = "gemini-3-flash-preview"
api_key = "YOUR_LLM_API_KEY"
temperature = 0.2

[connections.arcticdb]
uri = "lmdb://./data/stock_db"
```

`[llm]` 使用统一字段，通过 `provider` 切换模型服务：

```toml
# OpenAI
[llm]
provider = "openai"
model = "YOUR_OPENAI_MODEL"
api_key = "YOUR_OPENAI_API_KEY"
temperature = 0.2

# DeepSeek、通义等 OpenAI 兼容服务
[llm]
provider = "openai_compatible"
model = "YOUR_MODEL_NAME"
api_key = "YOUR_API_KEY"
api_base = "https://YOUR_ENDPOINT/v1"
context_window = 128000
temperature = 0.2
```

Ollama 使用原生接口，本地运行时不需要 API Key：

```toml
[llm]
provider = "ollama"
model = "qwen3:8b"
api_base = "http://localhost:11434" # 可省略
timeout = 180
context_window = 32768
temperature = 0.2
```

如果应用运行在 Docker 容器中而 Ollama 运行在宿主机，请将 `api_base`
设置为 `http://host.docker.internal:11434`。连接需要认证的远程 Ollama
服务时，可额外配置 `api_key`，它会作为 Bearer Token 发送。

可选字段包括 `max_tokens`、`timeout` 和 `context_window`。原有
`[gemini]` 配置仍然兼容，但建议迁移到统一的 `[llm]` 格式。

### 4. 启动应用

#### 本地运行

```bash
# 运行 Streamlit 仪表盘
uv run streamlit run app.py

# 运行 cron/自动化工具
uv run python db_manage.py add -s aapl
```

#### Docker 部署

```bash
docker-compose up -d --build
```

Dockerfile 使用 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` 作为基础镜像。

## 📊 功能模块展示

### 1. 多指标联动看板

- **K 线主图**: 支持爆量突破（Breakout）信号的自动标注 💰
- **RSI 视图**: 带有 70/30 超买超卖基准线与背景填充
- **RVOL 视图**: 实时监控相对成交量，识别机构异常放量行为

### 2. 风险监控

- **Waterfall Drawdown**: 实时计算策略回撤瀑布图
- **风险熔断**: 当回撤超过预设阈值（如 -5%）时，Telegram 立即报警

### 3. AI 投资研究分析

- **多维数据驱动**: 融合技术指标、回测数据、基本面及新闻情感
- **证据平衡**: 对称展示正面与负面证据，区分事实、推断和假设
- **情景分析**: 描述基准、乐观和谨慎情景的触发条件，同时标明置信度与数据局限

### 4. 数据同步引擎

- 支持多时间尺度数据抓取（1m/1h/Daily）
- 增量更新机制，避免重复下载
- 自动重采样与数据清洗
- 自带可视化日志管理与一键清除功能

### 4. 策略分析引擎

- **FVG**: 公允价值缺口检测
- **MACD**: 趋势动量信号识别
- **Breakouts**: 突破信号标记
- **RSI**: 超买超卖区域判断

## 🔧 开发指南

### 添加新指标

在 analytics.py 中添加新的技术指标：

```python
from pandas_ta import RSI, MACD, BBANDS

def calculate_indicators(df):
    df['RSI'] = RSI(df['close'], length=14)
    df['MACD'] = MACD(df['close'])
    df['BBANDS'] = BBANDS(df['close'])
    return df
```

### 自定义 Telegram 通知

在 tg.py 中修改通知模板：

```python
def send_alert(symbol, signal, message):
    bot.send_message(chat_id=chat_id, text=f"{symbol}: {signal} - {message}")
```

## 📚 依赖管理

项目使用 `uv` 进行依赖管理，所有依赖在 pyproject.toml 中定义。

主要依赖：

- `arcticdb` - 高性能时序数据库
- `ccxt` - 加密货币交易接口库
- `streamlit` - Web 界面框架
- `pandas_ta` - 技术分析指标
- `textblob` - NLP 情感分析
- `plotly` - 交互式图表
- `apscheduler` - 定时任务调度
- `python-telegram-bot` - Telegram 通知

## ⚠️ 免责声明

本系统仅用于技术研究与量化分析工具展示，不构成任何投资建议。入市有风险，投资需谨慎。

## 📝 许可证

MIT License
