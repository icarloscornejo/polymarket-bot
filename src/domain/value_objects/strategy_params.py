from __future__ import annotations

from dataclasses import dataclass

from src.domain.value_objects.time_window import TimeWindow


@dataclass(frozen=True)
class StrategyParams:
    """Immutable snapshot of all configurable strategy parameters."""

    entry_window: TimeWindow
    min_dtt: float
    min_gain_usd: float
    position_size_usd: float
    snapshot_interval_ms: int
    logging_window_buffer_sec: int

    def __post_init__(self) -> None:
        if self.min_dtt < 0.0:
            raise ValueError(f"min_dtt must be >= 0, got {self.min_dtt}")
        if self.min_gain_usd < 0.0:
            raise ValueError(f"min_gain_usd must be >= 0, got {self.min_gain_usd}")
        if self.position_size_usd <= 0.0:
            raise ValueError(f"position_size_usd must be > 0, got {self.position_size_usd}")
        if self.snapshot_interval_ms <= 0:
            raise ValueError(
                f"snapshot_interval_ms must be > 0, got {self.snapshot_interval_ms}"
            )

    @property
    def logging_window_max_sec(self) -> int:
        """Seconds before close at which snapshot logging starts."""
        return self.entry_window.max_sec + self.logging_window_buffer_sec
