# Polymarket BTC Scalping Bot — Plan de Implementación

> **Modelo de planeación**: Claude Opus 4.7 (high effort)
> **Modelo de ejecución previsto**: Claude Sonnet 4.6
> **Estado**: v4 — todas las decisiones de diseño cerradas + política de cleanup. Listo para ejecutar.
> **Modo de trabajo**: Plan vivo. Cada step se ejecuta, se revisa, se marca como done. Pausas entre steps.

> **Reglas globales:**
> - Todo el código en inglés. Sin em dashes en comentarios o strings.
> - Type hints obligatorios en parámetros, returns y atributos de clase.
> - TDD estricto: el test va antes que la implementación en Domain y Use Cases.
> - Domain no importa nada de infra/FastAPI/SQLAlchemy/SDKs externos.
> - Inyección de dependencias en `bot_runner.py`, jamás dentro de los use cases.
> - Todos los timestamps en DB son UTC. La conversión a TZ local solo en presentación.

---

## Tabla de Contenidos

1. [Resumen ejecutivo](#resumen-ejecutivo)
2. [Decisiones de diseño (todas cerradas)](#decisiones-de-diseño-todas-cerradas)
3. [Schema definitivo de base de datos](#schema-definitivo-de-base-de-datos)
4. [Política de cleanup y archival](#política-de-cleanup-y-archival)
5. [Convenciones](#convenciones)
6. [Roadmap de fases](#roadmap-de-fases)
7. [Steps detallados](#steps-detallados)
8. [Changelog del plan](#changelog-del-plan)

---

## Resumen ejecutivo

Bot de scalping para mercados BTC de 5 minutos en Polymarket. Arranca en **PAPER mode** (loguea, no opera) con toggle a **LIVE**. Stack: Python (bot + FastAPI), SQLite + SQLAlchemy, React + Vite (dashboard). Arquitectura limpia en 4 capas.

**Estrategia parametrizada (todos los valores son modificables en runtime desde el dashboard, persisten en DB):**
- `entry_window_min_sec` / `entry_window_max_sec` (default 5 / 25)
- `min_dtt` (default 10.0 USD)
- `min_gain_usd` (default 0.75 USD)
- `position_size_usd` (default 10.0)
- `snapshot_interval_ms` (default 1000)
- `logging_window_buffer_sec` (default 10)

**Logging selectivo de snapshots**: solo dentro de la logging window (desde `entry_window_max + buffer` hasta cierre). Cadencia 1/seg. Las señales (`signal_events`) siempre se loguean.

**Métrica mensual**: `% mensual = PnL_mes ÷ total_invertido_mes × 100` (D12). Corte mensual día 1 00:00 → último día 23:59:59 en TZ configurable (default `America/El_Salvador`).

**Feeds:**
- BTC price: Binance WebSocket (BTCUSDT) principal + Coinbase WebSocket (BTC-USD) fallback automático.
- Polymarket markets: WebSocket si está habilitado, fallback Gamma REST cada 30s.

**Modo seguro**: cada arranque del bot empieza en PAPER. LIVE es siempre activación manual con confirmación.

**Cleanup automático diario (D15)**: cada día a las 03:00 TZ local, los `market_snapshots` con > 7 días de antigüedad se resumen en `market_summaries` (1 row por mercado) y se borran. Adicionalmente se construye `daily_summaries` (1 row por día con métricas agregadas). Trades, signals, resolutions y strategy_params **nunca se borran**. Mantiene la DB en orden de ~70 MB max.

---

## Decisiones de diseño (todas cerradas)

| # | Tema | Resolución |
|---|------|------------|
| D1 | Fuente del precio BTC | **Binance (BTCUSDT) WebSocket principal + Coinbase (BTC-USD) WebSocket fallback automático** (failover si primario stale > 3s). |
| D2 | Descubrimiento de mercados | **WebSocket Polymarket** si está disponible, **fallback Gamma REST cada 30s.** |
| D3 | Logging window de snapshots | Desde `time_to_close = entry_window_max + logging_window_buffer` (default 35s) hasta `time_to_close = 0`. Cadencia 1/seg, configurable. |
| D4 | Order book depth | **Top 10 niveles por lado**, persistidos como JSON. |
| D5 | Concurrencia | **`asyncio`** single-process. |
| D6 | Persistencia de snapshots | **Escritura inmediata** (sin buffer). |
| D7 | Auth Polymarket (LIVE) | **`.env` local** con 5 vars. PAPER no requiere keys. |
| D8 | Reglas de salida en PAPER | Hold hasta resolución del mercado. |
| D9 | Markets sin liquidez suficiente | `action_taken = 'SKIPPED'` con `skip_reason` enumerado. |
| D10 | Frontend auth | Sin auth (uso local en `localhost:5173`). |
| D11 | Timezone | **Configurable desde dashboard**, default `America/El_Salvador`. DB siempre UTC. |
| D12 | Cálculo del `%` mensual | **`PnL_mes ÷ sum(position_size_usd de cada trade del mes) × 100`.** |
| D13 | Toggle PAPER/LIVE | NO se persiste. Cada arranque empieza en PAPER. |
| D14 | Reescritura de `config.yml` | NO. Cambios runtime van a tablas `strategy_params` y `runtime_settings`. |
| **D15** | **Cleanup automático** | **Diario a las 03:00 TZ local. Solo `market_snapshots` con > 7 días se resume en `market_summaries` (1 row/mercado) y se borra. Adicionalmente `daily_summaries` con agregados del día. Trades/signals/resolutions/strategy_params NO se borran. Sin backup a archivo (borrado directo).** |

---

## Schema definitivo de base de datos

```sql
-- ============================================================
-- DATA OPERACIONAL (vida corta, se resume y borra)
-- ============================================================

-- Snapshots dentro de la "logging window" (D3). Se borran después de 7 días (D15).
CREATE TABLE market_snapshots (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME NOT NULL,                -- UTC
  market_id TEXT NOT NULL,
  time_to_close_sec INTEGER NOT NULL,
  btc_price REAL NOT NULL,
  btc_price_source TEXT NOT NULL,             -- 'binance' | 'coinbase'
  threshold REAL NOT NULL,
  dtt REAL NOT NULL,
  yes_price REAL NOT NULL,
  no_price REAL NOT NULL,
  spread REAL NOT NULL,
  book_depth_yes REAL NOT NULL,               -- suma USD del top 10
  book_depth_no REAL NOT NULL,
  book_levels_yes TEXT NOT NULL,              -- JSON: [{"price":0.51,"size":120}, ...10]
  book_levels_no TEXT NOT NULL,               -- JSON
  potential_gain_yes REAL NOT NULL,
  potential_gain_no REAL NOT NULL,
  strategy_params_id INTEGER NOT NULL,
  FOREIGN KEY (strategy_params_id) REFERENCES strategy_params(id)
);
CREATE INDEX idx_snapshots_market_time ON market_snapshots(market_id, timestamp);
CREATE INDEX idx_snapshots_timestamp ON market_snapshots(timestamp);  -- para cleanup

-- ============================================================
-- DATA TRANSACCIONAL (NUNCA se borra)
-- ============================================================

CREATE TABLE signal_events (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME NOT NULL,
  market_id TEXT NOT NULL,
  side TEXT NOT NULL CHECK(side IN ('YES','NO')),
  yes_price REAL NOT NULL,
  no_price REAL NOT NULL,
  btc_price REAL NOT NULL,
  btc_price_source TEXT NOT NULL,
  dtt REAL NOT NULL,
  time_to_close_sec INTEGER NOT NULL,
  potential_gain REAL NOT NULL,
  action_taken TEXT NOT NULL CHECK(action_taken IN ('SKIPPED','PAPER_TRADE','LIVE_TRADE')),
  skip_reason TEXT,
  strategy_params_id INTEGER NOT NULL,
  FOREIGN KEY (strategy_params_id) REFERENCES strategy_params(id)
);
CREATE INDEX idx_signals_market_time ON signal_events(market_id, timestamp);

CREATE TABLE trades (
  id INTEGER PRIMARY KEY,
  signal_id INTEGER NOT NULL,
  market_id TEXT NOT NULL,
  side TEXT NOT NULL CHECK(side IN ('YES','NO')),
  entry_price REAL NOT NULL,
  entry_btc_price REAL NOT NULL,
  entry_dtt REAL NOT NULL,
  entry_time_to_close INTEGER NOT NULL,
  position_size_usd REAL NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('OPEN','RESOLVED')),
  exit_price REAL,
  resolved_at DATETIME,
  pnl_usd REAL,
  pnl_pct REAL,
  mode TEXT NOT NULL CHECK(mode IN ('PAPER','LIVE')),
  opened_at DATETIME NOT NULL,
  FOREIGN KEY (signal_id) REFERENCES signal_events(id)
);
CREATE INDEX idx_trades_market ON trades(market_id);
CREATE INDEX idx_trades_status_mode ON trades(status, mode);
CREATE INDEX idx_trades_resolved_at ON trades(resolved_at);

CREATE TABLE market_resolutions (
  id INTEGER PRIMARY KEY,
  market_id TEXT NOT NULL UNIQUE,
  resolved_at DATETIME NOT NULL,
  threshold REAL NOT NULL,
  btc_price_at_close REAL NOT NULL,
  btc_price_source TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('YES','NO')),
  had_position INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- CONFIGURACIÓN (NUNCA se borra)
-- ============================================================

CREATE TABLE strategy_params (
  id INTEGER PRIMARY KEY,
  valid_from DATETIME NOT NULL,
  valid_to DATETIME,                          -- NULL = vigente
  entry_window_min_sec INTEGER NOT NULL,
  entry_window_max_sec INTEGER NOT NULL,
  min_dtt REAL NOT NULL,
  min_gain_usd REAL NOT NULL,
  position_size_usd REAL NOT NULL,
  snapshot_interval_ms INTEGER NOT NULL DEFAULT 1000,
  logging_window_buffer_sec INTEGER NOT NULL DEFAULT 10,
  updated_by TEXT NOT NULL CHECK(updated_by IN ('CONFIG','DASHBOARD'))
);
CREATE INDEX idx_strategy_params_valid ON strategy_params(valid_from, valid_to);

CREATE TABLE runtime_settings (
  id INTEGER PRIMARY KEY CHECK(id = 1),       -- singleton
  timezone TEXT NOT NULL DEFAULT 'America/El_Salvador',
  updated_at DATETIME NOT NULL
);

-- ============================================================
-- AGREGADOS (creados por el cleanup, NUNCA se borran)
-- ============================================================

-- Una fila por mercado archivado (snapshots ya fueron resumidos y borrados)
CREATE TABLE market_summaries (
  id INTEGER PRIMARY KEY,
  market_id TEXT NOT NULL UNIQUE,
  archived_at DATETIME NOT NULL,              -- cuándo lo procesó el cleanup
  closes_at DATETIME NOT NULL,                -- close time original (UTC)
  threshold REAL NOT NULL,
  outcome TEXT,                               -- YES/NO si se resolvió, NULL si no
  snapshots_count INTEGER NOT NULL,

  -- BTC price stats durante la logging window
  btc_price_min REAL NOT NULL,
  btc_price_max REAL NOT NULL,
  btc_price_avg REAL NOT NULL,
  btc_price_at_close REAL,                    -- último snapshot

  -- DTT stats
  dtt_min REAL NOT NULL,
  dtt_max REAL NOT NULL,
  dtt_avg REAL NOT NULL,

  -- Order book prices
  yes_price_min REAL NOT NULL,
  yes_price_max REAL NOT NULL,
  yes_price_avg REAL NOT NULL,
  no_price_min REAL NOT NULL,
  no_price_max REAL NOT NULL,
  no_price_avg REAL NOT NULL,
  spread_avg REAL NOT NULL,

  -- Liquidez (suma top 10 USD)
  book_depth_yes_avg REAL NOT NULL,
  book_depth_no_avg REAL NOT NULL,

  -- Activity
  signals_count INTEGER NOT NULL DEFAULT 0,
  signals_entered INTEGER NOT NULL DEFAULT 0,
  trades_count INTEGER NOT NULL DEFAULT 0,
  trades_pnl_usd REAL NOT NULL DEFAULT 0
);
CREATE INDEX idx_market_summaries_closes_at ON market_summaries(closes_at);

-- Una fila por día (TZ local), agregado de toda la actividad de ese día
CREATE TABLE daily_summaries (
  id INTEGER PRIMARY KEY,
  date DATE NOT NULL UNIQUE,                  -- en TZ local vigente al momento del cleanup

  total_markets_archived INTEGER NOT NULL,
  total_snapshots_archived INTEGER NOT NULL,

  total_signals INTEGER NOT NULL,
  signals_entered INTEGER NOT NULL,
  signals_skipped INTEGER NOT NULL,

  paper_trades_count INTEGER NOT NULL,
  paper_winning_trades INTEGER NOT NULL,
  paper_pnl_usd REAL NOT NULL,
  paper_invested_usd REAL NOT NULL,
  paper_pnl_pct REAL NOT NULL,

  live_trades_count INTEGER NOT NULL,
  live_winning_trades INTEGER NOT NULL,
  live_pnl_usd REAL NOT NULL,
  live_invested_usd REAL NOT NULL,
  live_pnl_pct REAL NOT NULL,

  win_rate REAL NOT NULL,
  cleanup_ran_at DATETIME NOT NULL
);

-- Performance snapshots (uso interno, periodos arbitrarios)
CREATE TABLE performance_snapshots (
  id INTEGER PRIMARY KEY,
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,
  total_signals INTEGER NOT NULL,
  signals_entered INTEGER NOT NULL,
  signals_skipped INTEGER NOT NULL,
  paper_pnl REAL NOT NULL,
  live_pnl REAL NOT NULL,
  win_rate REAL NOT NULL,
  avg_dtt_on_entry REAL,
  avg_time_to_close_on_entry REAL
);
```

---

## Política de cleanup y archival

**Trigger**: tarea async dentro del bot que despierta a las **03:00 TZ local** cada día. No requiere cron externo.

**Algoritmo (use case `RunDailyCleanup`):**

1. Determinar `cutoff_utc = now_utc - 7 days`.
2. Obtener todos los `market_id` de `market_snapshots` cuyo `MAX(timestamp) < cutoff_utc` Y que aún no estén en `market_summaries`.
3. Para cada uno:
   - Llamar `BuildMarketSummary(market_id)`:
     - Lee snapshots del mercado, calcula min/max/avg de las columnas relevantes.
     - Cuenta signals y trades asociados (no los toca, solo cuenta).
     - Inserta fila en `market_summaries`.
     - Borra los snapshots del mercado en una transacción.
4. Determinar fechas (en TZ local) que tienen markets archivados pero NO tienen `daily_summaries` aún.
5. Para cada fecha:
   - Llamar `BuildDailySummary(date)`:
     - Agrega `market_summaries`, `signal_events`, `trades` por esa fecha.
     - Inserta fila en `daily_summaries`.
6. Loguear `cleanup_ran_at`, `markets_processed`, `snapshots_deleted`, `daily_summaries_created`.

**Garantías:**
- Idempotente: correrlo dos veces el mismo día no produce duplicados (UNIQUE en `market_summaries.market_id` y `daily_summaries.date`).
- Atómico por mercado: si falla mid-cleanup, los markets ya procesados quedan completos; el resto se procesa en la próxima corrida.
- Sin pérdida de signals/trades (esos no se tocan).
- Estimación de tamaño post-cleanup: ~70 MB max (7 días de snapshots crudos), independiente de cuánto tiempo lleve corriendo el bot.

---

## Convenciones

### Nomenclatura de tests
`test_<comportamiento_esperado>_when_<condición>` — ej.: `test_returns_skip_when_dtt_below_threshold`.

### Definición de "Done"
Un step se marca ✅ cuando todos los criterios están tildados Y el comando de verificación pasa en verde.

---

## Roadmap de fases

| Fase | Nombre | Steps | Pausa al final |
|------|--------|-------|----------------|
| 0 | Scaffold y tooling | 0.1 – 0.6 | SÍ |
| 1 | Domain — value objects | 1.1 – 1.4 | SÍ |
| 2 | Domain — entities | 2.1 – 2.6 | SÍ |
| 3 | Domain — repository interfaces | 3.1 | SÍ |
| 4 | Use cases (TDD puro) | 4.1 – 4.10 | SÍ |
| 5 | Infrastructure — persistence | 5.1 – 5.4 | SÍ |
| 6 | Infrastructure — feeds | 6.1 – 6.4 | SÍ |
| 7 | Infrastructure — config + bootstrap | 7.1 – 7.2 | NO |
| 8 | Application — services + bot runner + cleanup scheduler | 8.1 – 8.5 | SÍ |
| 9 | API — FastAPI | 9.1 – 9.8 | SÍ |
| 10 | Dashboard — React + Vite | 10.1 – 10.10 | SÍ |
| 11 | Integration tests + smoke run en PAPER | 11.1 – 11.4 | SÍ |
| 12 | Hardening LIVE mode | 12.1 – 12.3 | SÍ (gate manual) |

---

## Steps detallados

### Fase 0 — Scaffold y tooling

#### ✅ Step 0.1 — Estructura de carpetas y archivos vacíos
**Capa**: DevOps
**Criterios de aceptación**:
- [x] `tree -I '__pycache__|node_modules|.git|.venv'` muestra el árbol completo del prompt original.
- [x] `python3 -c "import src.domain, src.infrastructure, src.application, src.api"` no falla.
- [x] `.gitignore` incluye `*.db`, `.env`, `__pycache__/`, `node_modules/`, `dist/`, `.venv/`.

#### ✅ Step 0.2 — `requirements.txt` y `requirements-dev.txt`
- `requirements.txt`:
  ```
  py-clob-client
  fastapi
  uvicorn[standard]
  sqlalchemy
  python-dotenv
  pyyaml
  httpx
  websockets
  pydantic
  pydantic-settings
  python-dateutil
  pytz
  structlog
  ```
- `requirements-dev.txt`:
  ```
  -r requirements.txt
  pytest
  pytest-asyncio
  pytest-cov
  pytest-mock
  faker
  ruff
  mypy
  freezegun
  ```
**Criterios de aceptación**:
- [x] `pip install -r requirements-dev.txt` instala sin error. (requiere `--extra-index-url https://pypi.org/simple/` en redes con mirror corporativo)

#### ✅ Step 0.3 — `config.yml` y `.env.example`
- `config.yml`:
  ```yaml
  strategy_defaults:
    entry_window_min_sec: 5
    entry_window_max_sec: 25
    min_dtt: 10.0
    min_gain_usd: 0.75
    position_size_usd: 10.0
    snapshot_interval_ms: 1000
    logging_window_buffer_sec: 10
  runtime:
    mode: PAPER
    btc_feed_primary: binance
    btc_feed_fallback: coinbase
    btc_feed_failover_threshold_sec: 3
    market_discovery_websocket: true
    market_discovery_rest_interval_sec: 30
    timezone_default: America/El_Salvador
  cleanup:
    snapshots_retention_days: 7
    daily_run_hour_local: 3        # 03:00 TZ local
  storage:
    sqlite_path: data/polybot.db
  logging:
    level: INFO
    json: true
  ```
- `.env.example`:
  ```
  POLYMARKET_PRIVATE_KEY=
  POLYMARKET_PROXY_ADDRESS=
  POLYMARKET_API_KEY=
  POLYMARKET_API_SECRET=
  POLYMARKET_API_PASSPHRASE=
  API_HOST=127.0.0.1
  API_PORT=8000
  ```

#### ✅ Step 0.4 — `pyproject.toml` con configuración de pytest, ruff, mypy

#### ✅ Step 0.5 — `README.md` actualizado

#### ✅ Step 0.6 — Logger estructurado base
**Pausa de revisión**: SÍ — fin Fase 0.

---

### Fase 1 — Domain · Value Objects

#### ✅ Step 1.1 — `Price`
#### ✅ Step 1.2 — `DTT`
#### ✅ Step 1.3 — `TimeWindow`
#### ✅ Step 1.4 — `StrategyParams`
**Pausa de revisión**: SÍ — fin Fase 1.

---

### Fase 2 — Domain · Entities

#### ✅ Step 2.1 — `Market`
#### ✅ Step 2.2 — `Snapshot` (con `book_levels_yes/no` como lista de `(price, size)` top 10)
#### ✅ Step 2.3 — `Signal` (con enum `SkipReason`)
#### ✅ Step 2.4 — `Trade`
#### ✅ Step 2.5 — `MonthlyPerformance`
**Atributos**: `year`, `month`, `timezone`, `pnl_usd_paper`, `pnl_usd_live`, `pnl_pct_paper`, `pnl_pct_live`, `total_trades`, `winning_trades`, `total_invested_usd_paper`, `total_invested_usd_live`.
**Fórmula `%`** (D12): `pnl_pct = (pnl_usd / total_invested_usd) * 100` por mode. Si `total_invested == 0` → `pct = 0`.

#### ✅ Step 2.6 — `MarketSummary` y `DailySummary`
Value objects que matchean las nuevas tablas de agregados. Tests:
- `MarketSummary.from_snapshots(snapshots, signals, trades)` factory que computa todos los stats.
- `DailySummary.from_market_summaries(...)` factory.
**Pausa de revisión**: SÍ — fin Fase 2.

---

### Fase 3 — Domain · Repository Interfaces

#### ✅ Step 3.1 — Interfaces abstractas
- `signal_repository.py`
- `trade_repository.py` — incluye `list_resolved_between(start_utc, end_utc)`, `sum_invested_between(start_utc, end_utc, mode)`.
- `snapshot_repository.py` — incluye `list_market_ids_with_snapshots_older_than(cutoff_utc)`, `list_by_market(market_id)`, `delete_by_market(market_id)`.
- `market_resolution_repository.py`
- `performance_repository.py`
- `strategy_params_repository.py`
- `runtime_settings_repository.py`
- `market_summary_repository.py` — `save`, `get_by_market_id`, `list_by_date_range(start_utc, end_utc)`.
- `daily_summary_repository.py` — `save`, `get_by_date(date)`, `list_dates_without_summary(date_range)`.
**Criterios de aceptación**:
- [ ] Todos `@abstractmethod`, type hints completos.
- [ ] Importarlos no trae nada de SQLAlchemy.
**Pausa de revisión**: SÍ.

---

### Fase 4 — Use Cases

#### ✅ Step 4.1 — `EvaluateSignal` (5 reglas + ENTER, 13 tests)
#### ✅ Step 4.2 — `ExecuteTrade` (PAPER y LIVE, 6 tests)
#### ✅ Step 4.3 — `ResolveMarket` (idempotente, 6 tests)
#### ✅ Step 4.4 — `UpdateStrategyParams` (versionado, 4 tests)
#### ✅ Step 4.5 — `GetCurrentStrategyParams` (2 tests)
#### ✅ Step 4.6 — `GetMonthlyPerformance` (D12, TZ-aware, 7 tests)
#### ✅ Step 4.7 — `UpdateRuntimeSettings` (timezone toggle, 4 tests)

#### ✅ Step 4.8 — `BuildMarketSummary`
**Input**: `market_id`. **Output**: `MarketSummary` persistido.
**Reglas**:
1. Lee todos los snapshots del market.
2. Lee signals y trades asociados (count + sum de pnl).
3. Computa min/max/avg.
4. Persiste `MarketSummary`.
5. Borra snapshots del market en una transacción.
6. Idempotente: si ya existe `market_summaries.market_id`, no hace nada.
**Tests**:
- `test_creates_summary_with_correct_aggregates`
- `test_deletes_raw_snapshots_after_summary`
- `test_idempotent_when_called_twice`
- `test_handles_market_with_zero_signals_and_trades`
- `test_atomic_failure_does_not_partially_delete`

#### ✅ Step 4.9 — `BuildDailySummary`
**Input**: `date` (en TZ local), `tz`. **Output**: `DailySummary` persistido.
**Reglas**:
1. Convierte rango de día local a UTC.
2. Lee `market_summaries` con `closes_at` en el rango.
3. Lee `signal_events` y `trades` en el rango (`resolved_at`).
4. Computa agregados (PnL y `%` por mode usando D12).
5. Persiste `DailySummary`.
6. Idempotente por `UNIQUE(date)`.
**Tests**:
- `test_aggregates_pnl_per_mode_correctly`
- `test_pnl_pct_uses_d12_formula`
- `test_zero_when_no_activity_that_day`
- `test_handles_trades_that_resolved_across_day_boundary_in_local_tz`

#### ✅ Step 4.10 — `RunDailyCleanup` (orchestrator)
**Input**: `now_utc`, `retention_days`, `tz`.
**Reglas** (algoritmo de la sección "Política de cleanup"):
1. `cutoff = now_utc - retention_days`.
2. Para cada `market_id` con snapshots viejos no archivados → `BuildMarketSummary`.
3. Para cada fecha sin `daily_summary` → `BuildDailySummary`.
4. Loguea métricas del run.
**Tests**:
- `test_processes_only_markets_older_than_retention`
- `test_skips_already_archived_markets`
- `test_creates_daily_summary_for_each_processed_date`
- `test_idempotent_full_run`
- `test_resilient_to_partial_failure_in_one_market`
**Pausa de revisión**: SÍ — fin Fase 4.

---

### Fase 5 — Infrastructure · Persistence

#### ✅ Step 5.1 — Modelos SQLAlchemy (9 tablas, 100% coverage)
#### ✅ Step 5.2 — `Database` engine + `init_schema()` + `seed_defaults()` (idempotente)
#### ✅ Step 5.3 — Implementaciones de repositorios (48 tests con SQLite :memory:, 100% coverage)
#### ✅ Step 5.4 — Mappers `models <-> entities` (roundtrip incluye book_levels JSON)
**Pausa de revisión**: SÍ — fin Fase 5.

---

### Fase 6 — Infrastructure · Feeds

#### ✅ Step 6.1 — `BinanceFeed` (BTC price principal, 100%)
#### ✅ Step 6.2 — `CoinbaseFeed` (BTC price fallback, 100%)
#### ✅ Step 6.3 — `FailoverBTCFeed` (coordinador, 100%)
#### ✅ Step 6.4 — `PolymarketFeed` + `NullOrderExecutor` (100%)
**Pausa de revisión**: SÍ — fin Fase 6.

---

### Fase 7 — Infrastructure · Config + bootstrap

#### ✅ Step 7.1 — `Settings` loader (validación PAPER vs LIVE, 100%)
#### ✅ Step 7.2 — `bootstrap(session, settings)` siembra strategy_params y runtime_settings (100%)
**Pausa de revisión**: NO

---

### Fase 8 — Application

#### ✅ Step 8.1 — `MarketMonitorService` (100%)
#### ✅ Step 8.2 — `MarketDiscoveryService` (100%)
#### ✅ Step 8.3 — `EventBus` + 4 topic constants (100%)
#### ✅ Step 8.4 — `bot_runner.py` entry point (run() y main() con pragma no cover — cubiertos en Fase 11)
#### ✅ Step 8.5 — `DailyCleanupScheduler` (NUEVO)
**Objetivo**: Tarea async que despierta cada día a las `cleanup.daily_run_hour_local` en TZ vigente y ejecuta `RunDailyCleanup`.
**Implementación**:
- Calcula `next_run_utc` basado en TZ vigente.
- `await asyncio.sleep(seconds_until_next_run)`.
- Ejecuta `RunDailyCleanup`.
- Publica evento `cleanup.ran` en bus.
- Loop infinito.
- Suscribe a `runtime_settings.updated` para recalcular `next_run` si cambia la TZ.
**Tests** (con `freezegun`):
- `test_calculates_next_run_at_3am_local_tz`
- `test_recalculates_next_run_when_timezone_changes`
- `test_invokes_run_daily_cleanup_when_fired`
- `test_resilient_to_cleanup_failure_logs_and_retries_tomorrow`
**Criterios de aceptación**:
- [ ] Test pasa con `freezegun` simulando avance del tiempo.
- [ ] Se integra al `bot_runner.py` como tarea adicional.
**Pausa de revisión**: SÍ — fin Fase 8.

---

### Fase 9 — API (FastAPI)

#### Step 9.1 — `main.py` con CORS, lifespan, routers
- [ ] `GET /health` retorna `{"status":"ok","mode":"PAPER","current_params_id":N,"timezone":"America/El_Salvador","btc_feed_active":"binance"}`.

#### Step 9.2 — Router `signals.py`
#### Step 9.3 — Router `trades.py`
#### Step 9.4 — Router `snapshots.py` + `markets/active` + `POST /mode`
#### Step 9.5 — Router `strategy.py` (GET, PATCH, history)
#### Step 9.6 — Router `performance.py` (`GET /performance/monthly`, `GET /performance/daily?date=`)
#### Step 9.7 — Router `settings.py` (`GET`, `PATCH /settings` para timezone)

#### Step 9.8 — Router `maintenance.py` (NUEVO)
- `GET /maintenance/status` retorna:
  - `last_cleanup_at`
  - `oldest_raw_snapshot_timestamp`
  - `total_raw_snapshots`
  - `total_archived_markets`
  - `total_daily_summaries`
  - `next_cleanup_at` (calculado en base a TZ vigente)
- Tests cubren DB vacía y DB con datos.
**Pausa de revisión**: SÍ — fin Fase 9.

---

### Fase 10 — Dashboard (React + Vite + TypeScript)

#### Step 10.1 — Bootstrap Vite + TS
#### Step 10.2 — Cliente API tipado (incluye `MarketSummary`, `DailySummary`, `MaintenanceStatus`)
#### Step 10.3 — Panel principal: BTC vs threshold + indicador de feed activo
#### Step 10.4 — Feed de señales en vivo
#### Step 10.5 — Trades + métricas globales
#### Step 10.6 — Card de performance MENSUAL (D12)
#### Step 10.7 — Toggle PAPER/LIVE con confirmación
#### Step 10.8 — Panel de configuración de estrategia (sliders/inputs)
#### Step 10.9 — Settings: selector de timezone

#### Step 10.10 — Card de DB Status (NUEVO)
**Objetivo**: visibilidad del estado de almacenamiento y cleanup.
**Contenido**:
- Último cleanup ejecutado (timestamp en TZ local).
- Próximo cleanup programado.
- Snapshots crudos en DB (count + tamaño aprox MB).
- Mercados archivados (count).
- Días resumidos (count).
- Snapshot más viejo (timestamp).
- Tabla expandible: últimos 10 días con su `daily_summary` (PnL, trades, win rate).
- Llama `GET /maintenance/status` cada 60s.
**Sin botón de cleanup manual** (D15 elegida solo automático).
**Pausa de revisión**: SÍ — fin Fase 10.

---

### Fase 11 — Integration y smoke run en PAPER

#### ✅ Step 11.1 — Test integration end-to-end del bot
18 tests en `tests/integration/test_bot_runner.py`:
- [x] Genera ≥ 1 signal y ≥ 1 trade en PAPER.
- [x] Resuelve mercado simulado con pnl correcto (YES wins: +15.0, NO wins: -10.0).
- [x] Cambio de strategy_params mid-run respetado (via EventBus).
- [x] Failover BTC funciona si Binance simula desconexión.
**BUG FIX (detectado por tests)**: `ResolveMarket` tenia un error: cuando outcome=NO, el YES trade recibia `trade_exit = 1.0 - 0.0 = 1.0` (ganadora falsa). Corregido a `trade_exit = 1.0 if trade.side == outcome else 0.0`.

#### ✅ Step 11.2 — Test integration API
61 tests en `tests/integration/test_api_endpoints.py` (completado en Fase 9).

#### ✅ Step 11.3 — Test integration cleanup (NUEVO)
15 tests en `tests/integration/test_cleanup.py`:
- [x] Sembrar DB con snapshots de hace 8 dias + algunos recientes.
- [x] Correr `RunDailyCleanup`.
- [x] Verificar que solo los > 7 dias fueron archivados y borrados.
- [x] Verificar que `market_summaries` y `daily_summaries` se crearon correctamente.
- [x] Correrlo de nuevo: idempotente, no duplica filas ni borra nada nuevo.

#### Step 11.4 — Smoke run real (PAPER) por 10 minutos
Binance + Coinbase + Polymarket reales (read-only). Gate manual.
- [ ] Sin excepciones.
- [ ] Snapshots solo dentro de logging window.
- [ ] Memoria estable.
- [ ] Si simulamos desconexion del primary feed, failover funciona (ya cubierto en 11.1).
Comando: `source .venv/bin/activate && python -m src.application.bot_runner`
**Pausa de revision**: SI — fin Fase 11.

---

### Fase 12 — Hardening LIVE mode

#### Step 12.1 — `LiveOrderExecutor` con `py-clob-client`
#### Step 12.2 — Kill switch (`MAX_DAILY_LOSS_USD`, `MAX_OPEN_TRADES`)
#### Step 12.3 — `live_preflight()` antes de habilitar LIVE
**Pausa de revisión**: SÍ — gate manual antes de habilitar LIVE en producción.

---

## Changelog del plan

| Fecha | Versión | Cambio | Autor |
|-------|---------|--------|-------|
| 2026-04-25 | v1 | Versión inicial generada por Opus 4.7 | Carlos + Claude |
| 2026-04-25 | v2 | Strategy params dinámicos + tabla `strategy_params`; logging selectivo (D3); métrica mensual + endpoint `/performance/monthly`; nuevos use cases | Carlos + Claude |
| 2026-04-26 | v3 | Cierre de TODAS las decisiones D1–D14: feeds dual con failover, top 10 book levels en JSON, asyncio, escritura inmediata, .env, TZ configurable El Salvador, fórmula `%` mensual, modo PAPER siempre al arrancar. Schema actualizado: `book_levels_yes/no`, `btc_price_source`, `runtime_settings`. | Carlos + Claude |
| 2026-04-26 | v4 | **D15 cleanup automático**. Nuevas tablas `market_summaries` y `daily_summaries`. Use cases `BuildMarketSummary`, `BuildDailySummary`, `RunDailyCleanup`. Service `DailyCleanupScheduler` (corre 03:00 TZ local). Nuevo router `/maintenance/status`. Nueva card `DB Status` en dashboard (Step 10.10). Test integration de cleanup (Step 11.3). | Carlos + Claude |
| 2026-04-30 | v5 | **Phase 11 integration tests**. 18 tests end-to-end bot (11.1), 15 tests cleanup (11.3). BUG FIX en `ResolveMarket`: formula de `trade_exit` incorrecta para trades perdedores (NO outcome). Total: 424 tests, 100% cobertura en API + domain. | Carlos + Claude |
| _(pendiente)_ | — | Proximas modificaciones del usuario | Carlos |
