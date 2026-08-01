# OpenQuantApp

> 面向个人投资研究的多资产量化分析工作台。

OpenQuantApp 是一个基于 Python 的开源量化投研项目。它将股票与加密货币
行情、技术指标、回撤分析、基本面、宏观数据、新闻情绪和 LLM 研究报告整合
到一个 Streamlit Dashboard 中，并使用 ArcticDB 保存时序数据、SQLModel
管理元数据。

当前版本适合个人研究、数据探索和原型验证，不包含券商接入、自动下单或
实盘交易执行能力。

## 项目状态

当前 Streamlit 版本已覆盖日常个人投研需要，将作为首个开源版本继续维护，
重点放在稳定性、数据兼容性和问题修复。

后续计划将现有分析能力与 UI 解耦，并评估两条演进路径：

- 在主项目中逐步引入 FastAPI 服务层；
- 保留 Streamlit 版本，另建分支或 fork 开发 FastAPI 版本。

无论采用哪条路线，`engine/`、`database/`、行情同步和 LLM Provider 都应尽量
保持可复用，避免重写已经验证过的投研逻辑。

## 功能概览

- **多资产行情**：通过 yfinance 获取股票、ETF、指数和期货行情，通过 CCXT
  获取 Binance、OKX 等交易所的加密货币现货行情。
- **多周期数据**：支持 `1m`、`1h`、日线、周线和月线数据的增量同步与重采样。
- **技术分析**：提供 RSI、MACD、Bollinger Bands、RVOL、FVG 和突破信号。
- **风险观察**：展示最大回撤、当前回撤、回撤区间及 VectorBT 风险调整指标。
- **研究数据**：整合基本面、FRED 宏观指标和 Finnhub 新闻情绪。
- **LLM 研究报告**：统一支持 Gemini、OpenAI、OpenAI-compatible API 和 Ollama，
  输出平衡、证据驱动并明确数据局限的分析报告。
- **自动化任务**：使用 APScheduler 执行行情同步与策略扫描。
- **消息提醒**：通过 Telegram 推送 RSI、突破和回撤提醒。
- **本地部署**：支持 `uv` 环境管理与 Docker Compose 部署。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| Web UI | Streamlit、Plotly |
| 数据分析 | Pandas、pandas-ta、VectorBT |
| 市场数据 | yfinance、CCXT、Finnhub、FRED |
| 时序存储 | ArcticDB |
| 关系数据 | SQLModel、SQLAlchemy、SQLite、Alembic |
| LLM | LlamaIndex、Gemini、OpenAI、OpenAI-compatible、Ollama |
| 自动化 | APScheduler、Telegram Bot |
| 工程工具 | Python 3.12+、uv、Pytest、Ruff、Docker |

## 快速开始

