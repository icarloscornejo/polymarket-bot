"""Router for strategy params endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_session
from src.api.schemas.strategy_schema import StrategyParamsRecordSchema, StrategyParamsUpdateSchema
from src.domain.use_cases.update_strategy_params import UpdateStrategyParams
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow
from src.infrastructure.persistence.strategy_params_repository_impl import StrategyParamsRepositoryImpl

router = APIRouter(tags=["strategy"])


@router.get("/strategy", response_model=StrategyParamsRecordSchema)
def get_current_strategy(
    session: Session = Depends(get_session),
) -> StrategyParamsRecordSchema:
    repo = StrategyParamsRepositoryImpl(session)
    record = repo.get_current_record()
    return StrategyParamsRecordSchema(**record)


@router.get("/strategy/history", response_model=list[StrategyParamsRecordSchema])
def get_strategy_history(
    session: Session = Depends(get_session),
) -> list[StrategyParamsRecordSchema]:
    repo = StrategyParamsRepositoryImpl(session)
    return [StrategyParamsRecordSchema(**r) for r in repo.list_all_records()]


@router.patch("/strategy", response_model=StrategyParamsRecordSchema)
def patch_strategy(
    body: StrategyParamsUpdateSchema,
    session: Session = Depends(get_session),
) -> StrategyParamsRecordSchema:
    repo = StrategyParamsRepositoryImpl(session)
    current = repo.get_current_record()

    new_min_sec = body.entry_window_min_sec if body.entry_window_min_sec is not None else current["entry_window_min_sec"]
    new_max_sec = body.entry_window_max_sec if body.entry_window_max_sec is not None else current["entry_window_max_sec"]

    try:
        new_params = StrategyParams(
            entry_window=TimeWindow(min_sec=new_min_sec, max_sec=new_max_sec),
            min_dtt=body.min_dtt if body.min_dtt is not None else current["min_dtt"],
            min_gain_usd=body.min_gain_usd if body.min_gain_usd is not None else current["min_gain_usd"],
            position_size_usd=body.position_size_usd if body.position_size_usd is not None else current["position_size_usd"],
            snapshot_interval_ms=body.snapshot_interval_ms if body.snapshot_interval_ms is not None else current["snapshot_interval_ms"],
            logging_window_buffer_sec=body.logging_window_buffer_sec if body.logging_window_buffer_sec is not None else current["logging_window_buffer_sec"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    UpdateStrategyParams(repo).execute(new_params, updated_by="DASHBOARD")
    session.commit()
    return StrategyParamsRecordSchema(**repo.get_current_record())
