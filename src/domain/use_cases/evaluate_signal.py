from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.market import Market
from src.domain.entities.signal import SkipReason
from src.domain.value_objects.strategy_params import StrategyParams


@dataclass(frozen=True)
class MarketState:
    """Live snapshot of a market and its current price feeds."""

    market: Market
    now: datetime
    btc_price: float
    btc_price_source: str
    yes_price: float
    no_price: float
    book_depth_yes: float
    book_depth_no: float


@dataclass(frozen=True)
class SignalDecision:
    """Output of EvaluateSignal: whether to enter a trade and why."""

    enter: bool
    side: str | None
    potential_gain: float
    skip_reason: SkipReason | None


class EvaluateSignal:
    """Evaluate whether current market conditions meet entry criteria."""

    def __init__(self, params: StrategyParams) -> None:
        self._params = params

    def execute(self, state: MarketState) -> SignalDecision:
        p = self._params

        time_to_close = state.market.time_to_close_sec(state.now)
        if not p.entry_window.contains(time_to_close):
            return SignalDecision(False, None, 0.0, SkipReason.OUTSIDE_WINDOW)

        dtt = abs(state.btc_price - state.market.threshold)
        if dtt < p.min_dtt:
            return SignalDecision(False, None, 0.0, SkipReason.DTT_BELOW_MIN)

        side = "YES" if state.btc_price >= state.market.threshold else "NO"
        price = state.yes_price if side == "YES" else state.no_price
        potential_gain = (
            p.position_size_usd * (1.0 - price) / price if price > 0 else 0.0
        )

        if potential_gain < p.min_gain_usd:
            return SignalDecision(False, None, 0.0, SkipReason.GAIN_BELOW_MIN)

        depth = state.book_depth_yes if side == "YES" else state.book_depth_no
        if depth < p.position_size_usd:
            return SignalDecision(False, None, 0.0, SkipReason.INSUFFICIENT_LIQUIDITY)

        return SignalDecision(True, side, potential_gain, None)