### 环境要求

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- 可选：Docker 与 Docker Compose
- 可选：本地 [Ollama](https://ollama.com/)

### 1. 获取代码并安装依赖

```bash
git clone https://github.com/edison7500/OpenQuantApp.git
cd OpenQuantApp
uv sync
```

### 2. 配置 Streamlit Secrets

创建 `.streamlit/secrets.toml`。以下是完整示例，请只填写自己需要启用的服务：

```toml
[connections.arcticdb]
url = "lmdb://./arctic_db"
library = "financial_data"

[connections.quant_db]
url = "sqlite:///quant.db"

[finnhub]
api_key = "YOUR_FINNHUB_API_KEY"

[fred]
api_key = "YOUR_FRED_API_KEY"

[telegram]
token = "YOUR_TELEGRAM_BOT_TOKEN"
chat_id = "YOUR_TELEGRAM_CHAT_ID"

[llm]
provider = "gemini"
model = "gemini-3-flash-preview"
api_key = "YOUR_LLM_API_KEY"
temperature = 0.2
timeout = 180
```

不要提交 `.streamlit/secrets.toml`、`.env` 或任何真实 Token。密钥一旦出现在
截图、日志、Issue 或提交历史中，应立即撤销并重新生成。

### 3. 初始化元数据

```bash
uv run python db_manage.py init
uv run python db_manage.py add -s AAPL
uv run python db_manage.py list
```

更多标的可在应用的“资产管理”页面中维护。

### 4. 启动应用

```bash
uv run streamlit run app.py
```

默认访问地址为 <http://localhost:8501>。

### Docker Compose

```bash
docker-compose up -d --build
```

容器会将应用暴露在 `8501` 端口。部署前请检查 `docker-compose.yml` 中的
数据卷、环境变量和 `.streamlit` 挂载是否符合本机目录结构。

## LLM 配置

所有 Provider 使用统一的 `[llm]` 配置。通用字段包括：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `provider` | 是 | `gemini`、`openai`、`openai_compatible` 或 `ollama` |
| `model` | 是 | Provider 对应的模型名称 |
| `api_key` | 视 Provider 而定 | 本地 Ollama 不需要 |
| `api_base` | 可选 | 自定义或远程 API 地址 |
| `temperature` | 可选 | 默认 `0.2` |
| `timeout` | 可选 | 请求超时秒数，默认 `60` |
| `max_tokens` | 可选 | 最大输出 Token 数 |
| `context_window` | 可选 | 上下文窗口大小 |

### OpenAI

```toml
[llm]
provider = "openai"
model = "YOUR_OPENAI_MODEL"
api_key = "YOUR_OPENAI_API_KEY"
temperature = 0.2
timeout = 180
```

### OpenAI-compatible API

适用于 DeepSeek、通义以及其他实现 OpenAI Chat Completions 接口的服务：

```toml
[llm]
provider = "openai_compatible"
model = "YOUR_MODEL_NAME"
api_key = "YOUR_API_KEY"
api_base = "https://YOUR_ENDPOINT/v1"
context_window = 128000
temperature = 0.2
timeout = 180
```

### 本地 Ollama

```toml
[llm]
provider = "ollama"
model = "qwen3:8b"
api_base = "http://localhost:11434"
timeout = 180
context_window = 32768
temperature = 0.2
```

本地 Ollama 不需要 `api_key`。如果应用运行在 Docker 中而 Ollama 运行在
宿主机，可将 `api_base` 改为 `http://host.docker.internal:11434`。

### Ollama Cloud

```toml
[llm]
provider = "ollama"
model = "gemma4:31b"
api_key = "YOUR_OLLAMA_API_KEY"
api_base = "https://ollama.com"
timeout = 180
context_window = 32768
temperature = 0.2
```

直连 `ollama.com` 时，应用也兼容 `gemma4:31b-cloud` 形式的别名，并会自动
转换为云 API 使用的模型名。通过本机 Ollama 代理云模型时仍保留 `-cloud`
后缀。

原有 `[gemini]` 配置目前仍可使用，但新部署建议统一迁移到 `[llm]`。

## 主要页面

- **股票分析**：技术指标、策略信号、回撤、财务数据、新闻和 AI 报告。
- **Crypto 分析**：CCXT 现货行情、小时线和日线分析。
- **指数 / ETF / 期货分析**：共享统一指标和图表管线。
- **行情同步**：手动执行与观察数据同步任务。
- **通知管理**：配置和测试 Telegram 提醒。
- **资产管理**：维护标的、资产类型、交易所和市场类型。

## 项目结构

```text
OpenQuantApp/
├── app.py                  # Streamlit 入口与页面导航
├── sync_engine.py          # yfinance / CCXT -> ArcticDB
├── db_manage.py            # 元数据管理 CLI
├── api/                    # 市场数据与新闻接入
├── database/               # SQLModel 与 ArcticDB 连接层
├── engine/
│   ├── analytics.py        # 技术指标管线
│   ├── strategies.py       # 策略与信号
│   ├── chart_factory.py    # Plotly 图表
│   ├── macro_manager.py    # FRED 宏观数据
│   ├── llm_provider.py     # LLM 配置与 Provider 工厂
│   └── llm_manager.py      # 证据驱动的研究报告
├── ui/                     # Streamlit 页面与组件
├── tools/                  # 定时任务与通知管理
├── notifier/               # Telegram 通知
├── migrations/             # Alembic 迁移
└── tests/                  # Pytest 测试
```

## 开发与测试

```bash
# 运行全部测试
uv run pytest

# 代码检查
uv run ruff check .

# 检查格式
uv run ruff format --check .

# 自动格式化
uv run ruff format .
```

提交新功能时，请优先：

1. 将数据源或 Provider 差异隔离在 manager/factory 中；
2. 避免把新的业务逻辑直接绑定到 Streamlit Session State；
3. 为配置解析、数据转换和分析逻辑补充测试；
4. 保持已有数据库与 ArcticDB 数据兼容。

## Roadmap

### Streamlit 版本

- 稳定现有股票、Crypto、宏观、通知和 LLM 分析能力；
- 完善错误提示、缓存与数据质量检查；
- 补充公开部署文档和示例配置；
- 扩展自动化测试覆盖率。

### FastAPI 版本

- 将行情、指标、研究和 LLM 逻辑提取为独立 service；
- 通过 FastAPI 提供类型化 HTTP API；
- 将 LLM 分析改为可查询状态的后台任务，并支持 SSE/流式输出；
- 将 Streamlit 逐步降级为兼容客户端，或在独立 fork 中构建新前端；
- 在真实需要出现前保持模块化单体，不提前引入复杂微服务基础设施。

Roadmap 表示方向而非交付承诺，欢迎通过 Issue 讨论设计与优先级。

## 参与贡献

欢迎提交 Bug、数据兼容问题、文档改进和小而清晰的功能增强。

1. Fork 本仓库并创建功能分支；
2. 保持修改范围聚焦；
3. 添加或更新相关测试；
4. 确保 Pytest 与 Ruff 检查通过；
5. 提交 Pull Request，并说明动机、行为变化和验证方式。

涉及大规模架构调整，尤其是 FastAPI、任务队列、前端替换或存储结构变更时，
建议先创建 Issue 讨论方案。

## 数据与安全说明

- 第三方数据可能存在延迟、缺失、限流或字段变化，请勿将其视为交易所或监管
  机构发布的权威记录。
- 回测和技术指标受到样本区间、参数和幸存者偏差影响，不代表未来表现。
- LLM 输出可能不准确，只应作为研究线索，关键结论必须回到原始数据核验。
- 本项目不会要求你公开 API Key；请始终使用本地 secrets 或部署平台的密钥管理。

## 免责声明

本项目仅用于软件开发、数据研究和量化分析展示，不构成投资建议、收益承诺或
任何证券、衍生品及数字资产的买卖邀请。使用者应自行判断数据质量并承担决策
风险。

## License

本项目计划以 MIT License 开源。正式发布前请确认仓库根目录中的 `LICENSE`
文件及版权信息。
