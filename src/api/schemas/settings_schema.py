"""Pydantic schemas for settings endpoints."""
from __future__ import annotations

from datetime import datetime

import pytz
from pydantic import BaseModel, field_validator


class RuntimeSettingsSchema(BaseModel):
    timezone: str
    updated_at: datetime


class RuntimeSettingsUpdateSchema(BaseModel):
    timezone: str

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            pytz.timezone(value)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"'{value}' is not a valid IANA timezone")
        return value
