from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.domain.entities.runtime_settings import RuntimeSettings
from src.domain.repositories.runtime_settings_repository import RuntimeSettingsRepository
from src.infrastructure.persistence.mappers import runtime_settings_from_model
from src.infrastructure.persistence.models import RuntimeSettingsModel


class RuntimeSettingsRepositoryImpl(RuntimeSettingsRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> RuntimeSettings:
        row = self._session.query(RuntimeSettingsModel).filter_by(id=1).first()
        if row is None:
            raise RuntimeError("RuntimeSettings not seeded.")
        return runtime_settings_from_model(row)

    def update_timezone(self, tz: str) -> RuntimeSettings:
        # Validate via entity (raises ValueError if invalid)
        now = datetime.now(tz=timezone.utc)
        settings = RuntimeSettings(timezone=tz, updated_at=now)
        row = self._session.query(RuntimeSettingsModel).filter_by(id=1).first()
        if row:
            row.timezone = tz
            row.updated_at = now.replace(tzinfo=None)
        else:
            self._session.add(RuntimeSettingsModel(id=1, timezone=tz, updated_at=now.replace(tzinfo=None)))
        self._session.flush()
        return settings
