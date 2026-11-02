from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DailySummary:
    """Aggregated trading metrics for a single calendar day (local TZ)."""

    date: str
    total_markets_archived: int
    total_snapshots_archived: int
    total_signals: int
    signals_entered: int
    signals_skipped: int
    paper_trades_count: int
    paper_winning_trades: int
    paper_pnl_usd: float
    paper_invested_usd: float
    live_trades_count: int
    live_winning_trades: int
    live_pnl_usd: float
    live_invested_usd: float
    cleanup_ran_at: datetime

    @property
    def paper_pnl_pct(self) -> float:
        if self.paper_invested_usd == 0.0:
            return 0.0
        return (self.paper_pnl_usd / self.paper_invested_usd) * 100.0

    @property
    def live_pnl_pct(self) -> float:
        if self.live_invested_usd == 0.0:
            return 0.0
        return (self.live_pnl_usd / self.live_invested_usd) * 100.0

    @property
    def win_rate(self) -> float:
        total = self.paper_trades_count + self.live_trades_count
        if total == 0:
            return 0.0
        return (self.paper_winning_trades + self.live_winning_trades) / total
