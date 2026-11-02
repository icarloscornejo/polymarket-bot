from __future__ import annotations

from sqlalchemy.orm import Session

from src.domain.repositories.performance_repository import PerformanceRepository, PerformanceSnapshot
from src.infrastructure.persistence.mappers import perf_from_model, perf_to_model
from src.infrastructure.persistence.models import PerformanceSnapshotModel


class PerformanceRepositoryImpl(PerformanceRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, snapshot: PerformanceSnapshot) -> PerformanceSnapshot:
        self._session.add(perf_to_model(snapshot))
        self._session.flush()
        return snapshot

    def latest(self) -> PerformanceSnapshot | None:
        row = (
            self._session.query(PerformanceSnapshotModel)
            .order_by(PerformanceSnapshotModel.id.desc())
            .first()
        )
        return perf_from_model(row) if row else None
