from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytz

from src.domain.repositories.daily_summary_repository import DailySummaryRepository
from src.domain.repositories.market_summary_repository import MarketSummaryRepository
from src.domain.repositories.signal_repository import SignalRepository
from src.domain.repositories.snapshot_repository import SnapshotRepository
from src.domain.repositories.trade_repository import TradeRepository
from src.domain.use_cases.build_daily_summary import BuildDailySummary
from src.domain.use_cases.build_market_summary import BuildMarketSummary


class RunDailyCleanup:
    def __init__(
        self,
        snap_repo: SnapshotRepository,
        market_summary_repo: MarketSummaryRepository,
        daily_repo: DailySummaryRepository,
        trade_repo: TradeRepository,
        signal_repo: SignalRepository,
    ) -> None:
        self._snap_repo = snap_repo
        self._market_summary_repo = market_summary_repo
        self._daily_repo = daily_repo
        self._trade_repo = trade_repo
        self._signal_repo = signal_repo

    def execute(self, now_utc: datetime, retention_days: int, tz: str) -> dict:
        cutoff = now_utc - timedelta(days=retention_days)
        local_tz = pytz.timezone(tz)

        market_ids = self._snap_repo.list_market_ids_with_snapshots_older_than(cutoff)
        processed_markets = 0
        dates_to_summarize: set[str] = set()

        for market_id in market_ids:
            if self._market_summary_repo.get_by_market_id(market_id) is not None:
                continue

            # Get the closes_at from the oldest snapshot for that market
            snaps = self._snap_repo.list_by_market(market_id)
            if not snaps:
                continue
            closes_at = min(s.timestamp for s in snaps)

            BuildMarketSummary(
                self._snap_repo,
                self._market_summary_repo,
                self._trade_repo,
                self._signal_repo,
            ).execute(
                market_id=market_id,
                closes_at=closes_at,
                threshold=0.0,  # resolved later via market_resolutions
                archived_at=now_utc,
            )
            processed_markets += 1

            # Track which local dates were affected
            local_dt = closes_at.astimezone(local_tz)
            dates_to_summarize.add(local_dt.strftime("%Y-%m-%d"))

        for date in dates_to_summarize:
            BuildDailySummary(
                self._trade_repo,
                self._market_summary_repo,
                self._daily_repo,
                self._signal_repo,
            ).execute(date=date, tz=tz, archived_at=now_utc)

        return {
            "markets_processed": processed_markets,
            "daily_summaries_created": len(dates_to_summarize),
        }
