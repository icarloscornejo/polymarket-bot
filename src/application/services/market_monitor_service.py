from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from src.application.event_bus import EventBus, TOPIC_STRATEGY_PARAMS_UPDATED
from src.domain.entities.market import Market
from src.domain.entities.signal import ActionTaken, Signal
from src.domain.repositories.signal_repository import SignalRepository
from src.domain.repositories.snapshot_repository import SnapshotRepository
from src.domain.repositories.strategy_params_repository import StrategyParamsRepository
from src.domain.repositories.trade_repository import TradeRepository
from src.domain.use_cases.evaluate_signal import EvaluateSignal, MarketState
from src.domain.use_cases.execute_trade import ExecuteTrade
from src.domain.entities.trade import TradeMode
from src.domain.value_objects.strategy_params import StrategyParams

logger = logging.getLogger(__name__)


class MarketMonitorService:
    """Monitors a single active market: snapshots, evaluates signals, executes trades."""

    def __init__(
        self,
        market: Market,
        btc_feed: Any,
        polymarket_feed: Any,
        snap_repo: SnapshotRepository,
        trade_repo: TradeRepository,
        signal_repo: SignalRepository,
        params_repo: StrategyParamsRepository,
        bus: EventBus,
        mode: str,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._market = market
        self._btc_feed = btc_feed
        self._polymarket_feed = polymarket_feed
        self._snap_repo = snap_repo
        self._trade_repo = trade_repo
        self._signal_repo = signal_repo
        self._params_repo = params_repo
        self._mode = mode
        self._now_fn = now_fn or (lambda: datetime.now(tz=timezone.utc))
        self._params: StrategyParams = params_repo.get_current()

        bus.subscribe(TOPIC_STRATEGY_PARAMS_UPDATED, self._on_params_updated)

    def _on_params_updated(self, new_params: StrategyParams) -> None:
        self._params = new_params
        logger.info("market_monitor params_refreshed market=%s", self._market.id)

    async def tick(self) -> None:
        """Execute one monitoring cycle for this market."""
        now = self._now_fn()
        params = self._params
        try:
            btc_price = self._btc_feed.latest_price()
            btc_source = self._btc_feed.source_name()
        except RuntimeError:
            logger.debug("market_monitor skipping tick, BTC feed stale market=%s", self._market.id)
            return
        time_to_close = self._market.time_to_close_sec(now)

        book_levels = await self._polymarket_feed.get_order_book(self._market.yes_token_id)
        yes_price = book_levels[0][0] if book_levels else 0.5
        no_price = 1.0 - yes_price

        book_depth_yes = sum(p * s for p, s in book_levels)
        book_depth_no = book_depth_yes  # symmetric approximation for now

        # Persist snapshot only within the logging window
        if time_to_close <= params.logging_window_max_sec:
            from src.domain.entities.snapshot import Snapshot
            snap = Snapshot.from_market_state(
                timestamp=now,
                market_id=self._market.id,
                time_to_close_sec=time_to_close,
                btc_price=btc_price,
                btc_price_source=btc_source,
                threshold=self._market.threshold,
                yes_price=yes_price,
                no_price=no_price,
                book_levels_yes=book_levels,
                book_levels_no=book_levels,
                position_size_usd=params.position_size_usd,
                strategy_params_id=1,
            )
            self._snap_repo.save(snap)

        # Evaluate entry signal
        state = MarketState(
            market=self._market,
            now=now,
            btc_price=btc_price,
            btc_price_source=btc_source,
            yes_price=yes_price,
            no_price=no_price,
            book_depth_yes=book_depth_yes,
            book_depth_no=book_depth_no,
        )
        decision = EvaluateSignal(params).execute(state)

        if decision.enter and decision.side:
            signal = Signal(
                timestamp=now,
                market_id=self._market.id,
                side=decision.side,
                yes_price=yes_price,
                no_price=no_price,
                btc_price=btc_price,
                btc_price_source=btc_source,
                dtt=abs(btc_price - self._market.threshold),
                time_to_close_sec=time_to_close,
                potential_gain=decision.potential_gain,
                action_taken=ActionTaken.PAPER_TRADE
                if self._mode == "PAPER" else ActionTaken.LIVE_TRADE,
                skip_reason=None,
                strategy_params_id=1,
            )
            trade_mode = TradeMode.PAPER if self._mode == "PAPER" else TradeMode.LIVE
            ExecuteTrade().execute(
                signal=signal,
                mode=trade_mode,
                trade_repo=self._trade_repo,
                signal_repo=self._signal_repo,
                order_executor=None,
                position_size_usd=params.position_size_usd,
            )
            logger.info(
                "market_monitor signal_entered market=%s side=%s gain=%.4f",
                self._market.id, decision.side, decision.potential_gain,
            )
