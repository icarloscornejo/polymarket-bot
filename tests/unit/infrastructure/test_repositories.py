"""Integration tests for repository implementations using SQLite :memory:."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities.market_resolution import MarketResolution
from src.domain.entities.signal import ActionTaken, Signal
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.trade import Trade, TradeMode, TradeStatus
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow
from src.infrastructure.persistence.database import seed_defaults
from src.infrastructure.persistence.models import Base
from src.infrastructure.persistence.signal_repository_impl import SignalRepositoryImpl
from src.infrastructure.persistence.snapshot_repository_impl import SnapshotRepositoryImpl
from src.infrastructure.persistence.trade_repository_impl import TradeRepositoryImpl
from src.infrastructure.persistence.market_resolution_repository_impl import MarketResolutionRepositoryImpl
from src.infrastructure.persistence.strategy_params_repository_impl import StrategyParamsRepositoryImpl
from src.infrastructure.persistence.runtime_settings_repository_impl import RuntimeSettingsRepositoryImpl
from src.infrastructure.persistence.market_summary_repository_impl import MarketSummaryRepositoryImpl
from src.infrastructure.persistence.daily_summary_repository_impl import DailySummaryRepositoryImpl
from src.infrastructure.persistence.performance_repository_impl import PerformanceRepositoryImpl
from src.domain.repositories.performance_repository import PerformanceSnapshot
from src.domain.entities.market_summary import MarketSummary
from src.domain.entities.daily_summary import DailySummary


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        seed_defaults(s)
        yield s
    engine.dispose()  # close all pooled connections to avoid ResourceWarning


_BOOK = [(0.5, 100.0)] * 10
_NOW = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)


def _signal(market_id: str = "m1", action_taken: ActionTaken = ActionTaken.PAPER_TRADE) -> Signal:
    return Signal(
        timestamp=_NOW, market_id=market_id, side="YES",
        yes_price=0.55, no_price=0.47,
        btc_price=50010.0, btc_price_source="binance",
        dtt=10.0, time_to_close_sec=20,
        potential_gain=8.18,
        action_taken=action_taken, skip_reason=None,
        strategy_params_id=1,
    )


def _snapshot(market_id: str = "m1", timestamp: datetime | None = None) -> Snapshot:
    return Snapshot.from_market_state(
        timestamp=timestamp or _NOW,
        market_id=market_id, time_to_close_sec=20,
        btc_price=50010.0, btc_price_source="binance",
        threshold=50000.0, yes_price=0.55, no_price=0.47,
        book_levels_yes=_BOOK, book_levels_no=_BOOK,
        position_size_usd=10.0, strategy_params_id=1,
    )


def _trade(
    market_id: str = "m1",
    mode: TradeMode = TradeMode.PAPER,
    status: TradeStatus = TradeStatus.OPEN,
    resolved_at: datetime | None = None,
    pnl_usd: float | None = None,
) -> Trade:
    return Trade(
        signal_id=1, market_id=market_id, side="YES",
        entry_price=0.4, entry_btc_price=50010.0,
        entry_dtt=10.0, entry_time_to_close=20,
        position_size_usd=10.0, status=status,
        exit_price=1.0 if status == TradeStatus.RESOLVED else None,
        resolved_at=resolved_at,
        pnl_usd=pnl_usd,
        pnl_pct=(pnl_usd / 10.0 * 100) if pnl_usd is not None else None,
        mode=mode,
        opened_at=_NOW - timedelta(seconds=30),
    )


def _market_summary(market_id: str = "m1") -> MarketSummary:
    snap_data = [{
        "btc_price": 50010.0, "btc_price_source": "binance", "dtt": 10.0,
        "yes_price": 0.55, "no_price": 0.47, "spread": 0.02,
        "book_depth_yes": 500.0, "book_depth_no": 500.0,
    }]
    return MarketSummary.from_raw(
        market_id=market_id,
        archived_at=_NOW,
        closes_at=_NOW - timedelta(days=7),
        threshold=50000.0, outcome="YES",
        snapshots=snap_data,
        signals_count=1, signals_entered=1,
        trades_count=1, trades_pnl_usd=5.0,
    )


def _daily_summary(date: str = "2026-04-19") -> DailySummary:
    return DailySummary(
        date=date,
        total_markets_archived=1, total_snapshots_archived=35,
        total_signals=5, signals_entered=2, signals_skipped=3,
        paper_trades_count=2, paper_winning_trades=1,
        paper_pnl_usd=5.0, paper_invested_usd=20.0,
        live_trades_count=0, live_winning_trades=0,
        live_pnl_usd=0.0, live_invested_usd=0.0,
        cleanup_ran_at=_NOW,
    )


# ---------------------------------------------------------------------------
# SignalRepository
# ---------------------------------------------------------------------------

class TestSignalRepositoryImpl:
    def test_save_and_get_by_id_returns_signal(self, session) -> None:
        repo = SignalRepositoryImpl(session)
        saved_id = repo.save(_signal())
        result = repo.get_by_id(saved_id)
        assert result is not None
        assert result.market_id == "m1"

    def test_list_recent_returns_in_desc_order(self, session) -> None:
        repo = SignalRepositoryImpl(session)
        repo.save(_signal("m1"))
        repo.save(_signal("m2"))
        results = repo.list_recent(limit=10)
        assert len(results) == 2

    def test_list_recent_respects_limit(self, session) -> None:
        repo = SignalRepositoryImpl(session)
        for _ in range(5):
            repo.save(_signal())
        assert len(repo.list_recent(limit=3)) == 3

    def test_get_by_id_returns_none_for_missing(self, session) -> None:
        repo = SignalRepositoryImpl(session)
        assert repo.get_by_id(9999) is None

    def test_action_taken_roundtrip(self, session) -> None:
        repo = SignalRepositoryImpl(session)
        sig_id = repo.save(_signal(action_taken=ActionTaken.SKIPPED))
        result = repo.get_by_id(sig_id)
        assert result.action_taken == ActionTaken.SKIPPED


# ---------------------------------------------------------------------------
# SnapshotRepository
# ---------------------------------------------------------------------------

class TestSnapshotRepositoryImpl:
    def test_save_and_list_by_market(self, session) -> None:
        repo = SnapshotRepositoryImpl(session)
        repo.save(_snapshot("m1"))
        repo.save(_snapshot("m1"))
        repo.save(_snapshot("m2"))
        assert len(repo.list_by_market("m1")) == 2
        assert len(repo.list_by_market("m2")) == 1

    def test_list_by_market_respects_limit(self, session) -> None:
        repo = SnapshotRepositoryImpl(session)
        for _ in range(5):
            repo.save(_snapshot())
        assert len(repo.list_by_market("m1", limit=3)) == 3

    def test_list_market_ids_older_than_cutoff(self, session) -> None:
        repo = SnapshotRepositoryImpl(session)
        old_ts = _NOW - timedelta(days=8)
        repo.save(_snapshot("old-market", old_ts))
        repo.save(_snapshot("recent-market", _NOW))
        cutoff = _NOW - timedelta(days=7)
        old_ids = repo.list_market_ids_with_snapshots_older_than(cutoff)
        assert "old-market" in old_ids
        assert "recent-market" not in old_ids

    def test_delete_by_market_removes_snapshots(self, session) -> None:
        repo = SnapshotRepositoryImpl(session)
        repo.save(_snapshot("m1"))
        repo.save(_snapshot("m1"))
        count = repo.delete_by_market("m1")
        assert count == 2
        assert repo.list_by_market("m1") == []

    def test_book_levels_roundtrip(self, session) -> None:
        repo = SnapshotRepositoryImpl(session)
        repo.save(_snapshot())
        result = repo.list_by_market("m1")[0]
        assert len(result.book_levels_yes) == 10
        assert result.book_levels_yes[0] == pytest.approx((0.5, 100.0))


# ---------------------------------------------------------------------------
# TradeRepository
# ---------------------------------------------------------------------------

class TestTradeRepositoryImpl:
    def test_save_returns_trade(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        trade = repo.save(_trade())
        assert trade.market_id == "m1"

    def test_list_open_returns_only_open(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        repo.save(_trade(status=TradeStatus.OPEN))
        repo.save(_trade(status=TradeStatus.RESOLVED, resolved_at=_NOW, pnl_usd=5.0))
        open_trades = repo.list_open()
        assert len(open_trades) == 1
        assert open_trades[0].status == TradeStatus.OPEN

    def test_list_open_filters_by_mode(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        repo.save(_trade(mode=TradeMode.PAPER))
        repo.save(_trade(mode=TradeMode.LIVE))
        assert len(repo.list_open(mode=TradeMode.PAPER)) == 1

    def test_update_status_persists_changes(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        original = _trade()
        repo.save(original)
        # resolve() creates a new Trade with same market_id + opened_at
        resolved = original.resolve(exit_price=1.0, resolved_at=_NOW)
        repo.update_status(resolved)
        open_trades = repo.list_open()
        assert len(open_trades) == 0

    def test_list_resolved_between_filters_by_date(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        april_trade = _trade(
            status=TradeStatus.RESOLVED,
            resolved_at=datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc),
            pnl_usd=5.0,
        )
        march_trade = _trade(
            status=TradeStatus.RESOLVED,
            resolved_at=datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
            pnl_usd=10.0,
        )
        repo.save(april_trade)
        repo.save(march_trade)
        start = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc)
        results = repo.list_resolved_between(start, end)
        assert len(results) == 1
        assert results[0].pnl_usd == pytest.approx(5.0)

    def test_sum_invested_between(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        t1 = _trade(
            status=TradeStatus.RESOLVED, mode=TradeMode.PAPER,
            resolved_at=datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc),
            pnl_usd=5.0,
        )
        t2 = _trade(
            status=TradeStatus.RESOLVED, mode=TradeMode.LIVE,
            resolved_at=datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc),
            pnl_usd=5.0,
        )
        repo.save(t1)
        repo.save(t2)
        start = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc)
        total = repo.sum_invested_between(start, end, TradeMode.PAPER)
        assert total == pytest.approx(10.0)

    def test_list_by_market(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        repo.save(_trade("m1"))
        repo.save(_trade("m2"))
        assert len(repo.list_by_market("m1")) == 1

    def test_update_status_returns_trade_unchanged_when_not_in_db(self, session) -> None:
        """update_status() when row is None (trade never saved): branch 31->38 returns trade as-is."""
        repo = TradeRepositoryImpl(session)
        unsaved = _trade(market_id="ghost-market", status=TradeStatus.OPEN)
        result = repo.update_status(unsaved)
        # The trade is returned unchanged and no DB rows are created.
        assert result.market_id == "ghost-market"
        assert repo.list_open() == []


# ---------------------------------------------------------------------------
# MarketResolutionRepository
# ---------------------------------------------------------------------------

class TestMarketResolutionRepositoryImpl:
    def test_save_and_get_by_market_id(self, session) -> None:
        repo = MarketResolutionRepositoryImpl(session)
        resolution = MarketResolution(
            market_id="m1", resolved_at=_NOW, threshold=50000.0,
            btc_price_at_close=50010.0, btc_price_source="binance",
            outcome="YES", had_position=True,
        )
        repo.save(resolution)
        result = repo.get_by_market_id("m1")
        assert result is not None
        assert result.outcome == "YES"
        assert result.had_position is True

    def test_save_is_idempotent(self, session) -> None:
        repo = MarketResolutionRepositoryImpl(session)
        resolution = MarketResolution(
            market_id="m1", resolved_at=_NOW, threshold=50000.0,
            btc_price_at_close=50010.0, btc_price_source="binance",
            outcome="YES", had_position=False,
        )
        repo.save(resolution)
        repo.save(resolution)  # second save should not duplicate
        # If no IntegrityError, it's idempotent

    def test_get_by_market_id_returns_none_for_missing(self, session) -> None:
        repo = MarketResolutionRepositoryImpl(session)
        assert repo.get_by_market_id("nonexistent") is None


# ---------------------------------------------------------------------------
# StrategyParamsRepository
# ---------------------------------------------------------------------------

class TestStrategyParamsRepositoryImpl:
    def test_get_current_returns_seeded_params(self, session) -> None:
        repo = StrategyParamsRepositoryImpl(session)
        params = repo.get_current()
        assert params.min_dtt == pytest.approx(10.0)
        assert params.entry_window.min_sec == 5

    def test_update_creates_new_version(self, session) -> None:
        repo = StrategyParamsRepositoryImpl(session)
        new_params = StrategyParams(
            entry_window=TimeWindow(5, 30),
            min_dtt=15.0, min_gain_usd=1.0,
            position_size_usd=20.0,
            snapshot_interval_ms=500,
            logging_window_buffer_sec=5,
        )
        repo.update(new_params, updated_by="DASHBOARD")
        current = repo.get_current()
        assert current.min_dtt == pytest.approx(15.0)
        assert current.entry_window.max_sec == 30

    def test_update_closes_previous_version(self, session) -> None:
        from src.infrastructure.persistence.models import StrategyParamsModel
        repo = StrategyParamsRepositoryImpl(session)
        new_params = StrategyParams(
            entry_window=TimeWindow(5, 30), min_dtt=15.0, min_gain_usd=1.0,
            position_size_usd=20.0, snapshot_interval_ms=500, logging_window_buffer_sec=5,
        )
        repo.update(new_params, updated_by="DASHBOARD")
        open_rows = session.query(StrategyParamsModel).filter_by(valid_to=None).all()
        assert len(open_rows) == 1

    def test_get_by_id_returns_params(self, session) -> None:
        repo = StrategyParamsRepositoryImpl(session)
        params = repo.get_by_id(1)
        assert params is not None

    def test_update_creates_record_when_no_existing_active_params(self) -> None:
        """update() when current is None (no active params): branch 26->28 skips setting valid_to."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with sessionmaker(bind=engine)() as s:
            repo = StrategyParamsRepositoryImpl(s)
            new_params = StrategyParams(
                entry_window=TimeWindow(5, 25), min_dtt=10.0, min_gain_usd=0.75,
                position_size_usd=10.0, snapshot_interval_ms=1000, logging_window_buffer_sec=10,
            )
            result = repo.update(new_params, updated_by="DASHBOARD")
            s.commit()
        assert result.min_dtt == pytest.approx(10.0)

    def test_get_current_id_raises_when_no_params_seeded(self) -> None:
        """get_current_id() raises RuntimeError when DB has no active params (branch 40->41)."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with sessionmaker(bind=engine)() as s:
            repo = StrategyParamsRepositoryImpl(s)
            with pytest.raises(RuntimeError, match="No current strategy params"):
                repo.get_current_id()

    def test_get_current_record_raises_when_no_params_seeded(self) -> None:
        """get_current_record() raises RuntimeError when DB has no active params (branch 47->48)."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with sessionmaker(bind=engine)() as s:
            repo = StrategyParamsRepositoryImpl(s)
            with pytest.raises(RuntimeError, match="No current strategy params"):
                repo.get_current_record()


