# OpenQuantApp Project Context

## Project Overview
OpenQuantApp (also referred to as `quant-app`) is a modern quantitative research and trading dashboard built with Python. It integrates high-performance time-series storage (ArcticDB), relational metadata storage (SQLModel/SQLite), and an interactive UI (Streamlit & Plotly). The system supports data synchronization from market providers (yfinance, Finnhub), technical analysis indicator computation, and real-time alerts via Telegram.

## Key Technologies
- **Language:** Python 3.12+
- **Dependency Management:** `uv`
- **Time-Series Database:** [ArcticDB](https://arcticdb.io/) (for high-performance OHLCV data)
- **Relational Database:** SQLModel (with SQLite) for metadata, news, and logs
- **Web UI:** Streamlit (with Plotly for interactive charting)
- **Technical Analysis:** `pandas_ta`
- **Data Sources:** `yfinance` (market data), `finnhub-python` (news/meta)
- **Automation/Scheduling:** `APScheduler`
- **Notifications:** Telegram Bot API (`python-telegram-bot`)
- **Containerization:** Docker & Docker-Compose

## Core Architecture
- `app.py`: Main Streamlit entry point for navigation across pages.
- `sync_engine.py`: Core logic for fetching OHLCV data and syncing to ArcticDB.
- `database/`:
  - `models.py`: SQLModel definitions for `SymbolMeta`, `MarketNews`, and `SyncTaskLog`.
  - `manager.py`: Database operations for SQL metadata.
  - `connections/`: Custom Streamlit connection types for ArcticDB.
- `engine/`:
  - `analytics.py`: Technical indicator calculation pipeline using `pandas_ta`.
  - `strategies.py`: Signal identification (e.g., FVG, MACD, breakout patterns).
  - `chart_factory.py`: Plotly figure construction for charts and signals.
- `ui/`: Streamlit page implementations (Equity, Indices, ETF, Admin).
- `tools/`:
  - `cron.py`: Background tasks for data sync and alerting.
- `db_manage.py`: CLI tool for managing the metadata database (init, add symbols, etc.).
- `config.py`: Financial formatting and currency-specific configurations.

## Development Workflow

### Environment Setup
1. **Install uv:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Sync dependencies:**
   ```bash
   uv sync
   ```

### Running the Application
- **Streamlit Dashboard:**
  ```bash
  uv run streamlit run app.py
  ```
- **CLI Database Management:**
  ```bash
  # Initialize database tables
  uv run python db_manage.py init
  # Add a symbol to monitor
  uv run python db_manage.py add -s AAPL
  # List monitored symbols
  uv run python db_manage.py list
  ```
- **Docker Deployment:**
  ```bash
  docker-compose up -d --build
  ```

### Development Standards
- **Linting & Formatting:** Handled by `ruff`. Configurations are in `pyproject.toml`. Use `ruff check` and `ruff format`.
- **Database Migrations:** Managed by Alembic (see `migrations/` directory).
- **Type Safety:** Use Type Annotations (standard in SQLModel and project logic).
- **Environment Variables:** Credentials and paths are managed via `.streamlit/secrets.toml` or `.env`.

## Key Files & Locations
- `pyproject.toml`: Dependency definitions and tool configurations (ruff).
- `README.md`: High-level user-facing documentation.
- `CLAUDE.md`: Claude Code specific guidelines (Quick start, architecture).
- `.streamlit/config.toml`: UI-specific configuration.
- `data/stock_db`: Default location for ArcticDB (LMDB storage).
- `sync_engine.py`: Data ingestion logic.
- `engine/analytics.py`: Where to add new technical indicators.
- `notifier/tg.py`: Telegram notification implementation.

## Project TODOs / Future Enhancements
- Integration of `sqlite-vss` for semantic news search (vector embeddings).
- Expanded technical indicator library in `analytics.py`.
- More granular risk management features (drawdown alerts).
