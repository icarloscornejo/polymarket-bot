from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.trade import Trade, TradeMode, TradeStatus


class TradeRepository(ABC):
    @abstractmethod
    def save(self, trade: Trade) -> Trade: ...

    @abstractmethod
    def update_status(self, trade: Trade) -> Trade: ...

    @abstractmethod
    def list_open(self, mode: TradeMode | None = None) -> list[Trade]: ...

    @abstractmethod
    def list_by_mode(self, mode: TradeMode) -> list[Trade]: ...

    @abstractmethod
    def list_resolved_between(self, start_utc: datetime, end_utc: datetime) -> list[Trade]: ...

    @abstractmethod
    def sum_invested_between(
        self, start_utc: datetime, end_utc: datetime, mode: TradeMode
    ) -> float: ...

    @abstractmethod
    def list_by_market(self, market_id: str) -> list[Trade]: ...
