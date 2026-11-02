from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.market_summary import MarketSummary


class MarketSummaryRepository(ABC):
    @abstractmethod
    def save(self, summary: MarketSummary) -> MarketSummary: ...

    @abstractmethod
    def get_by_market_id(self, market_id: str) -> MarketSummary | None: ...

    @abstractmethod
    def list_by_date_range(
        self, start_utc: datetime, end_utc: datetime
    ) -> list[MarketSummary]: ...
