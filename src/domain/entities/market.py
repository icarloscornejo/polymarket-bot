from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Market:
    """An active BTC 5-minute prediction market on Polymarket."""

    id: str
    threshold: float
    closes_at: datetime
    yes_token_id: str
    no_token_id: str
    is_active: bool

    def time_to_close_sec(self, now: datetime) -> int:
        """Return seconds remaining until market closes, floored at 0."""
        delta = (self.closes_at - now).total_seconds()
        return max(0, int(delta))
