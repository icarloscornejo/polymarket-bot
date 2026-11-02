"""Router for maintenance/status endpoint."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytz
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.dependencies import AppState, get_app_state, get_session
from src.api.schemas.maintenance_schema import MaintenanceStatusSchema
from src.infrastructure.persistence.models import (
    DailySummaryModel,
    MarketSnapshotModel,
    MarketSummaryModel,
)
from src.infrastructure.persistence.runtime_settings_repository_impl import RuntimeSettingsRepositoryImpl

router = APIRouter(tags=["maintenance"])


def _compute_next_cleanup_utc(run_hour: int, timezone_str: str) -> datetime:
    """Compute the next cleanup run time in UTC (same logic as DailyCleanupScheduler)."""
    local_tz = pytz.timezone(timezone_str)
    now_local = datetime.now(tz=timezone.utc).astimezone(local_tz)
    target_local = now_local.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    if target_local <= now_local:
        target_local += timedelta(days=1)
    return target_local.astimezone(pytz.utc).replace(tzinfo=timezone.utc)


@router.get("/maintenance/status", response_model=MaintenanceStatusSchema)
def get_maintenance_status(
    app_state: AppState = Depends(get_app_state),
    session: Session = Depends(get_session),
) -> MaintenanceStatusSchema:
    rt_settings = RuntimeSettingsRepositoryImpl(session).get()

    last_cleanup_row = session.query(func.max(DailySummaryModel.cleanup_ran_at)).scalar()
    last_cleanup_at = (
        last_cleanup_row.replace(tzinfo=timezone.utc) if last_cleanup_row else None
    )

    oldest_row = session.query(func.min(MarketSnapshotModel.timestamp)).scalar()
    oldest_raw = oldest_row.replace(tzinfo=timezone.utc) if oldest_row else None

    total_raw = session.query(func.count(MarketSnapshotModel.id)).scalar() or 0
    total_archived = session.query(func.count(MarketSummaryModel.id)).scalar() or 0
    total_daily = session.query(func.count(DailySummaryModel.id)).scalar() or 0

    next_cleanup = _compute_next_cleanup_utc(app_state.cleanup_run_hour, rt_settings.timezone)

    return MaintenanceStatusSchema(
        last_cleanup_at=last_cleanup_at,
        oldest_raw_snapshot_timestamp=oldest_raw,
        total_raw_snapshots=total_raw,
        total_archived_markets=total_archived,
        total_daily_summaries=total_daily,
        next_cleanup_at=next_cleanup,
    )
