# Polymarket BTC Scalping Bot

BTC 5-minute market scalping bot for Polymarket. Runs in PAPER mode by default (logs only, no real trades). Clean architecture with FastAPI backend and React dashboard.

A personal experiment, not financial advice. It always starts in PAPER mode, and LIVE mode needs your own Polymarket credentials.

## What it does

Polymarket lists markets that ask whether BTC will be above a given price when a 5-minute window closes. In the last seconds of each window the outcome is often already clear, but the winning side can still be bought below $1. The bot looks for those moments:

1. **Discovers** the active BTC 5-minute markets over WebSocket, with a REST fallback.
2. **Watches** the live BTC price from Binance, failing over to Coinbase if the feed goes quiet for 3 seconds, together with each market's order book.
3. **Evaluates a signal** inside the entry window (by default, 5 to 25 seconds before close). It enters only when all of these hold:
   - BTC is far enough from the market's threshold (`min_dtt`, default $10), so the outcome is unlikely to flip.
   - The potential gain on the winning side is worth it (`min_gain_usd`, default $0.75 on a $10 position).
   - The order book has enough depth to fill the position.
4. **Records everything**: every signal, including the reason for each skip, every trade, per-second snapshots inside the entry window, and how each market resolved. Old snapshots are summarized and pruned every night.
5. **Shows it live** in the dashboard: signals, trades, performance by day and month, feed health, and strategy parameters you can change without restarting the bot.

The domain layer has no external dependencies, and every use case is tested in isolation. The suite has about 440 Python tests (unit, plus integration against an in-memory SQLite) and 65 dashboard tests.

## Requirements

- Python 3.11+
- Node.js 18+

## Setup

```bash
# 1. Clone and enter the repo
cd polymarket-bot

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Copy environment file and fill in credentials (only needed for LIVE mode)
cp .env.example .env

# 5. Review strategy defaults in config.yml (optional)
cat config.yml
```

## Run the bot (PAPER mode)

The bot always starts in PAPER mode regardless of previous state (safety default).

```bash
source .venv/bin/activate
python3 -m src.application.bot_runner
```

## Run the API

```bash
source .venv/bin/activate
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs available at `http://127.0.0.1:8000/docs`.

## Run the dashboard

```bash
cd dashboard
npm install
npm run dev
```

Dashboard available at `http://localhost:5173`.

## Run tests

```bash
source .venv/bin/activate

# All tests
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing

# Domain unit tests only
pytest tests/unit/domain/ -v

# Integration tests only
pytest tests/integration/ -v
```

## Project structure

```
src/
  domain/         Pure business logic (no external dependencies)
    entities/     Market, Signal, Trade, Snapshot, ...
    value_objects/ Price, DTT, TimeWindow, StrategyParams
    repositories/ Abstract interfaces (ABC)
    use_cases/    EvaluateSignal, ExecuteTrade, ResolveMarket, ...
  infrastructure/ Concrete implementations
    persistence/  SQLAlchemy models + repository implementations
    feeds/        BinanceFeed, CoinbaseFeed, FailoverBTCFeed, PolymarketFeed
    config/       Settings loader
  application/    Orchestration
    bot_runner.py Entry point and dependency injection root
    event_bus.py  In-memory pub/sub
    services/     MarketMonitorService, MarketDiscoveryService, DailyCleanupScheduler
  api/            FastAPI
    routers/      signals, trades, snapshots, performance, strategy, settings, maintenance
    schemas/      Pydantic request/response schemas
dashboard/        React + Vite + TypeScript frontend
tests/
  unit/           Pure unit tests with mocks (no network, no SQLite)
  integration/    Integration tests with SQLite :memory: and TestClient
data/             SQLite database (gitignored)
config.yml        Default configuration (strategy params, runtime, cleanup, logging)
.env              Credentials for LIVE mode (gitignored, copy from .env.example)
```

## Strategy parameters

All parameters are configurable at runtime from the dashboard without restarting the bot:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `entry_window_min_sec` | 5 | Minimum time to close to enter a trade |
| `entry_window_max_sec` | 25 | Maximum time to close to enter a trade |
| `min_dtt` | 10.0 | Minimum distance BTC to threshold (USD) |
| `min_gain_usd` | 0.75 | Minimum potential gain to enter |
| `position_size_usd` | 10.0 | Size of each trade in USD |
| `snapshot_interval_ms` | 1000 | Snapshot cadence within logging window |
| `logging_window_buffer_sec` | 10 | Seconds before entry window to start snapshotting |

## Database cleanup

The bot runs an automatic daily cleanup at 03:00 local time. `market_snapshots` older than 7 days are summarized into `market_summaries` (one row per market) and deleted. Trades, signals, and strategy history are never deleted. Maximum DB size is approximately 70 MB.