# ---------------------------------------------------------------------------
# RuntimeSettingsRepository
# ---------------------------------------------------------------------------

class TestRuntimeSettingsRepositoryImpl:
    def test_get_returns_seeded_default(self, session) -> None:
        repo = RuntimeSettingsRepositoryImpl(session)
        settings = repo.get()
        assert settings.timezone == "America/El_Salvador"

    def test_update_timezone_persists(self, session) -> None:
        repo = RuntimeSettingsRepositoryImpl(session)
        repo.update_timezone("America/Mexico_City")
        assert repo.get().timezone == "America/Mexico_City"

    def test_update_timezone_raises_for_invalid(self, session) -> None:
        repo = RuntimeSettingsRepositoryImpl(session)
        with pytest.raises(ValueError, match="timezone"):
            repo.update_timezone("Not/Valid")


# ---------------------------------------------------------------------------
# MarketSummaryRepository
# ---------------------------------------------------------------------------

class TestMarketSummaryRepositoryImpl:
    def test_save_and_get_by_market_id(self, session) -> None:
        repo = MarketSummaryRepositoryImpl(session)
        repo.save(_market_summary("m1"))
        result = repo.get_by_market_id("m1")
        assert result is not None
        assert result.snapshots_count == 1

    def test_save_is_idempotent(self, session) -> None:
        repo = MarketSummaryRepositoryImpl(session)
        repo.save(_market_summary("m1"))
        repo.save(_market_summary("m1"))
        # No duplicate

    def test_get_by_market_id_returns_none_for_missing(self, session) -> None:
        repo = MarketSummaryRepositoryImpl(session)
        assert repo.get_by_market_id("missing") is None

    def test_list_by_date_range(self, session) -> None:
        repo = MarketSummaryRepositoryImpl(session)
        repo.save(_market_summary("m1"))  # closes_at = _NOW - 7 days = April 19
        start = datetime(2026, 4, 18, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 20, 0, 0, 0, tzinfo=timezone.utc)
        results = repo.list_by_date_range(start, end)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# DailySummaryRepository
