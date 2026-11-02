"""Router for snapshots, active markets, and mode toggle endpoints."""
from __future__ import annotations

from datetime import timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.dependencies import AppState, get_app_state, get_session
from src.api.schemas.snapshot_schema import SnapshotSchema
from src.infrastructure.persistence.models import MarketSnapshotModel

router = APIRouter(tags=["snapshots"])


class ModeUpdateSchema(BaseModel):
    mode: Literal["PAPER", "LIVE"]


class ModeResponseSchema(BaseModel):
    mode: str


def _to_schema(m: MarketSnapshotModel) -> SnapshotSchema:
    return SnapshotSchema(
        id=m.id,
        timestamp=m.timestamp.replace(tzinfo=timezone.utc),
        market_id=m.market_id,
        time_to_close_sec=m.time_to_close_sec,
        btc_price=m.btc_price,
        btc_price_source=m.btc_price_source,
        threshold=m.threshold,
        dtt=m.dtt,
        yes_price=m.yes_price,
        no_price=m.no_price,
        spread=m.spread,
        book_depth_yes=m.book_depth_yes,
        book_depth_no=m.book_depth_no,
        potential_gain_yes=m.potential_gain_yes,
        potential_gain_no=m.potential_gain_no,
        strategy_params_id=m.strategy_params_id,
    )


@router.get("/snapshots", response_model=list[SnapshotSchema])
def list_snapshots(
    market_id: str = Query(...),
    limit: int = Query(default=100, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> list[SnapshotSchema]:
    rows = (
        session.query(MarketSnapshotModel)
        .filter_by(market_id=market_id)
        .order_by(MarketSnapshotModel.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [_to_schema(m) for m in rows]


@router.get("/markets/active", response_model=list[str])
def get_active_markets(
    app_state: AppState = Depends(get_app_state),
) -> list[str]:
    return app_state.active_markets


@router.post("/mode", response_model=ModeResponseSchema)
def set_mode(
    body: ModeUpdateSchema,
    app_state: AppState = Depends(get_app_state),
) -> ModeResponseSchema:
    app_state.mode = body.mode
    return ModeResponseSchema(mode=app_state.mode)
