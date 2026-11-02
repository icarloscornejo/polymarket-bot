from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeWindow:
    """Inclusive time window [min_sec, max_sec] in seconds."""

    min_sec: int
    max_sec: int

    def __post_init__(self) -> None:
        if self.min_sec > self.max_sec:
            raise ValueError(
                f"min_sec ({self.min_sec}) must be <= max_sec ({self.max_sec})"
            )

    def contains(self, seconds: int) -> bool:
        """Return True if seconds falls within [min_sec, max_sec]."""
        return self.min_sec <= seconds <= self.max_sec
