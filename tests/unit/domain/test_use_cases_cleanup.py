"""TDD tests for BuildMarketSummary, BuildDailySummary, RunDailyCleanup."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.unit.domain.fakes import (
    FakeDailySummaryRepository,
    FakeMarketResolutionRepository,
    FakeMarketSummaryRepository,
    FakeSignalRepository,
    FakeSnapshotRepository,
    FakeTradeRepository,
)
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.trade import Trade, TradeMode, TradeStatus
from src.domain.use_cases.build_market_summary import BuildMarketSummary
from src.domain.use_cases.build_daily_summary import BuildDailySummary
from src.domain.use_cases.run_daily_cleanup import RunDailyCleanup


_BOOK = [(0.5, 100.0)] * 10


def _snap(market_id: str, timestamp: datetime) -> Snapshot:
    return Snapshot.from_market_state(
        timestamp=timestamp, market_id=market_id,
        time_to_close_sec=20, btc_price=50010.0,
        btc_price_source="binance", threshold=50000.0,
        yes_price=0.55, no_price=0.47,
        book_levels_yes=_BOOK, book_levels_no=_BOOK,
        position_size_usd=10.0, strategy_params_id=1,
    )


def _resolved_trade(market_id: str, pnl: float, resolved_at: datetime) -> Trade:
    return Trade(
        signal_id=1, market_id=market_id, side="YES",
        entry_price=0.4, entry_btc_price=50010.0,
        entry_dtt=10.0, entry_time_to_close=20,
        position_size_usd=10.0, status=TradeStatus.RESOLVED,
        exit_price=1.0, resolved_at=resolved_at,
        pnl_usd=pnl, pnl_pct=(pnl / 10.0) * 100,
        mode=TradeMode.PAPER,
        opened_at=resolved_at - timedelta(seconds=30),
    )


# ---------------------------------------------------------------------------
# BuildMarketSummary
# ---------------------------------------------------------------------------

class TestBuildMarketSummary:
    _OLD = datetime(2026, 4, 19, 12, 5, 0, tzinfo=timezone.utc)
    _NOW = datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc)

    def test_creates_summary_with_correct_aggregates(self) -> None:
        snap_repo = FakeSnapshotRepository()
        snap_repo.save(_snap("m1", self._OLD))
        snap_repo.save(_snap("m1", self._OLD))
        summary_repo = FakeMarketSummaryRepository()
        trade_repo = FakeTradeRepository()
        signal_repo = FakeSignalRepository()

        BuildMarketSummary(snap_repo, summary_repo, trade_repo, signal_repo).execute(
            market_id="m1",
            closes_at=self._OLD,
            threshold=50000.0,
            archived_at=self._NOW,
        )

        summary = summary_repo.get_by_market_id("m1")
        assert summary is not None
        assert summary.snapshots_count == 2
        assert summary.btc_price_avg == pytest.approx(50010.0)

    def test_deletes_raw_snapshots_after_summary(self) -> None:
        snap_repo = FakeSnapshotRepository()
        snap_repo.save(_snap("m1", self._OLD))
        summary_repo = FakeMarketSummaryRepository()

        BuildMarketSummary(
            snap_repo, summary_repo, FakeTradeRepository(), FakeSignalRepository()
        ).execute(market_id="m1", closes_at=self._OLD, threshold=50000.0, archived_at=self._NOW)

        assert len(snap_repo.list_by_market("m1")) == 0

    def test_idempotent_when_called_twice(self) -> None:
        snap_repo = FakeSnapshotRepository()
        snap_repo.save(_snap("m1", self._OLD))
        summary_repo = FakeMarketSummaryRepository()
        kwargs: dict = dict(
            market_id="m1", closes_at=self._OLD, threshold=50000.0, archived_at=self._NOW
        )

        BuildMarketSummary(snap_repo, summary_repo, FakeTradeRepository(), FakeSignalRepository()).execute(**kwargs)
        BuildMarketSummary(snap_repo, summary_repo, FakeTradeRepository(), FakeSignalRepository()).execute(**kwargs)

        assert len(summary_repo.saved) == 1

    def test_handles_market_with_zero_trades(self) -> None:
        snap_repo = FakeSnapshotRepository()
        snap_repo.save(_snap("m1", self._OLD))
        summary_repo = FakeMarketSummaryRepository()

        BuildMarketSummary(
            snap_repo, summary_repo, FakeTradeRepository(), FakeSignalRepository()
        ).execute(market_id="m1", closes_at=self._OLD, threshold=50000.0, archived_at=self._NOW)

        assert summary_repo.get_by_market_id("m1").trades_count == 0

    def test_counts_signals_and_trades(self) -> None:
        snap_repo = FakeSnapshotRepository()
        snap_repo.save(_snap("m1", self._OLD))
        summary_repo = FakeMarketSummaryRepository()
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(_resolved_trade("m1", pnl=5.0, resolved_at=self._OLD))
        signal_repo = FakeSignalRepository()

        BuildMarketSummary(snap_repo, summary_repo, trade_repo, signal_repo).execute(
            market_id="m1", closes_at=self._OLD, threshold=50000.0, archived_at=self._NOW
        )

        assert summary_repo.get_by_market_id("m1").trades_count == 1


# ---------------------------------------------------------------------------
# BuildDailySummary
# ---------------------------------------------------------------------------

class TestBuildDailySummary:
    _DATE = "2026-04-19"
    _NOW = datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc)
    _RESOLVED_AT = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)

    def test_creates_daily_summary_with_pnl(self) -> None:
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(_resolved_trade("m1", pnl=10.0, resolved_at=self._RESOLVED_AT))
        trade_repo.saved.append(_resolved_trade("m2", pnl=-5.0, resolved_at=self._RESOLVED_AT))
        market_summary_repo = FakeMarketSummaryRepository()
        daily_repo = FakeDailySummaryRepository()

        BuildDailySummary(trade_repo, market_summary_repo, daily_repo, FakeSignalRepository()).execute(
            date=self._DATE, tz="America/El_Salvador", archived_at=self._NOW
        )

        ds = daily_repo.get_by_date(self._DATE)
        assert ds is not None
        assert ds.paper_pnl_usd == pytest.approx(5.0)
        assert ds.paper_invested_usd == pytest.approx(20.0)

    def test_pnl_pct_uses_d12_formula(self) -> None:
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(_resolved_trade("m1", pnl=5.0, resolved_at=self._RESOLVED_AT))

        daily_repo = FakeDailySummaryRepository()
        BuildDailySummary(
            trade_repo, FakeMarketSummaryRepository(), daily_repo, FakeSignalRepository()
        ).execute(date=self._DATE, tz="America/El_Salvador", archived_at=self._NOW)

        ds = daily_repo.get_by_date(self._DATE)
        assert ds.paper_pnl_pct == pytest.approx(50.0)  # 5/10 * 100

    def test_zero_when_no_activity(self) -> None:
        daily_repo = FakeDailySummaryRepository()
        BuildDailySummary(
            FakeTradeRepository(), FakeMarketSummaryRepository(), daily_repo, FakeSignalRepository()
        ).execute(date=self._DATE, tz="America/El_Salvador", archived_at=self._NOW)

        ds = daily_repo.get_by_date(self._DATE)
        assert ds.paper_pnl_usd == pytest.approx(0.0)
        assert ds.total_signals == 0

    def test_idempotent_when_called_twice(self) -> None:
        daily_repo = FakeDailySummaryRepository()
        kwargs: dict = dict(date=self._DATE, tz="America/El_Salvador", archived_at=self._NOW)

        BuildDailySummary(
            FakeTradeRepository(), FakeMarketSummaryRepository(), daily_repo, FakeSignalRepository()
        ).execute(**kwargs)
        BuildDailySummary(
            FakeTradeRepository(), FakeMarketSummaryRepository(), daily_repo, FakeSignalRepository()
        ).execute(**kwargs)

        assert len(daily_repo.saved) == 1


# ---------------------------------------------------------------------------
# RunDailyCleanup
# ---------------------------------------------------------------------------

class TestRunDailyCleanup:
    # _OLD must be > 7 days before _NOW for cutoff = _NOW - 7d to catch it.
    # cutoff = 2026-04-26 03:00 - 7d = 2026-04-19 03:00. Use April 18 to be safe.
    _OLD = datetime(2026, 4, 18, 12, 5, 0, tzinfo=timezone.utc)
    _RECENT = datetime(2026, 4, 25, 12, 5, 0, tzinfo=timezone.utc)
    _NOW = datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc)

    def _repos(self):
        snap_repo = FakeSnapshotRepository()
        snap_repo.save(_snap("old-market", self._OLD))
        snap_repo.save(_snap("recent-market", self._RECENT))
        return (
            snap_repo, FakeMarketSummaryRepository(),
            FakeDailySummaryRepository(), FakeTradeRepository(),
            FakeSignalRepository(), FakeMarketResolutionRepository(),
        )

    def test_processes_only_markets_older_than_retention(self) -> None:
        snap_repo, summary_repo, daily_repo, trade_repo, signal_repo, _ = self._repos()

        RunDailyCleanup(snap_repo, summary_repo, daily_repo, trade_repo, signal_repo).execute(
            now_utc=self._NOW, retention_days=7, tz="America/El_Salvador"
        )

        assert summary_repo.get_by_market_id("old-market") is not None
        assert summary_repo.get_by_market_id("recent-market") is None

    def test_skips_already_archived_markets(self) -> None:
        snap_repo, summary_repo, daily_repo, trade_repo, signal_repo, _ = self._repos()

        RunDailyCleanup(snap_repo, summary_repo, daily_repo, trade_repo, signal_repo).execute(
            now_utc=self._NOW, retention_days=7, tz="America/El_Salvador"
        )
        RunDailyCleanup(snap_repo, summary_repo, daily_repo, trade_repo, signal_repo).execute(
            now_utc=self._NOW, retention_days=7, tz="America/El_Salvador"
        )

        assert len(summary_repo.saved) == 1

    def test_raw_snapshots_deleted_for_processed_markets(self) -> None:
        snap_repo, summary_repo, daily_repo, trade_repo, signal_repo, _ = self._repos()

        RunDailyCleanup(snap_repo, summary_repo, daily_repo, trade_repo, signal_repo).execute(
            now_utc=self._NOW, retention_days=7, tz="America/El_Salvador"
        )

        assert snap_repo.list_by_market("old-market") == []
        assert len(snap_repo.list_by_market("recent-market")) == 1

    def test_creates_daily_summary_for_processed_date(self) -> None:
        snap_repo, summary_repo, daily_repo, trade_repo, signal_repo, _ = self._repos()

        RunDailyCleanup(snap_repo, summary_repo, daily_repo, trade_repo, signal_repo).execute(
            now_utc=self._NOW, retention_days=7, tz="America/El_Salvador"
        )

        assert len(daily_repo.saved) >= 1

    def test_idempotent_full_run(self) -> None:
        snap_repo, summary_repo, daily_repo, trade_repo, signal_repo, _ = self._repos()

        for _ in range(3):
            RunDailyCleanup(snap_repo, summary_repo, daily_repo, trade_repo, signal_repo).execute(
                now_utc=self._NOW, retention_days=7, tz="America/El_Salvador"
            )

        assert len(summary_repo.saved) == 1
        assert len(daily_repo.saved) >= 1

    def test_returns_none_when_market_has_no_snapshots(self) -> None:
        result = BuildMarketSummary(
            FakeSnapshotRepository(), FakeMarketSummaryRepository(),
            FakeTradeRepository(), FakeSignalRepository(),
        ).execute(
            market_id="ghost-market",
            closes_at=datetime(2026, 4, 19, 12, 5, 0, tzinfo=timezone.utc),
            threshold=50000.0,
            archived_at=datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc),
        )
        assert result is None

    def test_skips_market_already_in_summary_repo(self) -> None:
        """Line 41: market in snap_repo but already archived -> continue."""
        _OLD = datetime(2026, 4, 18, 12, 5, 0, tzinfo=timezone.utc)
        _NOW = datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc)

        snap_repo = FakeSnapshotRepository()
        snap_repo.save(_snap("pre-archived", _OLD))

        summary_repo = FakeMarketSummaryRepository()
        # Pre-populate summary for the market so it is "already archived"
        pre_summary = FakeMarketSummaryRepository()
        pre_summary.save(
            __import__(
                "src.domain.entities.market_summary", fromlist=["MarketSummary"]
            ).MarketSummary.from_raw(
                market_id="pre-archived",
                archived_at=_NOW,
                closes_at=_OLD,
                threshold=50000.0,
                outcome=None,
                snapshots=[{
                    "btc_price": 50010.0, "btc_price_source": "binance", "dtt": 10.0,
                    "yes_price": 0.55, "no_price": 0.47, "spread": 0.02,
                    "book_depth_yes": 500.0, "book_depth_no": 500.0,
                }],
                signals_count=0, signals_entered=0,
                trades_count=0, trades_pnl_usd=0.0,
            )
        )

        result = RunDailyCleanup(
            snap_repo, pre_summary, FakeDailySummaryRepository(),
            FakeTradeRepository(), FakeSignalRepository(),
        ).execute(now_utc=_NOW, retention_days=7, tz="America/El_Salvador")

        assert result["markets_processed"] == 0  # skipped because already in summary_repo

    def test_skips_market_with_no_snapshots_in_repo(self) -> None:
        """Line 46: market reported as old by list_market_ids but has no snapshots."""
        _NOW = datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc)

        class InconsistentSnapshotRepo(FakeSnapshotRepository):
            def list_market_ids_with_snapshots_older_than(self, cutoff_utc):
                return ["ghost"]  # reports ghost market as old

            def list_by_market(self, market_id, limit=None):
                return []  # but ghost has no snapshots

        result = RunDailyCleanup(
            InconsistentSnapshotRepo(), FakeMarketSummaryRepository(),
            FakeDailySummaryRepository(), FakeTradeRepository(), FakeSignalRepository(),
        ).execute(now_utc=_NOW, retention_days=7, tz="America/El_Salvador")

        assert result["markets_processed"] == 0
