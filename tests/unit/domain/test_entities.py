"""Tests for domain entities. One class per entity, TDD RED -> GREEN."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.entities.market import Market
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.signal import Signal, ActionTaken, SkipReason
from src.domain.entities.trade import Trade, TradeStatus, TradeMode
from src.domain.entities.monthly_performance import MonthlyPerformance
from src.domain.entities.market_summary import MarketSummary
from src.domain.entities.daily_summary import DailySummary


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------

class TestMarket:
    def _make(self, closes_at: datetime | None = None) -> Market:
        return Market(
            id="market-btc-001",
            threshold=50000.0,
            closes_at=closes_at or datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            yes_token_id="yes-token-001",
            no_token_id="no-token-001",
            is_active=True,
        )

    def test_time_to_close_sec_returns_correct_seconds_when_open(self) -> None:
        closes_at = datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc)
        now = datetime(2026, 4, 26, 12, 4, 45, tzinfo=timezone.utc)
        market = self._make(closes_at=closes_at)
        assert market.time_to_close_sec(now) == 15

    def test_time_to_close_sec_returns_zero_when_already_closed(self) -> None:
        closes_at = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
        now = datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc)
        market = self._make(closes_at=closes_at)
        assert market.time_to_close_sec(now) == 0

    def test_time_to_close_sec_returns_zero_when_exactly_at_close(self) -> None:
        closes_at = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
        market = self._make(closes_at=closes_at)
        assert market.time_to_close_sec(closes_at) == 0

    def test_time_to_close_sec_truncates_to_int(self) -> None:
        closes_at = datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc)
        now = datetime(2026, 4, 26, 12, 4, 45, 100000, tzinfo=timezone.utc)
        market = self._make(closes_at=closes_at)
        assert market.time_to_close_sec(now) == 14

    def test_market_attributes_are_set_correctly(self) -> None:
        market = self._make()
        assert market.id == "market-btc-001"
        assert market.threshold == 50000.0
        assert market.yes_token_id == "yes-token-001"
        assert market.is_active is True

    def test_is_frozen_dataclass(self) -> None:
        market = self._make()
        with pytest.raises((AttributeError, TypeError)):
            market.threshold = 99999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:
    _BOOK_LEVELS: list[tuple[float, float]] = [
        (0.52, 100.0), (0.51, 80.0), (0.50, 60.0), (0.49, 50.0), (0.48, 40.0),
        (0.47, 30.0), (0.46, 25.0), (0.45, 20.0), (0.44, 15.0), (0.43, 10.0),
    ]

    def _make(self, yes_price: float = 0.55, no_price: float = 0.47) -> Snapshot:
        return Snapshot.from_market_state(
            timestamp=datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),
            market_id="market-btc-001",
            time_to_close_sec=20,
            btc_price=50010.0,
            btc_price_source="binance",
            threshold=50000.0,
            yes_price=yes_price,
            no_price=no_price,
            book_levels_yes=self._BOOK_LEVELS,
            book_levels_no=self._BOOK_LEVELS,
            position_size_usd=10.0,
            strategy_params_id=1,
        )

    def test_factory_computes_dtt_correctly(self) -> None:
        snap = self._make()
        assert snap.dtt == pytest.approx(10.0)

    def test_factory_computes_spread_correctly(self) -> None:
        snap = self._make(yes_price=0.55, no_price=0.47)
        assert snap.spread == pytest.approx(0.55 + 0.47 - 1.0)

    def test_spread_is_negative_when_prices_sum_below_one(self) -> None:
        snap = self._make(yes_price=0.48, no_price=0.48)
        assert snap.spread == pytest.approx(-0.04)

    def test_factory_computes_book_depth_as_sum_of_levels(self) -> None:
        snap = self._make()
        expected_depth = sum(price * size for price, size in self._BOOK_LEVELS)
        assert snap.book_depth_yes == pytest.approx(expected_depth)

    def test_factory_computes_potential_gain_yes(self) -> None:
        snap = self._make(yes_price=0.4)
        expected = 10.0 * (1.0 - 0.4) / 0.4
        assert snap.potential_gain_yes == pytest.approx(expected)

    def test_factory_computes_potential_gain_no(self) -> None:
        snap = self._make(no_price=0.5)
        expected = 10.0 * (1.0 - 0.5) / 0.5
        assert snap.potential_gain_no == pytest.approx(expected)

    def test_potential_gain_yes_is_zero_when_yes_price_is_zero(self) -> None:
        snap = self._make(yes_price=0.0)
        assert snap.potential_gain_yes == pytest.approx(0.0)

    def test_potential_gain_no_is_zero_when_no_price_is_zero(self) -> None:
        snap = self._make(no_price=0.0)
        assert snap.potential_gain_no == pytest.approx(0.0)

    def test_factory_stores_book_levels_with_10_entries(self) -> None:
        snap = self._make()
        assert len(snap.book_levels_yes) == 10
        assert len(snap.book_levels_no) == 10

    def test_from_market_state_with_fewer_than_10_levels_stores_all(self) -> None:
        five_levels = [(0.5, 100.0)] * 5
        snap = Snapshot.from_market_state(
            timestamp=datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),
            market_id="m1", time_to_close_sec=20,
            btc_price=50010.0, btc_price_source="binance",
            threshold=50000.0, yes_price=0.55, no_price=0.47,
            book_levels_yes=five_levels, book_levels_no=five_levels,
            position_size_usd=10.0, strategy_params_id=1,
        )
        assert len(snap.book_levels_yes) == 5

    def test_dtt_is_zero_when_btc_equals_threshold(self) -> None:
        snap = Snapshot.from_market_state(
            timestamp=datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),
            market_id="m1", time_to_close_sec=20,
            btc_price=50000.0, btc_price_source="binance",
            threshold=50000.0, yes_price=0.5, no_price=0.5,
            book_levels_yes=self._BOOK_LEVELS, book_levels_no=self._BOOK_LEVELS,
            position_size_usd=10.0, strategy_params_id=1,
        )
        assert snap.dtt == pytest.approx(0.0)

    def test_factory_stores_btc_price_source(self) -> None:
        snap = self._make()
        assert snap.btc_price_source == "binance"

    def test_is_frozen_dataclass(self) -> None:
        snap = self._make()
        with pytest.raises((AttributeError, TypeError)):
            snap.btc_price = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

class TestSignal:
    def _make(self, **overrides: object) -> Signal:
        defaults: dict = {
            "timestamp": datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),
            "market_id": "market-btc-001",
            "side": "YES",
            "yes_price": 0.55,
            "no_price": 0.47,
            "btc_price": 50010.0,
            "btc_price_source": "binance",
            "dtt": 10.0,
            "time_to_close_sec": 20,
            "potential_gain": 0.82,
            "action_taken": ActionTaken.PAPER_TRADE,
            "skip_reason": None,
            "strategy_params_id": 1,
        }
        defaults.update(overrides)
        return Signal(**defaults)

    def test_action_taken_enum_has_three_values(self) -> None:
        assert set(ActionTaken) == {
            ActionTaken.SKIPPED, ActionTaken.PAPER_TRADE, ActionTaken.LIVE_TRADE,
        }

    def test_skip_reason_enum_has_four_values(self) -> None:
        assert set(SkipReason) == {
            SkipReason.OUTSIDE_WINDOW, SkipReason.DTT_BELOW_MIN,
            SkipReason.GAIN_BELOW_MIN, SkipReason.INSUFFICIENT_LIQUIDITY,
        }

    def test_creates_paper_trade_signal(self) -> None:
        sig = self._make()
        assert sig.action_taken == ActionTaken.PAPER_TRADE
        assert sig.skip_reason is None

    def test_creates_skipped_signal_with_reason(self) -> None:
        sig = self._make(action_taken=ActionTaken.SKIPPED, skip_reason=SkipReason.DTT_BELOW_MIN)
        assert sig.action_taken == ActionTaken.SKIPPED
        assert sig.skip_reason == SkipReason.DTT_BELOW_MIN

    def test_side_must_be_yes_or_no(self) -> None:
        with pytest.raises(ValueError, match="side"):
            self._make(side="MAYBE")

    def test_yes_side_is_valid(self) -> None:
        assert self._make(side="YES").side == "YES"

    def test_no_side_is_valid(self) -> None:
        assert self._make(side="NO").side == "NO"

    def test_skipped_with_no_reason_is_allowed(self) -> None:
        sig = self._make(action_taken=ActionTaken.SKIPPED, skip_reason=None)
        assert sig.action_taken == ActionTaken.SKIPPED

    def test_is_frozen_dataclass(self) -> None:
        sig = self._make()
        with pytest.raises((AttributeError, TypeError)):
            sig.side = "NO"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

class TestTrade:
    def _open_trade(self, side: str = "YES", entry_price: float = 0.4) -> Trade:
        return Trade(
            signal_id=1, market_id="market-btc-001",
            side=side, entry_price=entry_price,
            entry_btc_price=50010.0, entry_dtt=10.0, entry_time_to_close=20,
            position_size_usd=10.0, status=TradeStatus.OPEN,
            exit_price=None, resolved_at=None, pnl_usd=None, pnl_pct=None,
            mode=TradeMode.PAPER,
            opened_at=datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),
        )

    def test_trade_status_has_open_and_resolved(self) -> None:
        assert set(TradeStatus) == {TradeStatus.OPEN, TradeStatus.RESOLVED}

    def test_trade_mode_has_paper_and_live(self) -> None:
        assert set(TradeMode) == {TradeMode.PAPER, TradeMode.LIVE}

    def test_creates_open_trade(self) -> None:
        trade = self._open_trade()
        assert trade.status == TradeStatus.OPEN
        assert trade.pnl_usd is None

    def test_pnl_is_positive_when_yes_wins(self) -> None:
        resolved = self._open_trade(side="YES", entry_price=0.4).resolve(
            exit_price=1.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
        )
        assert resolved.pnl_usd == pytest.approx(15.0)
        assert resolved.pnl_pct == pytest.approx(150.0)

    def test_pnl_is_negative_when_yes_loses(self) -> None:
        resolved = self._open_trade(side="YES", entry_price=0.4).resolve(
            exit_price=0.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
        )
        assert resolved.pnl_usd == pytest.approx(-10.0)
        assert resolved.pnl_pct == pytest.approx(-100.0)

    def test_resolve_sets_status_to_resolved(self) -> None:
        resolved = self._open_trade().resolve(
            exit_price=1.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
        )
        assert resolved.status == TradeStatus.RESOLVED

    def test_resolve_returns_new_instance_original_unchanged(self) -> None:
        trade = self._open_trade()
        resolved = trade.resolve(
            exit_price=1.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
        )
        assert trade.status == TradeStatus.OPEN
        assert resolved.status == TradeStatus.RESOLVED

    def test_pnl_correct_for_no_side_winning(self) -> None:
        resolved = self._open_trade(side="NO", entry_price=0.5).resolve(
            exit_price=1.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
        )
        assert resolved.pnl_usd == pytest.approx(10.0)
        assert resolved.pnl_pct == pytest.approx(100.0)

    def test_resolve_raises_when_entry_price_is_zero(self) -> None:
        with pytest.raises((ValueError, ZeroDivisionError)):
            self._open_trade(entry_price=0.0).resolve(
                exit_price=1.0,
                resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            )

    def test_resolve_stores_exit_price_and_resolved_at(self) -> None:
        resolved_at = datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc)
        resolved = self._open_trade().resolve(exit_price=1.0, resolved_at=resolved_at)
        assert resolved.exit_price == pytest.approx(1.0)
        assert resolved.resolved_at == resolved_at

    def test_is_frozen_dataclass(self) -> None:
        with pytest.raises((AttributeError, TypeError)):
            self._open_trade().status = TradeStatus.RESOLVED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MonthlyPerformance
# ---------------------------------------------------------------------------

class TestMonthlyPerformance:
    def _make(self, **overrides: object) -> MonthlyPerformance:
        defaults: dict = {
            "year": 2026, "month": 4, "timezone": "America/El_Salvador",
            "pnl_usd_paper": 50.0, "pnl_usd_live": 0.0,
            "total_invested_usd_paper": 200.0, "total_invested_usd_live": 0.0,
            "total_trades": 4, "winning_trades": 3,
        }
        defaults.update(overrides)
        return MonthlyPerformance(**defaults)

    def test_pnl_pct_computed_with_d12_formula(self) -> None:
        mp = self._make()
        assert mp.pnl_pct_paper == pytest.approx(25.0)

    def test_pnl_pct_live_zero_when_no_live_investment(self) -> None:
        assert self._make().pnl_pct_live == pytest.approx(0.0)

    def test_pnl_pct_paper_zero_when_no_investment(self) -> None:
        mp = self._make(pnl_usd_paper=0.0, total_invested_usd_paper=0.0)
        assert mp.pnl_pct_paper == pytest.approx(0.0)

    def test_live_pnl_pct_computed_when_invested(self) -> None:
        mp = self._make(pnl_usd_live=20.0, total_invested_usd_live=100.0)
        assert mp.pnl_pct_live == pytest.approx(20.0)

    def test_negative_pnl_yields_negative_pct(self) -> None:
        mp = self._make(pnl_usd_paper=-30.0, total_invested_usd_paper=100.0)
        assert mp.pnl_pct_paper == pytest.approx(-30.0)

    def test_win_rate_computed_correctly(self) -> None:
        assert self._make().win_rate == pytest.approx(0.75)

    def test_win_rate_is_zero_when_no_trades(self) -> None:
        mp = self._make(total_trades=0, winning_trades=0)
        assert mp.win_rate == pytest.approx(0.0)

    def test_is_frozen_dataclass(self) -> None:
        with pytest.raises((AttributeError, TypeError)):
            self._make().pnl_usd_paper = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MarketSummary
# ---------------------------------------------------------------------------

class TestMarketSummary:
    _BASE_SNAP: dict = {
        "btc_price": 50000.0, "btc_price_source": "binance", "dtt": 10.0,
        "yes_price": 0.55, "no_price": 0.47, "spread": 0.02,
        "book_depth_yes": 500.0, "book_depth_no": 500.0,
    }

    def _make(self, snapshots: list[dict] | None = None, **overrides: object) -> MarketSummary:
        snaps = snapshots if snapshots is not None else [
            self._BASE_SNAP,
            {**self._BASE_SNAP, "btc_price": 50020.0, "dtt": 20.0},
        ]
        defaults: dict = {
            "market_id": "m1",
            "archived_at": datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc),
            "closes_at": datetime(2026, 4, 19, 12, 5, 0, tzinfo=timezone.utc),
            "threshold": 50000.0, "outcome": "YES",
            "snapshots": snaps,
            "signals_count": 2, "signals_entered": 1,
            "trades_count": 1, "trades_pnl_usd": 5.0,
        }
        defaults.update(overrides)
        return MarketSummary.from_raw(**defaults)  # type: ignore[arg-type]

    def test_computes_btc_avg_min_max(self) -> None:
        summary = self._make()
        assert summary.btc_price_avg == pytest.approx(50010.0)
        assert summary.btc_price_min == pytest.approx(50000.0)
        assert summary.btc_price_max == pytest.approx(50020.0)

    def test_snapshots_count_correct(self) -> None:
        assert self._make().snapshots_count == 2

    def test_single_snapshot_min_max_avg_all_equal(self) -> None:
        summary = self._make(snapshots=[self._BASE_SNAP], outcome=None)
        assert summary.btc_price_min == summary.btc_price_max == summary.btc_price_avg

    def test_stores_last_snapshot_as_btc_at_close(self) -> None:
        assert self._make().btc_price_at_close == pytest.approx(50020.0)

    def test_outcome_can_be_none(self) -> None:
        assert self._make(outcome=None).outcome is None

    def test_raises_when_snapshots_empty(self) -> None:
        with pytest.raises(ValueError, match="snapshots"):
            self._make(snapshots=[])


# ---------------------------------------------------------------------------
# DailySummary
# ---------------------------------------------------------------------------

class TestDailySummary:
    def _make(self, **overrides: object) -> DailySummary:
        defaults: dict = {
            "date": "2026-04-19",
            "total_markets_archived": 5, "total_snapshots_archived": 175,
            "total_signals": 10, "signals_entered": 3, "signals_skipped": 7,
            "paper_trades_count": 4, "paper_winning_trades": 3,
            "paper_pnl_usd": 15.0, "paper_invested_usd": 30.0,
            "live_trades_count": 0, "live_winning_trades": 0,
            "live_pnl_usd": 0.0, "live_invested_usd": 0.0,
            "cleanup_ran_at": datetime(2026, 4, 26, 9, 0, 0, tzinfo=timezone.utc),
        }
        defaults.update(overrides)
        return DailySummary(**defaults)

    def test_paper_pnl_pct_uses_d12_formula(self) -> None:
        assert self._make().paper_pnl_pct == pytest.approx(50.0)

    def test_paper_pnl_pct_zero_when_no_investment(self) -> None:
        ds = self._make(paper_pnl_usd=0.0, paper_invested_usd=0.0)
        assert ds.paper_pnl_pct == pytest.approx(0.0)

    def test_live_pnl_pct_when_invested(self) -> None:
        ds = self._make(live_pnl_usd=-10.0, live_invested_usd=10.0)
        assert ds.live_pnl_pct == pytest.approx(-100.0)

    def test_live_pnl_pct_zero_when_no_investment(self) -> None:
        assert self._make().live_pnl_pct == pytest.approx(0.0)

    def test_win_rate_from_paper_only(self) -> None:
        assert self._make().win_rate == pytest.approx(0.75)

    def test_win_rate_includes_live_trades(self) -> None:
        ds = self._make(
            paper_trades_count=2, paper_winning_trades=1,
            live_trades_count=2, live_winning_trades=2,
        )
        assert ds.win_rate == pytest.approx(0.75)

    def test_win_rate_zero_when_no_trades(self) -> None:
        ds = self._make(
            paper_trades_count=0, paper_winning_trades=0,
            paper_pnl_usd=0.0, paper_invested_usd=0.0,
        )
        assert ds.win_rate == pytest.approx(0.0)

    def test_is_frozen_dataclass(self) -> None:
        with pytest.raises((AttributeError, TypeError)):
            self._make().paper_pnl_usd = 999.0  # type: ignore[misc]


from src.domain.entities.market_resolution import MarketResolution
from src.domain.entities.runtime_settings import RuntimeSettings


# ---------------------------------------------------------------------------
# MarketResolution
# ---------------------------------------------------------------------------

class TestMarketResolution:
    def _make(self, **overrides: object) -> MarketResolution:
        defaults: dict = {
            "market_id": "market-btc-001",
            "resolved_at": datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            "threshold": 50000.0,
            "btc_price_at_close": 50010.0,
            "btc_price_source": "binance",
            "outcome": "YES",
            "had_position": True,
        }
        defaults.update(overrides)
        return MarketResolution(**defaults)

    def test_creates_with_valid_data(self) -> None:
        mr = self._make()
        assert mr.market_id == "market-btc-001"
        assert mr.outcome == "YES"
        assert mr.had_position is True

    def test_outcome_must_be_yes_or_no(self) -> None:
        with pytest.raises(ValueError, match="outcome"):
            self._make(outcome="MAYBE")

    def test_yes_outcome_is_valid(self) -> None:
        assert self._make(outcome="YES").outcome == "YES"

    def test_no_outcome_is_valid(self) -> None:
        assert self._make(outcome="NO").outcome == "NO"

    def test_had_position_false_is_valid(self) -> None:
        mr = self._make(had_position=False)
        assert mr.had_position is False

    def test_is_frozen_dataclass(self) -> None:
        with pytest.raises((AttributeError, TypeError)):
            self._make().outcome = "NO"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RuntimeSettings
# ---------------------------------------------------------------------------

class TestRuntimeSettings:
    def test_creates_with_valid_timezone(self) -> None:
        rs = RuntimeSettings(
            timezone="America/El_Salvador",
            updated_at=datetime(2026, 4, 26, 0, 0, 0, tzinfo=timezone.utc),
        )
        assert rs.timezone == "America/El_Salvador"

    def test_raises_when_timezone_is_empty(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            RuntimeSettings(
                timezone="",
                updated_at=datetime(2026, 4, 26, 0, 0, 0, tzinfo=timezone.utc),
            )

    def test_raises_when_timezone_is_invalid(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            RuntimeSettings(
                timezone="Not/AReal/Timezone",
                updated_at=datetime(2026, 4, 26, 0, 0, 0, tzinfo=timezone.utc),
            )

    def test_utc_timezone_is_valid(self) -> None:
        rs = RuntimeSettings(
            timezone="UTC",
            updated_at=datetime(2026, 4, 26, 0, 0, 0, tzinfo=timezone.utc),
        )
        assert rs.timezone == "UTC"

    def test_is_frozen_dataclass(self) -> None:
        rs = RuntimeSettings(
            timezone="UTC",
            updated_at=datetime(2026, 4, 26, 0, 0, 0, tzinfo=timezone.utc),
        )
        with pytest.raises((AttributeError, TypeError)):
            rs.timezone = "America/Mexico_City"  # type: ignore[misc]
