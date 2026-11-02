from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.domain.repositories.strategy_params_repository import StrategyParamsRepository
from src.domain.value_objects.strategy_params import StrategyParams
from src.infrastructure.persistence.mappers import strategy_params_from_model, strategy_params_to_model
from src.infrastructure.persistence.models import StrategyParamsModel


class StrategyParamsRepositoryImpl(StrategyParamsRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current(self) -> StrategyParams:
        row = self._session.query(StrategyParamsModel).filter_by(valid_to=None).first()
        if row is None:
            raise RuntimeError("No current strategy params found. Run seed_defaults() first.")
        return strategy_params_from_model(row)

    def update(self, new_params: StrategyParams, updated_by: str) -> StrategyParams:
        now = datetime.now(tz=timezone.utc)
        current = self._session.query(StrategyParamsModel).filter_by(valid_to=None).first()
        if current:
            current.valid_to = now.replace(tzinfo=None)
        new_model = strategy_params_to_model(new_params, valid_from=now, valid_to=None, updated_by=updated_by)
        self._session.add(new_model)
        self._session.flush()
        return new_params

    def get_by_id(self, id: int) -> StrategyParams | None:
        row = self._session.query(StrategyParamsModel).filter_by(id=id).first()
        return strategy_params_from_model(row) if row else None

    def get_current_id(self) -> int:
        """Return the DB id of the currently active strategy params row."""
        row = self._session.query(StrategyParamsModel.id).filter_by(valid_to=None).first()
        if row is None:
            raise RuntimeError("No current strategy params found. Run seed_defaults() first.")
        return row[0]  # type: ignore[return-value]

    def get_current_record(self) -> dict:
        """Return the full current strategy params row including DB metadata."""
        row = self._session.query(StrategyParamsModel).filter_by(valid_to=None).first()
        if row is None:
            raise RuntimeError("No current strategy params found. Run seed_defaults() first.")
        return self._row_to_dict(row)

    def list_all_records(self) -> list[dict]:
        """Return all strategy params rows ordered newest first (for history)."""
        rows = (
            self._session.query(StrategyParamsModel)
            .order_by(StrategyParamsModel.valid_from.desc())
            .all()
        )
        return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(m: StrategyParamsModel) -> dict:
        return {
            "id": m.id,
            "valid_from": m.valid_from.replace(tzinfo=timezone.utc) if m.valid_from else None,
            "valid_to": m.valid_to.replace(tzinfo=timezone.utc) if m.valid_to else None,
            "updated_by": m.updated_by,
            "entry_window_min_sec": m.entry_window_min_sec,
            "entry_window_max_sec": m.entry_window_max_sec,
            "min_dtt": m.min_dtt,
            "min_gain_usd": m.min_gain_usd,
            "position_size_usd": m.position_size_usd,
            "snapshot_interval_ms": m.snapshot_interval_ms,
            "logging_window_buffer_sec": m.logging_window_buffer_sec,
        }
