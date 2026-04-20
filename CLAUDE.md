# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies and create virtual environment
uv sync

# Run the Streamlit dashboard
uv run streamlit run app.py

# Run the cron/automation tool
uv run python db_manage.py add -s aapl
```

## Project Overview

一个基于 Python 构建的现代化量化投研系统 (Modern Quant Research & Trading Dashboard)。集成了 ArcticDB 高性能时序数据库、关系型数据库，并通过 Streamlit 与 Plotly 构建交互式实时监控面板。系统内置 APScheduler 后台同步与策略扫描引擎，支持 Telegram 风险与机会预警。

核心特性:
- ⚡️ 极速环境管理：使用 `uv` 进行依赖管理
- 🗄️ 高性能时序存储：ArcticDB 专为 Pandas 优化的 C++ 底层存储
- 🤖 无人值守同步：支持多时间尺度 (1m/1h/Daily) 增量数据抓取与自动重采样
- 📈 深度技术分析：基于 `pandas_ta` 计算 RSI、RVOL 及爆量突破信号
- 📱 实时风险预警：Telegram Bot 推送超买超卖、爆量突破及最大回撤预警
- 🐳 Docker 支持：一键容器化部署

## Architecture

```
quant-app/
├── app.py                  # Main Streamlit entry point (navigation)
├── sync_engine.py          # Data synchronization engine (yfinance -> ArcticDB)
├── config.py               # Financial formatting configuration
├── db_manage.py            # CLI tool for metadata database management
├── database/
│   ├── models.py           # SQLModel definitions (SymbolMeta, MarketNews, SyncTaskLog)
│   ├── manager.py          # DatabaseManager for SQL operations
│   ├── resource.py         # Resource management for database connections
│   ├── manage/             # Specialized database managers (News, Symbol)
│   └── connections/        # Custom Streamlit connection types (ArcticDB)
├── engine/
│   ├── analytics.py        # AnalyticsEngine: technical indicators pipeline (pandas_ta)
│   ├── strategies.py       # Signal identification (FVG, MACD, breakouts)
│   └── chart_factory.py    # Plotly chart builder
├── ui/
│   ├── common_layout.py    # Shared UI layout and styling
│   ├── equity.py           # Equity analysis page
│   ├── indices.py          # Indices analysis page
│   ├── etf.py              # ETF analysis page
│   ├── future.py           # Futures analysis page
│   ├── admin/              # Admin tools (Asset Manager)
│   └── components/         # Reusable UI components (Sidebar, Tabs, Fragments)
├── api/
│   ├── fetch_news.py       # Finnhub news integration
│   └── market_manager.py   # Market data retrieval logic
├── utils/
│   └── human_readable.py   # Formatting utilities for financial data
├── tools/
│   └── cron.py             # Automation tools (Cron/Scheduler)
├── notifier/
│   └── tg.py               # Telegram bot integration
└── migrations/             # Database migrations
```

## Key Components

- **DataSyncEngine** (`sync_engine.py`): Fetches OHLCV data from yfinance and stores in ArcticDB with libraries for different timeframes (1m, 1h, daily)
- **AnalyticsEngine** (`engine/analytics.py`): Pipeline for computing technical indicators (RSI, MACD, Bollinger Bands, RVOL) using pandas_ta
- **ChartFactory** (`engine/chart_factory.py`): Builds Plotly figures with candlestick charts, signal markers, and indicator subplots
- **TelegramNotifier** (`notifier/tg.py`): Sends alerts for RSI oversold/overbought conditions, breakout signals, and drawdown warnings
- **DatabaseManager** (`database/manager.py`): SQLModel-based database operations for metadata
- **MarketManager** (`api/market_manager.py`): Market data retrieval and processing

## Configuration

- `pyproject.toml`: Dependencies managed by uv
- `.streamlit/secrets.toml`: Telegram token, Finnhub API key, ArcticDB/SQLite connection strings
- `.env`: `DB_PATH` and `LIBRARY_NAME` for ArcticDB

## Docker

```bash
docker-compose up -d --build
```

The Dockerfile uses `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` as base image.

## Development Guidelines

### Adding New Indicators

Add new technical indicators in `analytics.py`:

```python
from pandas_ta import RSI, MACD, BBANDS

def calculate_indicators(df):
    df['RSI'] = RSI(df['close'], length=14)
    df['MACD'] = MACD(df['close'])
    df['BBANDS'] = BBANDS(df['close'])
    return df
```

### Customizing Telegram Notifications

Modify notification templates in `tg.py`:

```python
def send_alert(symbol, signal, message):
    bot.send_message(chat_id=chat_id, text=f"{symbol}: {signal} - {message}")
```

## Main Dependencies

- `arcticdb` - High-performance time-series database
- `ccxt` - Cryptocurrency exchange API
- `streamlit` - Web application framework
- `pandas_ta` - Technical analysis indicators
- `textblob` - NLP sentiment analysis
- `plotly` - Interactive charting
- `apscheduler` - Task scheduling
- `python-telegram-bot` - Telegram notifications
