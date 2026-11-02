from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.domain.entities.market_resolution import MarketResolution
from src.domain.repositories.market_resolution_repository import MarketResolutionRepository
from src.infrastructure.persistence.mappers import resolution_from_model, resolution_to_model
from src.infrastructure.persistence.models import MarketResolutionModel


class MarketResolutionRepositoryImpl(MarketResolutionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, resolution: MarketResolution) -> MarketResolution:
        existing = self.get_by_market_id(resolution.market_id)
        if existing is not None:
            return existing
        self._session.add(resolution_to_model(resolution))
        self._session.flush()
        return resolution

    def get_by_market_id(self, market_id: str) -> MarketResolution | None:
        row = self._session.query(MarketResolutionModel).filter_by(market_id=market_id).first()
        return resolution_from_model(row) if row else None
