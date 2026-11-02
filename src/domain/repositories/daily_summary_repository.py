from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.daily_summary import DailySummary


class DailySummaryRepository(ABC):
    @abstractmethod
    def save(self, summary: DailySummary) -> DailySummary: ...

    @abstractmethod
    def get_by_date(self, date: str) -> DailySummary | None: ...

    @abstractmethod
    def list_dates_without_summary(self, date_range: list[str]) -> list[str]: ...
