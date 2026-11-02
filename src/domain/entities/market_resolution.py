from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MarketResolution:
    """The final outcome of a closed BTC market."""

    market_id: str
    resolved_at: datetime
    threshold: float
    btc_price_at_close: float
    btc_price_source: str
    outcome: str
    had_position: bool

    def __post_init__(self) -> None:
        if self.outcome not in ("YES", "NO"):
            raise ValueError(f"outcome must be 'YES' or 'NO', got '{self.outcome}'")
