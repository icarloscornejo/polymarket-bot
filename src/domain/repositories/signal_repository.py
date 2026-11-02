from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.signal import Signal


class SignalRepository(ABC):
    @abstractmethod
    def save(self, signal: Signal) -> Signal: ...

    @abstractmethod
    def list_recent(self, limit: int = 50) -> list[Signal]: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Signal | None: ...