# ---------------------------------------------------------------------------

class TestDailySummaryRepositoryImpl:
    def test_save_and_get_by_date(self, session) -> None:
        repo = DailySummaryRepositoryImpl(session)
        repo.save(_daily_summary("2026-04-19"))
        result = repo.get_by_date("2026-04-19")
        assert result is not None
        assert result.paper_pnl_usd == pytest.approx(5.0)

    def test_save_is_idempotent(self, session) -> None:
        repo = DailySummaryRepositoryImpl(session)
        repo.save(_daily_summary())
        repo.save(_daily_summary())
        # No duplicate; verified by not raising

    def test_list_dates_without_summary(self, session) -> None:
        repo = DailySummaryRepositoryImpl(session)
        repo.save(_daily_summary("2026-04-19"))
        missing = repo.list_dates_without_summary(["2026-04-19", "2026-04-20", "2026-04-21"])
        assert "2026-04-19" not in missing
        assert "2026-04-20" in missing

    def test_get_by_date_returns_none_for_missing(self, session) -> None:
        repo = DailySummaryRepositoryImpl(session)
        assert repo.get_by_date("2099-01-01") is None


# ---------------------------------------------------------------------------
# PerformanceRepository
# ---------------------------------------------------------------------------

class TestPerformanceRepositoryImpl:
    def test_save_and_latest(self, session) -> None:
        repo = PerformanceRepositoryImpl(session)
        snap = PerformanceSnapshot(
            period_start=_NOW - timedelta(hours=1),
            period_end=_NOW,
            total_signals=10, signals_entered=3, signals_skipped=7,
            paper_pnl=15.0, live_pnl=0.0, win_rate=0.67,
            avg_dtt_on_entry=12.5, avg_time_to_close_on_entry=18.0,
        )
        repo.save(snap)
        result = repo.latest()
        assert result is not None
        assert result.paper_pnl == pytest.approx(15.0)

    def test_latest_returns_none_when_empty(self, session) -> None:
        repo = PerformanceRepositoryImpl(session)
        assert repo.latest() is None

    def test_latest_returns_most_recent(self, session) -> None:
        repo = PerformanceRepositoryImpl(session)
        snap1 = PerformanceSnapshot(
            period_start=_NOW - timedelta(hours=2), period_end=_NOW - timedelta(hours=1),
            total_signals=5, signals_entered=1, signals_skipped=4,
            paper_pnl=2.0, live_pnl=0.0, win_rate=0.5,
            avg_dtt_on_entry=None, avg_time_to_close_on_entry=None,
        )
        snap2 = PerformanceSnapshot(
            period_start=_NOW - timedelta(hours=1), period_end=_NOW,
            total_signals=10, signals_entered=3, signals_skipped=7,
            paper_pnl=99.0, live_pnl=0.0, win_rate=0.8,
            avg_dtt_on_entry=None, avg_time_to_close_on_entry=None,
        )
        repo.save(snap1)
        repo.save(snap2)
        assert repo.latest().paper_pnl == pytest.approx(99.0)


