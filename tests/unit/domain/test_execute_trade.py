"""TDD tests for ExecuteTrade and ResolveMarket use cases."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tests.unit.domain.fakes import (
    FakeMarketResolutionRepository,
    FakeOrderExecutor,
    FakeSignalRepository,
    FakeTradeRepository,
)
from src.domain.entities.signal import ActionTaken, Signal, SkipReason
from src.domain.entities.trade import TradeMode, TradeStatus
from src.domain.use_cases.execute_trade import ExecuteTrade
from src.domain.use_cases.resolve_market import ResolveMarket


def _signal(action_taken: ActionTaken = ActionTaken.PAPER_TRADE) -> Signal:
    return Signal(
        timestamp=datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),
        market_id="m1", side="YES",
        yes_price=0.4, no_price=0.6,
        btc_price=50020.0, btc_price_source="binance",
        dtt=20.0, time_to_close_sec=20,
        potential_gain=15.0,
        action_taken=action_taken, skip_reason=None,
        strategy_params_id=1,
    )


# ---------------------------------------------------------------------------
# ExecuteTrade
# ---------------------------------------------------------------------------

class TestExecuteTrade:

    def test_paper_mode_saves_trade_without_calling_executor(self) -> None:
        signal = _signal(ActionTaken.PAPER_TRADE)
        trade_repo = FakeTradeRepository()
        signal_repo = FakeSignalRepository()
        executor = FakeOrderExecutor()

        trade = ExecuteTrade().execute(
            signal=signal, mode=TradeMode.PAPER,
            trade_repo=trade_repo, signal_repo=signal_repo,
            order_executor=executor, position_size_usd=10.0,
        )

        assert trade.mode == TradeMode.PAPER
        assert trade.status == TradeStatus.OPEN
        assert len(trade_repo.saved) == 1
        assert len(executor.calls) == 0

    def test_paper_mode_persists_signal(self) -> None:
        signal = _signal(ActionTaken.PAPER_TRADE)
        signal_repo = FakeSignalRepository()

        ExecuteTrade().execute(
            signal=signal, mode=TradeMode.PAPER,
            trade_repo=FakeTradeRepository(), signal_repo=signal_repo,
            order_executor=FakeOrderExecutor(), position_size_usd=10.0,
        )

        assert len(signal_repo.saved) == 1

    def test_paper_trade_uses_signal_entry_price(self) -> None:
        signal = _signal(ActionTaken.PAPER_TRADE)
        trade_repo = FakeTradeRepository()

        ExecuteTrade().execute(
            signal=signal, mode=TradeMode.PAPER,
            trade_repo=trade_repo, signal_repo=FakeSignalRepository(),
            order_executor=FakeOrderExecutor(), position_size_usd=10.0,
        )

        assert trade_repo.saved[0].entry_price == pytest.approx(0.4)
        assert trade_repo.saved[0].side == "YES"

    def test_live_mode_calls_executor_then_persists(self) -> None:
        signal = _signal(ActionTaken.LIVE_TRADE)
        trade_repo = FakeTradeRepository()
        executor = FakeOrderExecutor(should_fail=False)

        trade = ExecuteTrade().execute(
            signal=signal, mode=TradeMode.LIVE,
            trade_repo=trade_repo, signal_repo=FakeSignalRepository(),
            order_executor=executor, position_size_usd=10.0,
        )

        assert len(executor.calls) == 1
        assert trade.mode == TradeMode.LIVE
        assert len(trade_repo.saved) == 1

    def test_live_mode_does_not_persist_trade_when_executor_fails(self) -> None:
        signal = _signal(ActionTaken.LIVE_TRADE)
        trade_repo = FakeTradeRepository()
        executor = FakeOrderExecutor(should_fail=True)

        with pytest.raises(RuntimeError):
            ExecuteTrade().execute(
                signal=signal, mode=TradeMode.LIVE,
                trade_repo=trade_repo, signal_repo=FakeSignalRepository(),
                order_executor=executor, position_size_usd=10.0,
            )

        assert len(trade_repo.saved) == 0

    def test_live_mode_still_persists_signal_even_when_executor_fails(self) -> None:
        signal = _signal(ActionTaken.LIVE_TRADE)
        signal_repo = FakeSignalRepository()
        executor = FakeOrderExecutor(should_fail=True)

        with pytest.raises(RuntimeError):
            ExecuteTrade().execute(
                signal=signal, mode=TradeMode.LIVE,
                trade_repo=FakeTradeRepository(), signal_repo=signal_repo,
                order_executor=executor, position_size_usd=10.0,
            )

        assert len(signal_repo.saved) == 1


# ---------------------------------------------------------------------------
# ResolveMarket
# ---------------------------------------------------------------------------

class TestResolveMarket:

    def _open_trade(
        self, side: str = "YES", entry_price: float = 0.4
    ):
        from src.domain.entities.trade import Trade
        return Trade(
            signal_id=1, market_id="m1", side=side,
            entry_price=entry_price, entry_btc_price=50020.0,
            entry_dtt=20.0, entry_time_to_close=20,
            position_size_usd=10.0, status=TradeStatus.OPEN,
            exit_price=None, resolved_at=None,
            pnl_usd=None, pnl_pct=None,
            mode=TradeMode.PAPER,
            opened_at=datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc),
        )

    def test_resolves_yes_outcome_when_btc_above_threshold(self) -> None:
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(self._open_trade(side="YES"))
        resolution_repo = FakeMarketResolutionRepository()
        resolved_at = datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc)

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=50020.0,
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=resolved_at,
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        resolution = resolution_repo.get_by_market_id("m1")
        assert resolution is not None
        assert resolution.outcome == "YES"

    def test_resolves_no_outcome_when_btc_below_threshold(self) -> None:
        trade_repo = FakeTradeRepository()
        resolution_repo = FakeMarketResolutionRepository()

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=49980.0,
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        assert resolution_repo.get_by_market_id("m1").outcome == "NO"

    def test_closes_open_trades_with_correct_pnl(self) -> None:
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(self._open_trade(side="YES", entry_price=0.4))
        resolution_repo = FakeMarketResolutionRepository()

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=50020.0,  # YES wins
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        resolved = trade_repo.saved[0]
        assert resolved.status == TradeStatus.RESOLVED
        assert resolved.pnl_usd == pytest.approx(15.0)

    def test_had_position_is_true_when_trades_existed(self) -> None:
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(self._open_trade())
        resolution_repo = FakeMarketResolutionRepository()

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=50020.0,
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        assert resolution_repo.get_by_market_id("m1").had_position is True

    def test_had_position_is_false_when_no_trades(self) -> None:
        trade_repo = FakeTradeRepository()
        resolution_repo = FakeMarketResolutionRepository()

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=50020.0,
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        assert resolution_repo.get_by_market_id("m1").had_position is False

    def test_idempotent_when_called_twice(self) -> None:
        trade_repo = FakeTradeRepository()
        resolution_repo = FakeMarketResolutionRepository()
        kwargs: dict = dict(
            market_id="m1", btc_price_at_close=50020.0,
            btc_price_source="binance", threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo, resolution_repo=resolution_repo,
        )

        ResolveMarket().execute(**kwargs)
        ResolveMarket().execute(**kwargs)

        assert len(resolution_repo.saved) == 1

    def test_closes_losing_yes_trade_when_no_outcome(self) -> None:
        """YES trade loses when BTC finishes below threshold (NO wins).
        shares = 10/0.4 = 25; exit = 0.0 -> PnL = 25*0.0 - 10 = -10.0
        """
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(self._open_trade(side="YES", entry_price=0.4))
        resolution_repo = FakeMarketResolutionRepository()

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=49900.0,  # NO wins
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        resolved = trade_repo.saved[0]
        assert resolved.status == TradeStatus.RESOLVED
        assert resolved.exit_price == pytest.approx(0.0)
        assert resolved.pnl_usd == pytest.approx(-10.0)

    def test_closes_winning_no_trade_when_no_outcome(self) -> None:
        """NO trade wins when BTC finishes below threshold (NO wins).
        shares = 10/0.47 ≈ 21.28; exit = 1.0 -> PnL = 21.28*1.0 - 10 ≈ 11.28
        """
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(self._open_trade(side="NO", entry_price=0.47))
        resolution_repo = FakeMarketResolutionRepository()

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=49900.0,  # NO wins
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        resolved = trade_repo.saved[0]
        assert resolved.status == TradeStatus.RESOLVED
        assert resolved.exit_price == pytest.approx(1.0)
        expected_pnl = (10.0 / 0.47) * 1.0 - 10.0
        assert resolved.pnl_usd == pytest.approx(expected_pnl, rel=1e-4)

    def test_closes_losing_no_trade_when_yes_outcome(self) -> None:
        """NO trade loses when BTC finishes above threshold (YES wins).
        shares = 10/0.47 ≈ 21.28; exit = 0.0 -> PnL = 21.28*0.0 - 10 = -10.0
        """
        trade_repo = FakeTradeRepository()
        trade_repo.saved.append(self._open_trade(side="NO", entry_price=0.47))
        resolution_repo = FakeMarketResolutionRepository()

        ResolveMarket().execute(
            market_id="m1",
            btc_price_at_close=50020.0,  # YES wins
            btc_price_source="binance",
            threshold=50000.0,
            resolved_at=datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc),
            trade_repo=trade_repo,
            resolution_repo=resolution_repo,
        )

        resolved = trade_repo.saved[0]
        assert resolved.status == TradeStatus.RESOLVED
        assert resolved.exit_price == pytest.approx(0.0)
        assert resolved.pnl_usd == pytest.approx(-10.0)
