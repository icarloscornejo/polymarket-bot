"""Pydantic schemas for signal endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SignalSchema(BaseModel):
    id: int
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
    action_taken: str
    skip_reason: str | None
    strategy_params_id: int
