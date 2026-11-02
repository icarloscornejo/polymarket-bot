from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


@dataclass(frozen=True)
class Trade:
    """A paper or live trade opened from a Signal."""

    signal_id: int
    market_id: str
    side: str
    entry_price: float
    entry_btc_price: float
    entry_dtt: float
    entry_time_to_close: int
    position_size_usd: float
    status: TradeStatus
    exit_price: float | None
    resolved_at: datetime | None
    pnl_usd: float | None
    pnl_pct: float | None
    mode: TradeMode
    opened_at: datetime

    def resolve(self, exit_price: float, resolved_at: datetime) -> Trade:
        """Return a new Trade instance marked as RESOLVED with computed PnL."""
        shares = self.position_size_usd / self.entry_price
        proceeds = shares * exit_price
        pnl_usd = proceeds - self.position_size_usd
        pnl_pct = (pnl_usd / self.position_size_usd) * 100.0
        return replace(
            self,
            status=TradeStatus.RESOLVED,
            exit_price=exit_price,
            resolved_at=resolved_at,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
        )
