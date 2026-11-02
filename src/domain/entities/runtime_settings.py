from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytz


@dataclass(frozen=True)
class RuntimeSettings:
    """Singleton runtime configuration (timezone, etc.)."""

    timezone: str
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.timezone:
            raise ValueError("timezone must not be empty")
        try:
            pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"timezone '{self.timezone}' is not a valid IANA timezone")
