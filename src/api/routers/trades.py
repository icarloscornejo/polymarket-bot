"""Router for trades endpoints."""
from __future__ import annotations

from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_session
from src.api.schemas.trade_schema import TradeSchema
from src.infrastructure.persistence.models import TradeModel

router = APIRouter(tags=["trades"])


def _to_schema(m: TradeModel) -> TradeSchema:
    return TradeSchema(
        id=m.id,
        signal_id=m.signal_id,
        market_id=m.market_id,
        side=m.side,
        entry_price=m.entry_price,
        entry_btc_price=m.entry_btc_price,
        entry_dtt=m.entry_dtt,
        entry_time_to_close=m.entry_time_to_close,
        position_size_usd=m.position_size_usd,
        status=m.status,
        exit_price=m.exit_price,
        resolved_at=m.resolved_at.replace(tzinfo=timezone.utc) if m.resolved_at else None,
        pnl_usd=m.pnl_usd,
        pnl_pct=m.pnl_pct,
        mode=m.mode,
        opened_at=m.opened_at.replace(tzinfo=timezone.utc),
    )


@router.get("/trades", response_model=list[TradeSchema])
def list_trades(
    mode: Optional[str] = None,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
) -> list[TradeSchema]:
    q = session.query(TradeModel).order_by(TradeModel.opened_at.desc())
    if mode is not None:
        q = q.filter_by(mode=mode)
    if status is not None:
        q = q.filter_by(status=status)
    return [_to_schema(m) for m in q.all()]
