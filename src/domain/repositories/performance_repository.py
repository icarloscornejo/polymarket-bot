from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Aggregated metrics for an arbitrary time window."""

    period_start: datetime
    period_end: datetime
    total_signals: int
    signals_entered: int
    signals_skipped: int
    paper_pnl: float
    live_pnl: float
    win_rate: float
    avg_dtt_on_entry: float | None
    avg_time_to_close_on_entry: float | None


class PerformanceRepository(ABC):
    @abstractmethod
    def save(self, snapshot: PerformanceSnapshot) -> PerformanceSnapshot: ...

    @abstractmethod
    def latest(self) -> PerformanceSnapshot | None: ...
