"""Pydantic schemas for strategy endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class StrategyParamsRecordSchema(BaseModel):
    id: int
    valid_from: datetime
    valid_to: datetime | None
    updated_by: str
    entry_window_min_sec: int
    entry_window_max_sec: int
    min_dtt: float
    min_gain_usd: float
    position_size_usd: float
    snapshot_interval_ms: int
    logging_window_buffer_sec: int


class StrategyParamsUpdateSchema(BaseModel):
    entry_window_min_sec: Optional[int] = None
    entry_window_max_sec: Optional[int] = None
    min_dtt: Optional[float] = None
    min_gain_usd: Optional[float] = None
    position_size_usd: Optional[float] = None
    snapshot_interval_ms: Optional[int] = None
    logging_window_buffer_sec: Optional[int] = None

    @field_validator("position_size_usd")
    @classmethod
    def validate_position_size(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value <= 0:
            raise ValueError("position_size_usd must be > 0")
        return value

    @field_validator("snapshot_interval_ms")
    @classmethod
    def validate_snapshot_interval(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value <= 0:
            raise ValueError("snapshot_interval_ms must be > 0")
        return value

    @field_validator("min_dtt")
    @classmethod
    def validate_min_dtt(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("min_dtt must be >= 0")
        return value

    @field_validator("min_gain_usd")
    @classmethod
    def validate_min_gain(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("min_gain_usd must be >= 0")
        return value
