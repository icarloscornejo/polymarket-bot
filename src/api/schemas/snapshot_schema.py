"""Pydantic schemas for snapshot endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SnapshotSchema(BaseModel):
    id: int
    timestamp: datetime
    market_id: str
    time_to_close_sec: int
    btc_price: float
    btc_price_source: str
    threshold: float
    dtt: float
    yes_price: float
    no_price: float
    spread: float
    book_depth_yes: float
    book_depth_no: float
    potential_gain_yes: float
    potential_gain_no: float
    strategy_params_id: int