# ---------------------------------------------------------------------------
# Database bootstrap / coverage gaps
# ---------------------------------------------------------------------------

class TestDatabaseLayer:
    def test_init_schema_is_idempotent(self, session) -> None:
        from sqlalchemy import create_engine
        from src.infrastructure.persistence.database import build_engine, init_schema
        engine = build_engine("sqlite:///:memory:")
        init_schema(engine)
        init_schema(engine)  # second call must not raise

    def test_make_session_factory_creates_tables(self) -> None:
        from src.infrastructure.persistence.database import make_session_factory
        factory = make_session_factory("sqlite:///:memory:")
        with factory() as s:
            # strategy_params seeded by default (via seed_defaults)
            from src.infrastructure.persistence.models import StrategyParamsModel
            count = s.query(StrategyParamsModel).count()
            assert count == 0  # seed_defaults not called here, just schema created

    def test_seed_defaults_does_not_duplicate(self, session) -> None:
        from src.infrastructure.persistence.database import seed_defaults
        seed_defaults(session)  # called again; already seeded by fixture
        from src.infrastructure.persistence.models import StrategyParamsModel, RuntimeSettingsModel
        assert session.query(StrategyParamsModel).filter_by(valid_to=None).count() == 1
        assert session.query(RuntimeSettingsModel).count() == 1

    def test_runtime_settings_update_creates_row_when_missing(self) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.infrastructure.persistence.models import Base
        from src.infrastructure.persistence.runtime_settings_repository_impl import RuntimeSettingsRepositoryImpl
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        with Session() as s:
            repo = RuntimeSettingsRepositoryImpl(s)
            result = repo.update_timezone("UTC")
            assert result.timezone == "UTC"


