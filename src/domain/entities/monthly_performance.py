from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonthlyPerformance:
    """Aggregated trading performance for a single calendar month."""

    year: int
    month: int
    timezone: str
    pnl_usd_paper: float
    pnl_usd_live: float
    total_invested_usd_paper: float
    total_invested_usd_live: float
    total_trades: int
    winning_trades: int

    @property
    def pnl_pct_paper(self) -> float:
        """PnL / total invested for PAPER trades (D12 formula)."""
        if self.total_invested_usd_paper == 0.0:
            return 0.0
        return (self.pnl_usd_paper / self.total_invested_usd_paper) * 100.0

    @property
    def pnl_pct_live(self) -> float:
        """PnL / total invested for LIVE trades (D12 formula)."""
        if self.total_invested_usd_live == 0.0:
            return 0.0
        return (self.pnl_usd_live / self.total_invested_usd_live) * 100.0

    @property
    def win_rate(self) -> float:
        """Fraction of winning trades over total trades."""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
