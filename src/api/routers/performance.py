"""Router for performance endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_session
from src.api.schemas.performance_schema import DailySummarySchema, MonthlyPerformanceSchema
from src.domain.use_cases.get_monthly_performance import GetMonthlyPerformance
from src.infrastructure.persistence.daily_summary_repository_impl import DailySummaryRepositoryImpl
from src.infrastructure.persistence.runtime_settings_repository_impl import RuntimeSettingsRepositoryImpl
from src.infrastructure.persistence.trade_repository_impl import TradeRepositoryImpl

router = APIRouter(tags=["performance"])


@router.get("/performance/monthly", response_model=MonthlyPerformanceSchema)
def get_monthly_performance(
    year: int = Query(...),
    month: int = Query(...),
    tz: str | None = None,
    session: Session = Depends(get_session),
) -> MonthlyPerformanceSchema:
    if tz is None:
        tz = RuntimeSettingsRepositoryImpl(session).get().timezone
    perf = GetMonthlyPerformance(TradeRepositoryImpl(session)).execute(year=year, month=month, tz=tz)
    return MonthlyPerformanceSchema(
        year=perf.year,
        month=perf.month,
        timezone=perf.timezone,
        pnl_usd_paper=perf.pnl_usd_paper,
        pnl_usd_live=perf.pnl_usd_live,
        total_invested_usd_paper=perf.total_invested_usd_paper,
        total_invested_usd_live=perf.total_invested_usd_live,
        total_trades=perf.total_trades,
        winning_trades=perf.winning_trades,
        pnl_pct_paper=perf.pnl_pct_paper,
        pnl_pct_live=perf.pnl_pct_live,
        win_rate=perf.win_rate,
    )


@router.get("/performance/daily", response_model=DailySummarySchema)
def get_daily_performance(
    date: str = Query(...),
    session: Session = Depends(get_session),
) -> DailySummarySchema:
    summary = DailySummaryRepositoryImpl(session).get_by_date(date)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No daily summary for date '{date}'")
    return DailySummarySchema(
        date=summary.date,
        total_markets_archived=summary.total_markets_archived,
        total_snapshots_archived=summary.total_snapshots_archived,
        total_signals=summary.total_signals,
        signals_entered=summary.signals_entered,
        signals_skipped=summary.signals_skipped,
        paper_trades_count=summary.paper_trades_count,
        paper_winning_trades=summary.paper_winning_trades,
        paper_pnl_usd=summary.paper_pnl_usd,
        paper_invested_usd=summary.paper_invested_usd,
        paper_pnl_pct=summary.paper_pnl_pct,
        live_trades_count=summary.live_trades_count,
        live_winning_trades=summary.live_winning_trades,
        live_pnl_usd=summary.live_pnl_usd,
        live_invested_usd=summary.live_invested_usd,
        live_pnl_pct=summary.live_pnl_pct,
        win_rate=summary.win_rate,
        cleanup_ran_at=summary.cleanup_ran_at,
    )