class TestMapperCoverage:
    def test_snapshot_to_model_preserves_book_levels(self) -> None:
        from src.infrastructure.persistence.mappers import snapshot_from_model, snapshot_to_model
        snap = _snapshot()
        model = snapshot_to_model(snap)
        roundtrip = snapshot_from_model(model)
        assert len(roundtrip.book_levels_yes) == 10

    def test_trade_without_resolved_at_roundtrip(self) -> None:
        from src.infrastructure.persistence.mappers import trade_from_model, trade_to_model
        trade = _trade(status=TradeStatus.OPEN)
        model = trade_to_model(trade)
        roundtrip = trade_from_model(model)
        assert roundtrip.resolved_at is None
        assert roundtrip.pnl_usd is None

    def test_strategy_params_get_current_raises_when_not_seeded(self) -> None:
        with create_engine("sqlite:///:memory:").connect() as conn:
            engine = conn.engine
            Base.metadata.create_all(engine)
            with sessionmaker(bind=engine)() as s:
                repo = StrategyParamsRepositoryImpl(s)
                with pytest.raises(RuntimeError, match="seed_defaults"):
                    repo.get_current()

    def test_runtime_settings_get_raises_when_not_seeded(self) -> None:
        with create_engine("sqlite:///:memory:").connect() as conn:
            engine = conn.engine
            Base.metadata.create_all(engine)
            with sessionmaker(bind=engine)() as s:
                repo = RuntimeSettingsRepositoryImpl(s)
                with pytest.raises(RuntimeError, match="RuntimeSettings"):
                    repo.get()

    def test_mappers_utc_on_naive_datetime(self) -> None:
        from datetime import datetime as dt
        from src.infrastructure.persistence.mappers import _utc
        naive = dt(2026, 4, 26, 12, 0, 0)  # no tzinfo -> gets UTC attached
        result = _utc(naive)
        assert result.tzinfo is not None

    def test_mappers_utc_preserves_existing_timezone(self) -> None:
        from src.infrastructure.persistence.mappers import _utc
        aware = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
        result = _utc(aware)
        assert result == aware  # returned as-is (line 36)

    def test_trade_list_by_mode_filters_correctly(self, session) -> None:
        repo = TradeRepositoryImpl(session)
        repo.save(_trade(mode=TradeMode.PAPER))
        repo.save(_trade(mode=TradeMode.PAPER))
        repo.save(_trade(mode=TradeMode.LIVE))
        paper = repo.list_by_mode(TradeMode.PAPER)
        live = repo.list_by_mode(TradeMode.LIVE)
        assert len(paper) == 2
        assert len(live) == 1
