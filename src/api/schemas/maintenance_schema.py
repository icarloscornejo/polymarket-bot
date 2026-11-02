"""Pydantic schemas for maintenance endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MaintenanceStatusSchema(BaseModel):
    last_cleanup_at: datetime | None
    oldest_raw_snapshot_timestamp: datetime | None
    total_raw_snapshots: int
    total_archived_markets: int
    total_daily_summaries: int
    next_cleanup_at: datetime
