from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.domain.entities.market_summary import MarketSummary
from src.domain.repositories.market_summary_repository import MarketSummaryRepository
from src.infrastructure.persistence.mappers import market_summary_from_model, market_summary_to_model
from src.infrastructure.persistence.models import MarketSummaryModel


class MarketSummaryRepositoryImpl(MarketSummaryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, summary: MarketSummary) -> MarketSummary:
        if self.get_by_market_id(summary.market_id) is not None:
            return summary
        self._session.add(market_summary_to_model(summary))
        self._session.flush()
        return summary

    def get_by_market_id(self, market_id: str) -> MarketSummary | None:
        row = self._session.query(MarketSummaryModel).filter_by(market_id=market_id).first()
        return market_summary_from_model(row) if row else None

    def list_by_date_range(self, start_utc: datetime, end_utc: datetime) -> list[MarketSummary]:
        naive_start = start_utc.replace(tzinfo=None)
        naive_end = end_utc.replace(tzinfo=None)
        rows = (
            self._session.query(MarketSummaryModel)
            .filter(
                MarketSummaryModel.closes_at >= naive_start,
                MarketSummaryModel.closes_at <= naive_end,
            )
            .all()
        )
        return [market_summary_from_model(r) for r in rows]
