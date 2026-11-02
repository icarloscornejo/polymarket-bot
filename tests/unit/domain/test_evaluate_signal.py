"""TDD tests for EvaluateSignal use case. Tests written before implementation."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.entities.market import Market
from src.domain.entities.signal import SkipReason
from src.domain.use_cases.evaluate_signal import EvaluateSignal, MarketState, SignalDecision
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow


def _params(**overrides: object) -> StrategyParams:
    defaults: dict = {
        "entry_window": TimeWindow(min_sec=5, max_sec=25),
        "min_dtt": 10.0,
        "min_gain_usd": 0.75,
        "position_size_usd": 10.0,
        "snapshot_interval_ms": 1000,
        "logging_window_buffer_sec": 10,
    }
    defaults.update(overrides)
    return StrategyParams(**defaults)


def _market(threshold: float = 50000.0) -> Market:
    return Market(
        id="m1", threshold=threshold,
        closes_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
        yes_token_id="yes-1", no_token_id="no-1", is_active=True,
    )


def _state(
    btc_price: float = 50020.0,
    now: datetime | None = None,
    yes_price: float = 0.55,
    no_price: float = 0.47,
    book_depth_yes: float = 500.0,
    book_depth_no: float = 500.0,
    threshold: float = 50000.0,
) -> MarketState:
    return MarketState(
        market=_market(threshold=threshold),
        now=now or datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),  # 20s left
        btc_price=btc_price,
        btc_price_source="binance",
        yes_price=yes_price,
        no_price=no_price,
        book_depth_yes=book_depth_yes,
        book_depth_no=book_depth_no,
    )


class TestEvaluateSignal:

    # --- Rule 1: time_to_close outside entry_window -> SKIP ---

    def test_skips_when_time_to_close_above_max(self) -> None:
        # 30s left, window max=25 -> outside
        now = datetime(2026, 4, 26, 12, 4, 30, tzinfo=timezone.utc)
        decision = EvaluateSignal(_params()).execute(_state(now=now))
        assert decision.enter is False
        assert decision.skip_reason == SkipReason.OUTSIDE_WINDOW

    def test_skips_when_time_to_close_below_min(self) -> None:
        # 3s left, window min=5 -> outside
        now = datetime(2026, 4, 26, 12, 4, 57, tzinfo=timezone.utc)
        decision = EvaluateSignal(_params()).execute(_state(now=now))
        assert decision.enter is False
        assert decision.skip_reason == SkipReason.OUTSIDE_WINDOW

    def test_enters_at_window_boundary_max(self) -> None:
        # exactly 25s left -> inside window
        now = datetime(2026, 4, 26, 12, 4, 35, tzinfo=timezone.utc)
        decision = EvaluateSignal(_params()).execute(_state(now=now))
        assert decision.skip_reason != SkipReason.OUTSIDE_WINDOW

    # --- Rule 2: dtt < min_dtt -> SKIP ---

    def test_skips_when_dtt_below_min(self) -> None:
        # btc=50005, threshold=50000 -> dtt=5 < min_dtt=10
        decision = EvaluateSignal(_params()).execute(_state(btc_price=50005.0))
        assert decision.enter is False
        assert decision.skip_reason == SkipReason.DTT_BELOW_MIN

    def test_enters_when_dtt_exactly_at_min(self) -> None:
        # btc=50010, threshold=50000 -> dtt=10 == min_dtt=10
        decision = EvaluateSignal(_params()).execute(_state(btc_price=50010.0))
        assert decision.skip_reason != SkipReason.DTT_BELOW_MIN

    # --- Rule 3+4: potential_gain < min_gain_usd -> SKIP ---

    def test_skips_when_gain_below_min(self) -> None:
        # yes_price=0.99 -> gain = 10*(1-0.99)/0.99 ≈ 0.10 < 0.75
        decision = EvaluateSignal(_params()).execute(_state(btc_price=50020.0, yes_price=0.99))
        assert decision.enter is False
        assert decision.skip_reason == SkipReason.GAIN_BELOW_MIN

    def test_potential_gain_matches_formula(self) -> None:
        # yes_price=0.4, position=10 -> gain=10*(1-0.4)/0.4=15
        decision = EvaluateSignal(_params()).execute(_state(btc_price=50020.0, yes_price=0.4))
        if decision.enter:
            assert decision.potential_gain == pytest.approx(15.0)

    # --- Rule 5: book depth insufficient -> SKIP ---

    def test_skips_when_book_depth_insufficient(self) -> None:
        # book_depth_yes=5.0 < position_size=10.0
        decision = EvaluateSignal(_params()).execute(
            _state(btc_price=50020.0, yes_price=0.4, book_depth_yes=5.0)
        )
        assert decision.enter is False
        assert decision.skip_reason == SkipReason.INSUFFICIENT_LIQUIDITY

    # --- Rule 6: all conditions met -> ENTER ---

    def test_enters_yes_when_btc_above_threshold(self) -> None:
        # btc=50020 > threshold=50000 -> implied YES
        decision = EvaluateSignal(_params()).execute(
            _state(btc_price=50020.0, yes_price=0.4, book_depth_yes=500.0)
        )
        assert decision.enter is True
        assert decision.side == "YES"
        assert decision.skip_reason is None

    def test_enters_no_when_btc_below_threshold(self) -> None:
        # btc=49980 < threshold=50000 -> implied NO
        decision = EvaluateSignal(_params()).execute(
            _state(btc_price=49980.0, no_price=0.4, book_depth_no=500.0)
        )
        assert decision.enter is True
        assert decision.side == "NO"

    def test_decision_has_no_skip_reason_when_entering(self) -> None:
        decision = EvaluateSignal(_params()).execute(
            _state(btc_price=50020.0, yes_price=0.4, book_depth_yes=500.0)
        )
        assert decision.enter is True
        assert decision.skip_reason is None

    # --- Edge cases ---

    def test_skips_when_market_already_closed(self) -> None:
        # now is after closes_at -> time_to_close=0, outside window
        now = datetime(2026, 4, 26, 12, 6, 0, tzinfo=timezone.utc)
        decision = EvaluateSignal(_params()).execute(_state(now=now))
        assert decision.skip_reason == SkipReason.OUTSIDE_WINDOW

    def test_uses_no_price_for_gain_when_btc_below_threshold(self) -> None:
        no_price = 0.4
        decision = EvaluateSignal(_params()).execute(
            _state(btc_price=49980.0, no_price=no_price, book_depth_no=500.0)
        )
        if decision.enter:
            expected = 10.0 * (1 - no_price) / no_price
            assert decision.potential_gain == pytest.approx(expected)
