from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.entities.snapshot import Snapshot
from src.domain.repositories.snapshot_repository import SnapshotRepository
from src.infrastructure.persistence.mappers import snapshot_from_model, snapshot_to_model
from src.infrastructure.persistence.models import MarketSnapshotModel


class SnapshotRepositoryImpl(SnapshotRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, snapshot: Snapshot) -> Snapshot:
        self._session.add(snapshot_to_model(snapshot))
        self._session.flush()
        return snapshot

    def list_by_market(self, market_id: str, limit: int | None = None) -> list[Snapshot]:
        q = (
            self._session.query(MarketSnapshotModel)
            .filter_by(market_id=market_id)
            .order_by(MarketSnapshotModel.timestamp.asc())
        )
        if limit:
            q = q.limit(limit)
        return [snapshot_from_model(r) for r in q.all()]

    def list_market_ids_with_snapshots_older_than(self, cutoff_utc: datetime) -> list[str]:
        naive_cutoff = cutoff_utc.replace(tzinfo=None)
        rows = (
            self._session.query(MarketSnapshotModel.market_id)
            .filter(MarketSnapshotModel.timestamp < naive_cutoff)
            .distinct()
            .all()
        )
        return [r[0] for r in rows]

    def delete_by_market(self, market_id: str) -> int:
        count = (
            self._session.query(MarketSnapshotModel)
            .filter_by(market_id=market_id)
            .delete()
        )
        self._session.flush()
        return count  # type: ignore[return-value]
