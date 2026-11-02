"""Integration tests for RunDailyCleanup against a real SQLite :memory: DB.

Step 11.3 per PLAN.md:
- Seed DB with snapshots > 7 days old AND some recent snapshots.
- Run RunDailyCleanup.
- Verify only old markets are archived and deleted.
- Verify market_summaries and daily_summaries are created correctly.
- Verify idempotency: running again does not duplicate anything.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.use_cases.run_daily_cleanup import RunDailyCleanup
from src.domain.use_cases.resolve_market import ResolveMarket
from src.domain.entities.trade import TradeMode, TradeStatus, Trade
from src.infrastructure.persistence.database import init_schema, seed_defaults
from src.infrastructure.persistence.models import (
    MarketSnapshotModel,
    MarketSummaryModel,
    DailySummaryModel,
    SignalEventModel,
    TradeModel,
)
from src.infrastructure.persistence.snapshot_repository_impl import SnapshotRepositoryImpl
from src.infrastructure.persistence.market_summary_repository_impl import MarketSummaryRepositoryImpl
from src.infrastructure.persistence.daily_summary_repository_impl import DailySummaryRepositoryImpl
from src.infrastructure.persistence.trade_repository_impl import TradeRepositoryImpl
from src.infrastructure.persistence.signal_repository_impl import SignalRepositoryImpl
from src.infrastructure.persistence.market_resolution_repository_impl import MarketResolutionRepositoryImpl


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TZ = "America/El_Salvador"
# "now" used for all cleanup runs in these tests
_NOW = datetime(2026, 4, 30, 3, 0, 0, tzinfo=timezone.utc)
# Old: 10 days before now (definitely > 7-day retention)
_OLD_TS = _NOW - timedelta(days=10)
# Recent: 2 days before now (within retention window)
_RECENT_TS = _NOW - timedelta(days=2)
# Book levels placeholder (top-10 levels)
_BOOK = "[]"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """Shared in-memory SQLite engine via StaticPool so all sessions share one connection."""
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_schema(e)
    return e


@pytest.fixture
def session(engine):
    """Session wired to the shared engine; commits on exit."""
    factory = sessionmaker(bind=engine)
    s = factory()
    seed_defaults(s)
    yield s
    s.close()


@pytest.fixture
def repos(session):
    """All repository implementations sharing the same session."""
    return {
        "snap": SnapshotRepositoryImpl(session),
        "market_summary": MarketSummaryRepositoryImpl(session),
        "daily": DailySummaryRepositoryImpl(session),
        "trade": TradeRepositoryImpl(session),
        "signal": SignalRepositoryImpl(session),
        "resolution": MarketResolutionRepositoryImpl(session),
    }


def _use_case(repos: dict) -> RunDailyCleanup:
    return RunDailyCleanup(
        snap_repo=repos["snap"],
        market_summary_repo=repos["market_summary"],
        daily_repo=repos["daily"],
        trade_repo=repos["trade"],
        signal_repo=repos["signal"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_snapshot(session, market_id: str, timestamp: datetime) -> None:
    """Insert a raw snapshot row directly via the model."""
    naive_ts = timestamp.replace(tzinfo=None)
    session.add(MarketSnapshotModel(
        timestamp=naive_ts,
        market_id=market_id,
        time_to_close_sec=20,
        btc_price=50010.0,
        btc_price_source="binance",
        threshold=50000.0,
        dtt=10.0,
        yes_price=0.55,
        no_price=0.47,
        spread=0.08,
        book_depth_yes=500.0,
        book_depth_no=500.0,
        book_levels_yes=_BOOK,
        book_levels_no=_BOOK,
        potential_gain_yes=0.80,
        potential_gain_no=0.80,
        strategy_params_id=1,
    ))
    session.flush()


def _insert_signal(session, market_id: str, timestamp: datetime) -> int:
    """Insert a PAPER_TRADE signal and return its id."""
    naive_ts = timestamp.replace(tzinfo=None)
    model = SignalEventModel(
        timestamp=naive_ts,
        market_id=market_id,
        side="YES",
        yes_price=0.55,
        no_price=0.47,
        btc_price=50010.0,
        btc_price_source="binance",
        dtt=10.0,
        time_to_close_sec=20,
        potential_gain=0.80,
        action_taken="PAPER_TRADE",
        skip_reason=None,
        strategy_params_id=1,
    )
    session.add(model)
    session.flush()
    return model.id  # type: ignore[return-value]


def _insert_trade(session, market_id: str, signal_id: int, opened_at: datetime, pnl_usd: float) -> None:
    """Insert a resolved PAPER trade directly via the model."""
    naive_opened = opened_at.replace(tzinfo=None)
    naive_resolved = (opened_at + timedelta(seconds=300)).replace(tzinfo=None)
    session.add(TradeModel(
        signal_id=signal_id,
        market_id=market_id,
        side="YES",
        entry_price=0.55,
        entry_btc_price=50010.0,
        entry_dtt=10.0,
        entry_time_to_close=20,
        position_size_usd=10.0,
        status="RESOLVED",
        exit_price=1.0,
        resolved_at=naive_resolved,
        pnl_usd=pnl_usd,
        pnl_pct=(pnl_usd / 10.0) * 100,
        mode="PAPER",
        opened_at=naive_opened,
    ))
    session.flush()


# ---------------------------------------------------------------------------
# Tests: basic archival behavior
# ---------------------------------------------------------------------------

class TestCleanupArchival:
    def test_archives_only_markets_older_than_retention(self, session, repos) -> None:
        _insert_snapshot(session, "old-market", _OLD_TS)
        _insert_snapshot(session, "recent-market", _RECENT_TS)

        result = _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        summaries = session.query(MarketSummaryModel).all()
        archived_ids = {s.market_id for s in summaries}
        assert "old-market" in archived_ids
        assert "recent-market" not in archived_ids
        assert result["markets_processed"] == 1

    def test_raw_snapshots_deleted_for_archived_market(self, session, repos) -> None:
        _insert_snapshot(session, "old-market", _OLD_TS)
        _insert_snapshot(session, "old-market", _OLD_TS - timedelta(seconds=1))

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        remaining = (
            session.query(MarketSnapshotModel)
            .filter_by(market_id="old-market")
            .count()
        )
        assert remaining == 0

    def test_recent_snapshots_are_preserved(self, session, repos) -> None:
        _insert_snapshot(session, "recent-market", _RECENT_TS)

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        remaining = (
            session.query(MarketSnapshotModel)
            .filter_by(market_id="recent-market")
            .count()
        )
        assert remaining == 1

    def test_market_summary_contains_correct_aggregates(self, session, repos) -> None:
        for i in range(3):
            _insert_snapshot(session, "old-market", _OLD_TS + timedelta(seconds=i))

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        row = session.query(MarketSummaryModel).filter_by(market_id="old-market").first()
        assert row is not None
        assert row.snapshots_count == 3
        assert abs(row.btc_price_avg - 50010.0) < 0.01
        assert abs(row.yes_price_avg - 0.55) < 0.01


# ---------------------------------------------------------------------------
# Tests: signal and trade counting
# ---------------------------------------------------------------------------

class TestCleanupSignalsAndTrades:
    def test_signal_and_trade_counts_in_market_summary(self, session, repos) -> None:
        _insert_snapshot(session, "market-a", _OLD_TS)
        sig_id = _insert_signal(session, "market-a", _OLD_TS)
        _insert_trade(session, "market-a", sig_id, _OLD_TS, pnl_usd=5.0)

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        row = session.query(MarketSummaryModel).filter_by(market_id="market-a").first()
        assert row is not None
        assert row.signals_count == 1
        assert row.signals_entered == 1
        assert row.trades_count == 1
        assert abs(row.trades_pnl_usd - 5.0) < 0.01

    def test_market_with_no_signals_or_trades(self, session, repos) -> None:
        _insert_snapshot(session, "bare-market", _OLD_TS)

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        row = session.query(MarketSummaryModel).filter_by(market_id="bare-market").first()
        assert row is not None
        assert row.signals_count == 0
        assert row.trades_count == 0
        assert row.trades_pnl_usd == 0.0


# ---------------------------------------------------------------------------
# Tests: daily summaries
# ---------------------------------------------------------------------------

class TestCleanupDailySummaries:
    def test_daily_summary_created_for_processed_date(self, session, repos) -> None:
        _insert_snapshot(session, "old-market", _OLD_TS)

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        count = session.query(DailySummaryModel).count()
        assert count >= 1

    def test_daily_summary_aggregates_pnl_correctly(self, session, repos) -> None:
        _insert_snapshot(session, "market-x", _OLD_TS)
        sig_id = _insert_signal(session, "market-x", _OLD_TS)
        _insert_trade(session, "market-x", sig_id, _OLD_TS, pnl_usd=3.0)

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        # At least one daily summary must exist with the trade PnL captured.
        rows = session.query(DailySummaryModel).all()
        total_paper_pnl = sum(r.paper_pnl_usd for r in rows)
        assert abs(total_paper_pnl - 3.0) < 0.01

    def test_no_daily_summary_when_no_old_markets(self, session, repos) -> None:
        _insert_snapshot(session, "recent-market", _RECENT_TS)

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        count = session.query(DailySummaryModel).count()
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: idempotency
# ---------------------------------------------------------------------------

class TestCleanupIdempotency:
    def test_running_twice_does_not_duplicate_market_summaries(self, session, repos) -> None:
        _insert_snapshot(session, "old-market", _OLD_TS)

        for _ in range(2):
            _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        count = session.query(MarketSummaryModel).filter_by(market_id="old-market").count()
        assert count == 1

    def test_running_twice_does_not_duplicate_daily_summaries(self, session, repos) -> None:
        _insert_snapshot(session, "old-market", _OLD_TS)

        for _ in range(2):
            _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        count = session.query(DailySummaryModel).count()
        assert count >= 1
        # Verify UNIQUE constraint: each date appears exactly once
        rows = session.query(DailySummaryModel).all()
        dates = [r.date for r in rows]
        assert len(dates) == len(set(dates))

    def test_running_three_times_processes_zero_markets_after_first(self, session, repos) -> None:
        _insert_snapshot(session, "old-market", _OLD_TS)

        first = _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)
        second = _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)
        third = _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        assert first["markets_processed"] == 1
        assert second["markets_processed"] == 0
        assert third["markets_processed"] == 0


# ---------------------------------------------------------------------------
# Tests: multiple markets and dates
# ---------------------------------------------------------------------------

class TestCleanupMultipleMarketsAndDates:
    def test_processes_multiple_old_markets_independently(self, session, repos) -> None:
        for i in range(3):
            _insert_snapshot(session, f"old-market-{i}", _OLD_TS + timedelta(minutes=i))

        result = _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        assert result["markets_processed"] == 3
        count = session.query(MarketSummaryModel).count()
        assert count == 3

    def test_mixed_old_and_recent_markets(self, session, repos) -> None:
        _insert_snapshot(session, "old-a", _OLD_TS)
        _insert_snapshot(session, "old-b", _OLD_TS - timedelta(days=1))
        _insert_snapshot(session, "recent-c", _RECENT_TS)

        result = _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        assert result["markets_processed"] == 2
        assert session.query(MarketSnapshotModel).filter_by(market_id="recent-c").count() == 1

    def test_snapshots_from_two_old_dates_create_two_daily_summaries(self, session, repos) -> None:
        # Two markets closed on different old dates
        date_a = _NOW - timedelta(days=12)  # April 18 local
        date_b = _NOW - timedelta(days=14)  # April 16 local
        _insert_snapshot(session, "market-day-a", date_a)
        _insert_snapshot(session, "market-day-b", date_b)

        _use_case(repos).execute(now_utc=_NOW, retention_days=7, tz=_TZ)

        count = session.query(DailySummaryModel).count()
        assert count == 2
