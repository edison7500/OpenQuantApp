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

This is a quantitative research and trading dashboard built with Python. It integrates ArcticDB for time-series storage, Streamlit for the UI, and Telegram for real-time alerts.

## Architecture

```
quant-app/
├── app.py              # Main Streamlit entry point (navigation)
├── sync_engine.py      # Data synchronization engine (yfinance -> ArcticDB)
├── config.py           # Financial formatting configuration
├── database/
│   ├── models.py       # SQLModel definitions (SymbolMeta, MarketNews, SyncTaskLog)
│   ├── manager.py      # DatabaseManager for SQL operations
│   └── connections/    # Custom Streamlit connection types (ArcticDB)
├── engine/
│   ├── analytics.py    # AnalyticsEngine: technical indicators pipeline (pandas_ta)
│   ├── strategies.py   # Signal identification (FVG, MACD, breakouts)
│   └── chart_factory.py # Plotly chart builder (candlestick, indicators, signals)
├── ui/                 # Streamlit pages (equity, indices, etf)
├── tools/              # Cron/scheduler tool (APScheduler + Telegram alerts)
├── notifier/           # Telegram bot integration
└── api/                # Market data fetching (Finnhub, news)
```

## Key Components

- **DataSyncEngine** (`sync_engine.py`): Fetches OHLCV data from yfinance and stores in ArcticDB with libraries for different timeframes (1m, 1h, daily)
- **AnalyticsEngine** (`engine/analytics.py`): Pipeline for computing technical indicators (RSI, MACD, Bollinger Bands, RVOL) using pandas_ta
- **ChartFactory** (`engine/chart_factory.py`): Builds Plotly figures with candlestick charts, signal markers, and indicator subplots
- **TelegramNotifier** (`notifier/tg.py`): Sends alerts for RSI oversold/overbought conditions and breakout signals

## Configuration

- `pyproject.toml`: Dependencies managed by uv
- `.streamlit/secrets.toml`: Telegram token, Finnhub API key, ArcticDB/SQLite connection strings
- `.env`: `DB_PATH` and `LIBRARY_NAME` for ArcticDB

## Docker

```bash
docker-compose up -d --build
```

The Dockerfile uses `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` as base image.
