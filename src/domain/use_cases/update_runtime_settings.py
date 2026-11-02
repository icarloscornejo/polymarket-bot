from __future__ import annotations

from src.domain.entities.runtime_settings import RuntimeSettings
from src.domain.repositories.runtime_settings_repository import RuntimeSettingsRepository


class UpdateRuntimeSettings:
    def __init__(self, repo: RuntimeSettingsRepository) -> None:
        self._repo = repo

    def execute(self, timezone: str) -> RuntimeSettings:
        # Validation delegated to RuntimeSettings entity (raises ValueError if invalid)
        return self._repo.update_timezone(timezone)
