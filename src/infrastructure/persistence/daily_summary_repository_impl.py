from __future__ import annotations

from sqlalchemy.orm import Session

from src.domain.entities.daily_summary import DailySummary
from src.domain.repositories.daily_summary_repository import DailySummaryRepository
from src.infrastructure.persistence.mappers import daily_summary_from_model, daily_summary_to_model
from src.infrastructure.persistence.models import DailySummaryModel


class DailySummaryRepositoryImpl(DailySummaryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, summary: DailySummary) -> DailySummary:
        if self.get_by_date(summary.date) is not None:
            return summary
        self._session.add(daily_summary_to_model(summary))
        self._session.flush()
        return summary

    def get_by_date(self, date: str) -> DailySummary | None:
        row = self._session.query(DailySummaryModel).filter_by(date=date).first()
        return daily_summary_from_model(row) if row else None

    def list_dates_without_summary(self, date_range: list[str]) -> list[str]:
        existing = {
            row.date
            for row in self._session.query(DailySummaryModel.date)
            .filter(DailySummaryModel.date.in_(date_range))
            .all()
        }
        return [d for d in date_range if d not in existing]
