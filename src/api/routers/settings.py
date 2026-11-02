"""Router for runtime settings endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_session
from src.api.schemas.settings_schema import RuntimeSettingsSchema, RuntimeSettingsUpdateSchema
from src.domain.use_cases.update_runtime_settings import UpdateRuntimeSettings
from src.infrastructure.persistence.runtime_settings_repository_impl import RuntimeSettingsRepositoryImpl

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=RuntimeSettingsSchema)
def get_settings(
    session: Session = Depends(get_session),
) -> RuntimeSettingsSchema:
    settings = RuntimeSettingsRepositoryImpl(session).get()
    return RuntimeSettingsSchema(timezone=settings.timezone, updated_at=settings.updated_at)


@router.patch("/settings", response_model=RuntimeSettingsSchema)
def patch_settings(
    body: RuntimeSettingsUpdateSchema,
    session: Session = Depends(get_session),
) -> RuntimeSettingsSchema:
    repo = RuntimeSettingsRepositoryImpl(session)
    updated = UpdateRuntimeSettings(repo).execute(body.timezone)
    session.commit()
    return RuntimeSettingsSchema(timezone=updated.timezone, updated_at=updated.updated_at)
