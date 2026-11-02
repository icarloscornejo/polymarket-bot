from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ActionTaken(str, Enum):
    SKIPPED = "SKIPPED"
    PAPER_TRADE = "PAPER_TRADE"
    LIVE_TRADE = "LIVE_TRADE"


class SkipReason(str, Enum):
    OUTSIDE_WINDOW = "OUTSIDE_WINDOW"
    DTT_BELOW_MIN = "DTT_BELOW_MIN"
    GAIN_BELOW_MIN = "GAIN_BELOW_MIN"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"


@dataclass(frozen=True)
class Signal:
    """A detected trading opportunity (entered or skipped)."""

    timestamp: datetime
    market_id: str
    side: str
    yes_price: float
    no_price: float
    btc_price: float
    btc_price_source: str
    dtt: float
    time_to_close_sec: int
    potential_gain: float
    action_taken: ActionTaken
    skip_reason: SkipReason | None
    strategy_params_id: int

    def __post_init__(self) -> None:
        if self.side not in ("YES", "NO"):
            raise ValueError(f"side must be 'YES' or 'NO', got '{self.side}'")
