"""Integration tests for all FastAPI API endpoints (Phase 9)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.dependencies import AppState
from src.api.main import create_app
from src.infrastructure.persistence.database import init_schema, seed_defaults
from src.infrastructure.persistence.models import (
    DailySummaryModel,
    MarketSnapshotModel,
    MarketSummaryModel,
    SignalEventModel,
    StrategyParamsModel,
    TradeModel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    # StaticPool ensures all sessions share the same in-memory SQLite connection,
    # so API requests see the same data as the test fixture.
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_schema(e)
    return e


@pytest.fixture
def session_factory(engine):
    factory = sessionmaker(bind=engine)
    with factory() as session:
        seed_defaults(session)
    return factory


@pytest.fixture
def state():
    return AppState(
        mode="PAPER",
        btc_feed_active="binance",
        active_markets=["market-1", "market-2"],
    )


@pytest.fixture
def client(session_factory, state):
    app = create_app(state=state, session_factory=session_factory)
    return TestClient(app)


def _seed_data(engine) -> None:
    """Seed signals, trades, and snapshots for tests that need data."""
    factory = sessionmaker(bind=engine)
    now = datetime.now(tz=timezone.utc)

    with factory() as session:
        params = session.query(StrategyParamsModel).filter_by(valid_to=None).first()
        params_id = params.id

        session.add(SignalEventModel(
            timestamp=(now - timedelta(minutes=5)).replace(tzinfo=None),
            market_id="market-1",
            side="YES",
            yes_price=0.6,
            no_price=0.4,
            btc_price=95000.0,
            btc_price_source="binance",
            dtt=500.0,
            time_to_close_sec=20,
            potential_gain=0.80,
            action_taken="PAPER_TRADE",
            skip_reason=None,
            strategy_params_id=params_id,
        ))
        session.add(SignalEventModel(
            timestamp=(now - timedelta(minutes=2)).replace(tzinfo=None),
            market_id="market-2",
            side="NO",
            yes_price=0.4,
            no_price=0.6,
            btc_price=94000.0,
            btc_price_source="coinbase",
            dtt=1000.0,
            time_to_close_sec=15,
            potential_gain=0.75,
            action_taken="SKIPPED",
            skip_reason="DTT_BELOW_MIN",
            strategy_params_id=params_id,
        ))

        session.add(TradeModel(
            signal_id=1,
            market_id="market-1",
            side="YES",
            entry_price=0.6,
            entry_btc_price=95000.0,
            entry_dtt=500.0,
            entry_time_to_close=20,
            position_size_usd=10.0,
            status="OPEN",
            exit_price=None,
            resolved_at=None,
            pnl_usd=None,
            pnl_pct=None,
            mode="PAPER",
            opened_at=(now - timedelta(minutes=5)).replace(tzinfo=None),
        ))

        session.add(MarketSnapshotModel(
            timestamp=(now - timedelta(minutes=1)).replace(tzinfo=None),
            market_id="market-1",
            time_to_close_sec=10,
            btc_price=95100.0,
            btc_price_source="binance",
            threshold=95000.0,
            dtt=100.0,
            yes_price=0.62,
            no_price=0.38,
            spread=0.0,
            book_depth_yes=500.0,
            book_depth_no=300.0,
            book_levels_yes="[[0.62, 100]]",
            book_levels_no="[[0.38, 100]]",
            potential_gain_yes=0.77,
            potential_gain_no=1.05,
            strategy_params_id=params_id,
        ))

        session.commit()


@pytest.fixture
def seeded_client(engine, session_factory, state):
    _seed_data(engine)
    app = create_app(state=state, session_factory=sessionmaker(bind=engine))
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200_with_ok_status(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_returns_paper_mode_by_default(self, client: TestClient) -> None:
        assert client.get("/health").json()["mode"] == "PAPER"

    def test_returns_current_params_id_as_int(self, client: TestClient) -> None:
        assert isinstance(client.get("/health").json()["current_params_id"], int)

    def test_returns_configured_timezone(self, client: TestClient) -> None:
        assert client.get("/health").json()["timezone"] == "America/El_Salvador"

    def test_returns_btc_feed_active(self, client: TestClient) -> None:
        assert client.get("/health").json()["btc_feed_active"] == "binance"


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class TestSignals:
    def test_list_signals_empty(self, client: TestClient) -> None:
        response = client.get("/signals")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_signals_returns_results(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/signals")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_signals_filters_by_market_id(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/signals?market_id=market-1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["market_id"] == "market-1"

    def test_list_signals_respects_limit(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/signals?limit=1")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_signal_schema_has_id_and_required_fields(self, seeded_client: TestClient) -> None:
        data = seeded_client.get("/signals").json()[0]
        for field in ("id", "timestamp", "market_id", "side", "action_taken", "strategy_params_id"):
            assert field in data

    def test_list_signals_ordered_newest_first(self, seeded_client: TestClient) -> None:
        data = seeded_client.get("/signals").json()
        # market-2 signal was 2 min ago, market-1 was 5 min ago
        assert data[0]["market_id"] == "market-2"


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

class TestTrades:
    def test_list_trades_empty(self, client: TestClient) -> None:
        response = client.get("/trades")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_trades_returns_results(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/trades")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_trades_filters_by_mode_paper(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/trades?mode=PAPER")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_trades_filters_by_mode_live_empty(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/trades?mode=LIVE")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_trades_filters_by_status_open(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/trades?status=OPEN")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_trades_filters_by_status_resolved_empty(self, seeded_client: TestClient) -> None:
        assert seeded_client.get("/trades?status=RESOLVED").json() == []

    def test_trade_schema_has_required_fields(self, seeded_client: TestClient) -> None:
        data = seeded_client.get("/trades").json()[0]
        for field in ("id", "market_id", "side", "status", "mode", "position_size_usd", "opened_at"):
            assert field in data


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

class TestSnapshots:
    def test_list_snapshots_market_id_required(self, client: TestClient) -> None:
        response = client.get("/snapshots")
        assert response.status_code == 422

    def test_list_snapshots_returns_empty_for_unknown_market(self, client: TestClient) -> None:
        response = client.get("/snapshots?market_id=unknown")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_snapshots_for_known_market(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/snapshots?market_id=market-1")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_snapshots_respects_limit(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/snapshots?market_id=market-1&limit=1")
        assert response.status_code == 200
        assert len(response.json()) <= 1

    def test_snapshot_schema_has_required_fields(self, seeded_client: TestClient) -> None:
        data = seeded_client.get("/snapshots?market_id=market-1").json()[0]
        for field in ("id", "timestamp", "market_id", "btc_price", "dtt", "yes_price"):
            assert field in data


# ---------------------------------------------------------------------------
# Markets active
# ---------------------------------------------------------------------------

class TestMarketsActive:
    def test_returns_configured_active_markets(self, client: TestClient) -> None:
        response = client.get("/markets/active")
        assert response.status_code == 200
        assert set(response.json()) == {"market-1", "market-2"}

    def test_returns_empty_list_when_no_active_markets(self, engine, session_factory) -> None:
        empty_state = AppState(mode="PAPER", btc_feed_active="binance", active_markets=[])
        app = create_app(state=empty_state, session_factory=session_factory)
        c = TestClient(app)
        assert c.get("/markets/active").json() == []


# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------

class TestMode:
    def test_post_mode_to_live(self, client: TestClient) -> None:
        response = client.post("/mode", json={"mode": "LIVE"})
        assert response.status_code == 200
        assert response.json()["mode"] == "LIVE"

    def test_post_mode_updates_state(self, client: TestClient, state: AppState) -> None:
        client.post("/mode", json={"mode": "LIVE"})
        assert state.mode == "LIVE"

    def test_post_mode_back_to_paper(self, client: TestClient, state: AppState) -> None:
        state.mode = "LIVE"
        response = client.post("/mode", json={"mode": "PAPER"})
        assert response.status_code == 200
        assert response.json()["mode"] == "PAPER"

    def test_post_mode_invalid_returns_422(self, client: TestClient) -> None:
        response = client.post("/mode", json={"mode": "INVALID"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

class TestStrategy:
    def test_get_current_strategy_has_id(self, client: TestClient) -> None:
        response = client.get("/strategy")
        assert response.status_code == 200
        assert isinstance(response.json()["id"], int)

    def test_get_current_strategy_default_values(self, client: TestClient) -> None:
        data = client.get("/strategy").json()
        assert data["entry_window_min_sec"] == 5
        assert data["entry_window_max_sec"] == 25
        assert data["min_dtt"] == 10.0

    def test_get_strategy_history_returns_list(self, client: TestClient) -> None:
        response = client.get("/strategy/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    def test_get_strategy_history_record_has_metadata(self, client: TestClient) -> None:
        record = client.get("/strategy/history").json()[0]
        for field in ("id", "valid_from", "updated_by"):
            assert field in record

    def test_patch_strategy_updates_single_field(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"min_dtt": 15.0})
        assert response.status_code == 200
        assert response.json()["min_dtt"] == 15.0

    def test_patch_strategy_preserves_unset_fields(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"min_dtt": 12.0})
        data = response.json()
        assert data["entry_window_min_sec"] == 5
        assert data["entry_window_max_sec"] == 25

    def test_patch_strategy_invalid_position_size_returns_422(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"position_size_usd": -1.0})
        assert response.status_code == 422

    def test_patch_strategy_zero_snapshot_interval_returns_422(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"snapshot_interval_ms": 0})
        assert response.status_code == 422

    def test_patch_strategy_negative_min_dtt_returns_422(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"min_dtt": -1.0})
        assert response.status_code == 422

    def test_patch_strategy_negative_min_gain_returns_422(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"min_gain_usd": -0.5})
        assert response.status_code == 422

    def test_patch_strategy_valid_positive_position_size(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"position_size_usd": 50.0})
        assert response.status_code == 200
        assert response.json()["position_size_usd"] == 50.0

    def test_patch_strategy_valid_snapshot_interval(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"snapshot_interval_ms": 500})
        assert response.status_code == 200
        assert response.json()["snapshot_interval_ms"] == 500

    def test_patch_strategy_valid_min_gain_usd(self, client: TestClient) -> None:
        response = client.patch("/strategy", json={"min_gain_usd": 1.5})
        assert response.status_code == 200
        assert response.json()["min_gain_usd"] == 1.5

    def test_patch_strategy_min_window_exceeds_max_returns_422(self, client: TestClient) -> None:
        # domain ValueError: TimeWindow min_sec > max_sec → caught by except block in router
        response = client.patch("/strategy", json={"entry_window_min_sec": 30, "entry_window_max_sec": 5})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_get_monthly_empty_returns_zero_metrics(self, client: TestClient) -> None:
        response = client.get("/performance/monthly?year=2026&month=4")
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0
        assert data["pnl_pct_paper"] == 0.0
        assert data["pnl_pct_live"] == 0.0

    def test_get_monthly_uses_db_timezone_when_tz_not_provided(self, client: TestClient) -> None:
        response = client.get("/performance/monthly?year=2026&month=4")
        assert response.status_code == 200
        assert response.json()["timezone"] == "America/El_Salvador"

    def test_get_monthly_accepts_custom_timezone(self, client: TestClient) -> None:
        response = client.get("/performance/monthly?year=2026&month=4&tz=America/New_York")
        assert response.status_code == 200
        assert response.json()["timezone"] == "America/New_York"

    def test_get_monthly_missing_year_returns_422(self, client: TestClient) -> None:
        assert client.get("/performance/monthly?month=4").status_code == 422

    def test_get_monthly_missing_month_returns_422(self, client: TestClient) -> None:
        assert client.get("/performance/monthly?year=2026").status_code == 422

    def test_get_daily_not_found_returns_404(self, client: TestClient) -> None:
        response = client.get("/performance/daily?date=2026-01-01")
        assert response.status_code == 404

    def test_get_daily_with_data_returns_summary(self, engine, session_factory, state) -> None:
        factory = sessionmaker(bind=engine)
        now = datetime.now(tz=timezone.utc)
        with factory() as session:
            session.add(DailySummaryModel(
                date="2026-04-01",
                total_markets_archived=1,
                total_snapshots_archived=10,
                total_signals=5,
                signals_entered=2,
                signals_skipped=3,
                paper_trades_count=2,
                paper_winning_trades=1,
                paper_pnl_usd=0.5,
                paper_invested_usd=20.0,
                live_trades_count=0,
                live_winning_trades=0,
                live_pnl_usd=0.0,
                live_invested_usd=0.0,
                win_rate=0.5,
                cleanup_ran_at=now.replace(tzinfo=None),
            ))
            session.commit()
        app = create_app(state=state, session_factory=factory)
        c = TestClient(app)
        response = c.get("/performance/daily?date=2026-04-01")
        assert response.status_code == 200
        assert response.json()["date"] == "2026-04-01"

    def test_get_daily_missing_date_returns_422(self, client: TestClient) -> None:
        assert client.get("/performance/daily").status_code == 422


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_get_settings_returns_default_timezone(self, client: TestClient) -> None:
        response = client.get("/settings")
        assert response.status_code == 200
        assert response.json()["timezone"] == "America/El_Salvador"

    def test_get_settings_has_updated_at(self, client: TestClient) -> None:
        assert "updated_at" in client.get("/settings").json()

    def test_patch_settings_timezone(self, client: TestClient) -> None:
        response = client.patch("/settings", json={"timezone": "America/New_York"})
        assert response.status_code == 200
        assert response.json()["timezone"] == "America/New_York"

    def test_patch_settings_get_reflects_change(self, client: TestClient) -> None:
        client.patch("/settings", json={"timezone": "UTC"})
        assert client.get("/settings").json()["timezone"] == "UTC"

    def test_patch_settings_invalid_timezone_returns_422(self, client: TestClient) -> None:
        response = client.patch("/settings", json={"timezone": "Not/A/Zone"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

class TestMaintenance:
    def test_maintenance_status_empty_db(self, client: TestClient) -> None:
        response = client.get("/maintenance/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total_raw_snapshots"] == 0
        assert data["total_archived_markets"] == 0
        assert data["total_daily_summaries"] == 0
        assert data["last_cleanup_at"] is None
        assert data["oldest_raw_snapshot_timestamp"] is None
        assert "next_cleanup_at" in data

    def test_maintenance_status_counts_raw_snapshots(self, seeded_client: TestClient) -> None:
        response = seeded_client.get("/maintenance/status")
        assert response.status_code == 200
        assert response.json()["total_raw_snapshots"] == 1

    def test_maintenance_status_has_oldest_timestamp_when_data_exists(self, seeded_client: TestClient) -> None:
        data = seeded_client.get("/maintenance/status").json()
        assert data["oldest_raw_snapshot_timestamp"] is not None

    def test_maintenance_status_counts_archived_markets(self, engine, session_factory, state) -> None:
        factory = sessionmaker(bind=engine)
        now = datetime.now(tz=timezone.utc)
        with factory() as session:
            session.add(MarketSummaryModel(
                market_id="archived-1",
                archived_at=now.replace(tzinfo=None),
                closes_at=(now - timedelta(days=8)).replace(tzinfo=None),
                threshold=95000.0,
                outcome="YES",
                snapshots_count=100,
                btc_price_min=94000.0, btc_price_max=96000.0, btc_price_avg=95000.0,
                btc_price_at_close=95500.0,
                dtt_min=100.0, dtt_max=2000.0, dtt_avg=500.0,
                yes_price_min=0.5, yes_price_max=0.8, yes_price_avg=0.65,
                no_price_min=0.2, no_price_max=0.5, no_price_avg=0.35,
                spread_avg=0.0,
                book_depth_yes_avg=300.0, book_depth_no_avg=200.0,
                signals_count=3, signals_entered=1,
                trades_count=1, trades_pnl_usd=0.5,
            ))
            session.commit()
        app = create_app(state=state, session_factory=factory)
        c = TestClient(app)
        assert c.get("/maintenance/status").json()["total_archived_markets"] == 1

    def test_maintenance_next_cleanup_at_is_in_the_future(self, client: TestClient) -> None:
        data = client.get("/maintenance/status").json()
        next_cleanup = datetime.fromisoformat(data["next_cleanup_at"].replace("Z", "+00:00"))
        assert next_cleanup > datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# _compute_next_cleanup_utc branch coverage
# ---------------------------------------------------------------------------

class TestComputeNextCleanupUtc:
    """Direct unit tests for the _compute_next_cleanup_utc helper in maintenance.py.

    The API integration tests above always run at daytime, so run_hour=3 has
    already passed and the +1 day branch is always taken.  These tests use
    freezegun to exercise both branches explicitly.
    """

    def test_adds_one_day_when_run_hour_already_passed_today(self) -> None:
        """Branch 28->29: target_local <= now_local -> +1 day (branch is covered by API tests too)."""
        from freezegun import freeze_time
        from src.api.routers.maintenance import _compute_next_cleanup_utc
        # 14:00 UTC = 08:00 El Salvador; run_hour=3 already passed -> +1 day
        with freeze_time("2026-04-26 14:00:00 UTC"):
            result = _compute_next_cleanup_utc(run_hour=3, timezone_str="America/El_Salvador")
        expected = datetime(2026, 4, 27, 9, 0, 0, tzinfo=timezone.utc)  # Apr 27 03:00 ESV = 09:00 UTC
        assert abs((result - expected).total_seconds()) < 2

    def test_no_day_added_when_run_hour_not_yet_passed_today(self) -> None:
        """Branch 28->30: target_local > now_local -> no +1 day (covers the skipped branch)."""
        from freezegun import freeze_time
        from src.api.routers.maintenance import _compute_next_cleanup_utc
        # 09:00 UTC = 03:00 El Salvador; run_hour=22 hasn't passed yet -> same day
        with freeze_time("2026-04-30 09:00:00 UTC"):
            result = _compute_next_cleanup_utc(run_hour=22, timezone_str="America/El_Salvador")
        # 22:00 El Salvador = 04:00 UTC next day (Apr 30 22:00 ESV + 6h = May 1 04:00 UTC)
        expected = datetime(2026, 5, 1, 4, 0, 0, tzinfo=timezone.utc)
        assert abs((result - expected).total_seconds()) < 2
