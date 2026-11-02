"""Pydantic schemas for trade endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TradeSchema(BaseModel):
    id: int
    signal_id: int
    market_id: str
    side: str
    entry_price: float
    entry_btc_price: float
    entry_dtt: float
    entry_time_to_close: int
    position_size_usd: float
    status: str
    exit_price: float | None
    resolved_at: datetime | None
    pnl_usd: float | None
    pnl_pct: float | None
    mode: str
    opened_at: datetime
