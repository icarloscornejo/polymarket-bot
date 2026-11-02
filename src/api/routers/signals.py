"""Router for signal_events endpoints."""
from __future__ import annotations

from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_session
from src.api.schemas.signal_schema import SignalSchema
from src.infrastructure.persistence.models import SignalEventModel

router = APIRouter(tags=["signals"])


def _to_schema(m: SignalEventModel) -> SignalSchema:
    return SignalSchema(
        id=m.id,
        timestamp=m.timestamp.replace(tzinfo=timezone.utc),
        market_id=m.market_id,
        side=m.side,
        yes_price=m.yes_price,
        no_price=m.no_price,
        btc_price=m.btc_price,
        btc_price_source=m.btc_price_source,
        dtt=m.dtt,
        time_to_close_sec=m.time_to_close_sec,
        potential_gain=m.potential_gain,
        action_taken=m.action_taken,
        skip_reason=m.skip_reason,
        strategy_params_id=m.strategy_params_id,
    )


@router.get("/signals", response_model=list[SignalSchema])
def list_signals(
    limit: int = Query(default=50, ge=1, le=500),
    market_id: Optional[str] = None,
    session: Session = Depends(get_session),
) -> list[SignalSchema]:
    q = session.query(SignalEventModel).order_by(SignalEventModel.timestamp.desc())
    if market_id is not None:
        q = q.filter_by(market_id=market_id)
    return [_to_schema(m) for m in q.limit(limit).all()]
