# OpenQuantApp Agent Guide

This file provides repository context and development guidance for coding agents
working on OpenQuantApp (`quant-app`).

## Project Overview

OpenQuantApp is a Python 3.12+ quantitative research and trading dashboard. It
combines ArcticDB time-series storage, SQLModel relational metadata, Streamlit
and Plotly visualizations, scheduled data synchronization, multi-asset market
data, evidence-driven LLM research, and Telegram alerts.

Core capabilities:

- Dependency and environment management with `uv`
- OHLCV storage in ArcticDB and metadata storage in SQLModel/SQLite
- Equity and cryptocurrency ingestion through yfinance and CCXT
- Multi-timeframe incremental synchronization and resampling
- Technical analysis with `pandas_ta`
- News and metadata retrieval through Finnhub
- Configurable Gemini, OpenAI, OpenAI-compatible, and Ollama LLM providers
- APScheduler automation and Telegram risk/opportunity notifications
- Docker and Docker Compose deployment

## Quick Start

```bash
# Install dependencies and create the virtual environment
uv sync

# Run the Streamlit dashboard
uv run streamlit run app.py

# Initialize the metadata database
uv run python db_manage.py init

# Add or list monitored symbols
uv run python db_manage.py add -s AAPL
uv run python db_manage.py list

# Run tests, lint, and formatting checks
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Architecture

```text
quant-app/
├── app.py                  # Streamlit entry point and navigation
├── sync_engine.py          # yfinance/CCXT -> ArcticDB synchronization
├── config.py               # Financial and currency formatting
├── db_manage.py            # Metadata database CLI
├── api/
│   ├── fetch_news.py       # Finnhub news integration
│   └── market_manager.py   # Multi-asset market data retrieval
├── database/
│   ├── models.py           # SymbolMeta, MarketNews, SyncTaskLog
│   ├── manager.py          # Database operations
│   ├── resource.py         # Database resource management
│   ├── manage/             # Symbol and news managers
│   └── connections/        # Custom Streamlit/ArcticDB connections
├── engine/
│   ├── analytics.py        # pandas_ta indicator pipeline
│   ├── strategies.py       # FVG, MACD, and breakout signals
│   ├── chart_factory.py    # Plotly charts and signal markers
│   ├── macro_manager.py    # FRED macroeconomic data
│   ├── llm_provider.py     # Provider-neutral LLM configuration/factory
│   └── llm_manager.py      # Evidence-driven asset research
├── ui/
│   ├── equity.py           # Equity analysis page
│   ├── crypto.py           # Cryptocurrency analysis page
│   ├── indices.py          # Index analysis page
│   ├── etf.py              # ETF analysis page
│   ├── future.py           # Futures analysis page
│   ├── admin/              # Administration tools
│   └── components/         # Shared sidebar, tabs, and fragments
├── notifier/
│   └── tg.py               # Telegram notification integration
├── tools/
│   ├── cron.py             # Scheduled synchronization and alerts
│   └── telegram_bot.py     # Telegram management UI
├── migrations/             # Alembic database migrations
└── tests/                  # Pytest test suite
```

## Key Components

- `DataSyncEngine`: Retrieves OHLCV data and stores it in timeframe-specific
  ArcticDB libraries.
- `MarketDataManager`: Normalizes equity and cryptocurrency data retrieval and
  processing.
- `AnalyticsEngine`: Computes RSI, MACD, Bollinger Bands, RVOL, and related
  technical indicators.
- `ChartFactory`: Builds candlestick charts, indicators, and signal overlays.
- `MacroManager`: Fetches FRED macroeconomic indicators using a thread pool.
- `LLMManager`: Uses the provider-neutral LlamaIndex interface and VectorBT,
  financial, macro, and news inputs to produce balanced research. Prompts must
  distinguish facts from inference, show positive and negative evidence, avoid
  invented precision, and state confidence and data limitations.
- `DatabaseManager`: Handles SQLModel metadata, news, and task-log operations.
- `TelegramNotifier`: Sends RSI, breakout, and drawdown alerts.

## Configuration

- `pyproject.toml`: Project dependencies and Ruff configuration
- `uv.lock`: Reproducible dependency lock
- `.streamlit/secrets.toml`: LLM, Telegram, Finnhub, FRED, ArcticDB, and SQL
  connection credentials
- `.streamlit/config.toml`: Streamlit UI configuration
- `.env`: Optional local paths such as `DB_PATH` and `LIBRARY_NAME`
- `data/stock_db`: Default local ArcticDB LMDB location

Never commit real credentials or print secret values during diagnostics. Keep
the legacy `[gemini]` configuration compatible when changing the unified
`[llm]` provider configuration.

## Development Standards

- Manage dependencies through `uv` and keep `pyproject.toml` and `uv.lock` in
  sync.
- Use type annotations for new project logic.
- Run focused tests for changed behavior, then the full Pytest suite.
- Run Ruff lint and format checks before handoff.
- Use Alembic migrations for relational schema changes.
- Preserve existing data compatibility when changing database or ArcticDB
  structures.
- Keep UI components reusable and isolate provider/data-source specifics behind
  managers or factories.
- LLM output should remain evidence-driven and non-sensational; do not restore
  provider-specific or overly risk-biased personas.

## Common Extension Points

### Technical Indicators

Add indicator calculations to `engine/analytics.py`, then expose them through
the relevant UI fragment and add focused tests.

```python
from pandas_ta import bbands, macd, rsi


def calculate_indicators(df):
    df["RSI"] = rsi(df["close"], length=14)
    df["MACD"] = macd(df["close"])
    df["BBANDS"] = bbands(df["close"])
    return df
```

### Telegram Notifications

Notification templates live in `notifier/tg.py`; scheduling and management are
handled by `tools/cron.py` and `tools/telegram_bot.py`.

### LLM Providers

Add provider configuration and validation in `engine/llm_provider.py`. Keep
`engine/llm_manager.py` dependent only on the common LlamaIndex completion
interface and cover configuration/factory changes with tests.

## Main Dependencies

- `arcticdb`: Time-series database
- `sqlmodel` / `sqlalchemy` / `alembic`: Relational data and migrations
- `yfinance` / `ccxt` / `finnhub-python`: Market and news data
- `streamlit` / `plotly`: Interactive web UI
- `pandas` / `pandas_ta` / `vectorbt`: Quantitative analysis
- `llama-index`: Provider-neutral LLM interface
- `apscheduler`: Background scheduling
- Telegram integration: Notifications and management UI

## Docker

```bash
docker-compose up -d --build
```

The Dockerfile uses `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` as its base
image. When Ollama runs on the host and the application runs in Docker, use
`http://host.docker.internal:11434` as the Ollama API base URL.

## Future Enhancements

- Add semantic news search with a SQLite vector extension.
- Expand the technical indicator library.
- Add more granular evidence-based drawdown interpretation and scenario
  analysis.
