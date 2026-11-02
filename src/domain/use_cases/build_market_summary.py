from __future__ import annotations

from datetime import datetime

from src.domain.entities.market_summary import MarketSummary
from src.domain.repositories.market_summary_repository import MarketSummaryRepository
from src.domain.repositories.signal_repository import SignalRepository
from src.domain.repositories.snapshot_repository import SnapshotRepository
from src.domain.repositories.trade_repository import TradeRepository


class BuildMarketSummary:
    def __init__(
        self,
        snap_repo: SnapshotRepository,
        summary_repo: MarketSummaryRepository,
        trade_repo: TradeRepository,
        signal_repo: SignalRepository,
    ) -> None:
        self._snap_repo = snap_repo
        self._summary_repo = summary_repo
        self._trade_repo = trade_repo
        self._signal_repo = signal_repo

    def execute(
        self,
        market_id: str,
        closes_at: datetime,
        threshold: float,
        archived_at: datetime,
    ) -> MarketSummary | None:
        if self._summary_repo.get_by_market_id(market_id) is not None:
            return self._summary_repo.get_by_market_id(market_id)

        snapshots = self._snap_repo.list_by_market(market_id)
        if not snapshots:
            return None

        snap_dicts = [
            {
                "btc_price": s.btc_price,
                "btc_price_source": s.btc_price_source,
                "dtt": s.dtt,
                "yes_price": s.yes_price,
                "no_price": s.no_price,
                "spread": s.spread,
                "book_depth_yes": s.book_depth_yes,
                "book_depth_no": s.book_depth_no,
            }
            for s in snapshots
        ]

        signals = self._signal_repo.list_recent(limit=10000)
        market_signals = [sig for sig in signals if sig.market_id == market_id]

        from src.domain.entities.signal import ActionTaken
        signals_entered = sum(
            1 for s in market_signals
            if s.action_taken in (ActionTaken.PAPER_TRADE, ActionTaken.LIVE_TRADE)
        )

        all_trades = self._trade_repo.list_by_market(market_id)
        trades_pnl = sum(t.pnl_usd or 0.0 for t in all_trades)

        summary = MarketSummary.from_raw(
            market_id=market_id,
            archived_at=archived_at,
            closes_at=closes_at,
            threshold=threshold,
            outcome=None,
            snapshots=snap_dicts,
            signals_count=len(market_signals),
            signals_entered=signals_entered,
            trades_count=len(all_trades),
            trades_pnl_usd=trades_pnl,
        )

        self._snap_repo.delete_by_market(market_id)
        return self._summary_repo.save(summary)
