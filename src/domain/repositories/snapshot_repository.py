from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.snapshot import Snapshot


class SnapshotRepository(ABC):
    @abstractmethod
    def save(self, snapshot: Snapshot) -> Snapshot: ...

    @abstractmethod
    def list_by_market(self, market_id: str, limit: int | None = None) -> list[Snapshot]: ...

    @abstractmethod
    def list_market_ids_with_snapshots_older_than(self, cutoff_utc: datetime) -> list[str]: ...

    @abstractmethod
    def delete_by_market(self, market_id: str) -> int: ...
