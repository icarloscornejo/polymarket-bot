from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.runtime_settings import RuntimeSettings


class RuntimeSettingsRepository(ABC):
    @abstractmethod
    def get(self) -> RuntimeSettings: ...

    @abstractmethod
    def update_timezone(self, tz: str) -> RuntimeSettings: ...
