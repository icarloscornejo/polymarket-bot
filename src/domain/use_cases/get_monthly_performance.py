from __future__ import annotations

from datetime import datetime, timezone

import pytz

from src.domain.entities.monthly_performance import MonthlyPerformance
from src.domain.repositories.trade_repository import TradeRepository
from src.domain.entities.trade import TradeMode


class GetMonthlyPerformance:
    def __init__(self, trade_repo: TradeRepository) -> None:
        self._trade_repo = trade_repo

    def execute(self, year: int, month: int, tz: str) -> MonthlyPerformance:
        local_tz = pytz.timezone(tz)

        # Build UTC range for the full month in local TZ
        month_start_local = local_tz.localize(datetime(year, month, 1, 0, 0, 0))
        if month == 12:
            next_month_local = local_tz.localize(datetime(year + 1, 1, 1, 0, 0, 0))
        else:
            next_month_local = local_tz.localize(datetime(year, month + 1, 1, 0, 0, 0))

        start_utc = month_start_local.astimezone(pytz.utc).replace(tzinfo=timezone.utc)
        end_utc = next_month_local.astimezone(pytz.utc).replace(tzinfo=timezone.utc)

        trades = self._trade_repo.list_resolved_between(start_utc, end_utc)

        pnl_paper = pnl_live = 0.0
        invested_paper = invested_live = 0.0
        total = winning = 0

        for t in trades:
            pnl = t.pnl_usd or 0.0
            if t.mode == TradeMode.PAPER:
                pnl_paper += pnl
                invested_paper += t.position_size_usd
            else:
                pnl_live += pnl
                invested_live += t.position_size_usd
            total += 1
            if pnl > 0:
                winning += 1

        return MonthlyPerformance(
            year=year, month=month, timezone=tz,
            pnl_usd_paper=pnl_paper,
            pnl_usd_live=pnl_live,
            total_invested_usd_paper=invested_paper,
            total_invested_usd_live=invested_live,
            total_trades=total,
            winning_trades=winning,
        )
