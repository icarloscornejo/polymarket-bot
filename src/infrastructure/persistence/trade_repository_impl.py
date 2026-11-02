from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.domain.entities.trade import Trade, TradeMode, TradeStatus
from src.domain.repositories.trade_repository import TradeRepository
from src.infrastructure.persistence.mappers import trade_from_model, trade_to_model
from src.infrastructure.persistence.models import TradeModel


class TradeRepositoryImpl(TradeRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, trade: Trade) -> Trade:
        self._session.add(trade_to_model(trade))
        self._session.flush()
        return trade

    def update_status(self, trade: Trade) -> Trade:
        row = (
            self._session.query(TradeModel)
            .filter_by(
                market_id=trade.market_id,
                opened_at=trade.opened_at.replace(tzinfo=None),
            )
            .first()
        )
        if row:
            row.status = trade.status.value
            row.exit_price = trade.exit_price
            row.resolved_at = trade.resolved_at.replace(tzinfo=None) if trade.resolved_at else None
            row.pnl_usd = trade.pnl_usd
            row.pnl_pct = trade.pnl_pct
            self._session.flush()
        return trade

    def list_open(self, mode: TradeMode | None = None) -> list[Trade]:
        q = self._session.query(TradeModel).filter_by(status=TradeStatus.OPEN.value)
        if mode is not None:
            q = q.filter_by(mode=mode.value)
        return [trade_from_model(r) for r in q.all()]

    def list_by_mode(self, mode: TradeMode) -> list[Trade]:
        rows = self._session.query(TradeModel).filter_by(mode=mode.value).all()
        return [trade_from_model(r) for r in rows]

    def list_by_market(self, market_id: str) -> list[Trade]:
        rows = self._session.query(TradeModel).filter_by(market_id=market_id).all()
        return [trade_from_model(r) for r in rows]

    def list_resolved_between(self, start_utc: datetime, end_utc: datetime) -> list[Trade]:
        naive_start = start_utc.replace(tzinfo=None)
        naive_end = end_utc.replace(tzinfo=None)
        rows = (
            self._session.query(TradeModel)
            .filter(
                TradeModel.status == TradeStatus.RESOLVED.value,
                TradeModel.resolved_at >= naive_start,
                TradeModel.resolved_at <= naive_end,
            )
            .all()
        )
        return [trade_from_model(r) for r in rows]

    def sum_invested_between(
        self, start_utc: datetime, end_utc: datetime, mode: TradeMode
    ) -> float:
        trades = [
            t for t in self.list_resolved_between(start_utc, end_utc)
            if t.mode == mode
        ]
        return sum(t.position_size_usd for t in trades)
