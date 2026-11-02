"""Pydantic schemas for performance endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MonthlyPerformanceSchema(BaseModel):
    year: int
    month: int
    timezone: str
    pnl_usd_paper: float
    pnl_usd_live: float
    total_invested_usd_paper: float
    total_invested_usd_live: float
    total_trades: int
    winning_trades: int
    pnl_pct_paper: float
    pnl_pct_live: float
    win_rate: float


class DailySummarySchema(BaseModel):
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
    paper_pnl_pct: float
    live_trades_count: int
    live_winning_trades: int
    live_pnl_usd: float
    live_invested_usd: float
    live_pnl_pct: float
    win_rate: float
    cleanup_ran_at: datetime
