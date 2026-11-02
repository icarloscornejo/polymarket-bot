from __future__ import annotations

from datetime import datetime, timezone

import pytz

from src.domain.entities.daily_summary import DailySummary
from src.domain.entities.trade import TradeMode
from src.domain.repositories.daily_summary_repository import DailySummaryRepository
from src.domain.repositories.market_summary_repository import MarketSummaryRepository
from src.domain.repositories.signal_repository import SignalRepository
from src.domain.repositories.trade_repository import TradeRepository


class BuildDailySummary:
    def __init__(
        self,
        trade_repo: TradeRepository,
        market_summary_repo: MarketSummaryRepository,
        daily_repo: DailySummaryRepository,
        signal_repo: SignalRepository,
    ) -> None:
        self._trade_repo = trade_repo
        self._market_summary_repo = market_summary_repo
        self._daily_repo = daily_repo
        self._signal_repo = signal_repo

    def execute(self, date: str, tz: str, archived_at: datetime) -> DailySummary | None:
        if self._daily_repo.get_by_date(date) is not None:
            return self._daily_repo.get_by_date(date)

        local_tz = pytz.timezone(tz)
        year, month, day = (int(p) for p in date.split("-"))
        day_start = local_tz.localize(datetime(year, month, day, 0, 0, 0))
        day_end = local_tz.localize(datetime(year, month, day, 23, 59, 59))
        start_utc = day_start.astimezone(pytz.utc).replace(tzinfo=timezone.utc)
        end_utc = day_end.astimezone(pytz.utc).replace(tzinfo=timezone.utc)

        trades = self._trade_repo.list_resolved_between(start_utc, end_utc)
        signals = self._signal_repo.list_recent(limit=100000)
        day_signals = [
            s for s in signals
            if start_utc <= s.timestamp <= end_utc
        ]

        paper_trades = [t for t in trades if t.mode == TradeMode.PAPER]
        live_trades = [t for t in trades if t.mode == TradeMode.LIVE]

        def _pnl(ts: list) -> float:
            return sum(t.pnl_usd or 0.0 for t in ts)

        def _invested(ts: list) -> float:
            return sum(t.position_size_usd for t in ts)

        def _winning(ts: list) -> int:
            return sum(1 for t in ts if (t.pnl_usd or 0.0) > 0)

        market_summaries = self._market_summary_repo.list_by_date_range(start_utc, end_utc)

        from src.domain.entities.signal import ActionTaken
        entered = sum(
            1 for s in day_signals
            if s.action_taken in (ActionTaken.PAPER_TRADE, ActionTaken.LIVE_TRADE)
        )

        paper_pnl = _pnl(paper_trades)
        paper_inv = _invested(paper_trades)
        live_pnl = _pnl(live_trades)
        live_inv = _invested(live_trades)

        ds = DailySummary(
            date=date,
            total_markets_archived=len(market_summaries),
            total_snapshots_archived=sum(m.snapshots_count for m in market_summaries),
            total_signals=len(day_signals),
            signals_entered=entered,
            signals_skipped=len(day_signals) - entered,
            paper_trades_count=len(paper_trades),
            paper_winning_trades=_winning(paper_trades),
            paper_pnl_usd=paper_pnl,
            paper_invested_usd=paper_inv,
            live_trades_count=len(live_trades),
            live_winning_trades=_winning(live_trades),
            live_pnl_usd=live_pnl,
            live_invested_usd=live_inv,
            cleanup_ran_at=archived_at,
        )
        return self._daily_repo.save(ds)
