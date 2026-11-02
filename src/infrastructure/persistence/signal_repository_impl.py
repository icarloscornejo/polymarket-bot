from __future__ import annotations

from sqlalchemy.orm import Session

from src.domain.entities.signal import Signal
from src.domain.repositories.signal_repository import SignalRepository
from src.infrastructure.persistence.mappers import signal_from_model, signal_to_model
from src.infrastructure.persistence.models import SignalEventModel


class SignalRepositoryImpl(SignalRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, signal: Signal) -> int:
        model = signal_to_model(signal)
        self._session.add(model)
        self._session.flush()
        return model.id  # type: ignore[return-value]

    def list_recent(self, limit: int = 50) -> list[Signal]:
        rows = (
            self._session.query(SignalEventModel)
            .order_by(SignalEventModel.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [signal_from_model(r) for r in rows]

    def get_by_id(self, id: int) -> Signal | None:
        row = self._session.query(SignalEventModel).filter_by(id=id).first()
        return signal_from_model(row) if row else None
