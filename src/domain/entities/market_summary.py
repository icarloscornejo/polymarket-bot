from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MarketSummary:
    """Aggregated statistics for a single archived market."""

    market_id: str
    archived_at: datetime
    closes_at: datetime
    threshold: float
    outcome: str | None
    snapshots_count: int
    btc_price_min: float
    btc_price_max: float
    btc_price_avg: float
    btc_price_at_close: float | None
    dtt_min: float
    dtt_max: float
    dtt_avg: float
    yes_price_min: float
    yes_price_max: float
    yes_price_avg: float
    no_price_min: float
    no_price_max: float
    no_price_avg: float
    spread_avg: float
    book_depth_yes_avg: float
    book_depth_no_avg: float
    signals_count: int
    signals_entered: int
    trades_count: int
    trades_pnl_usd: float

    @classmethod
    def from_raw(
        cls,
        *,
        market_id: str,
        archived_at: datetime,
        closes_at: datetime,
        threshold: float,
        outcome: str | None,
        snapshots: list[dict],
        signals_count: int,
        signals_entered: int,
        trades_count: int,
        trades_pnl_usd: float,
    ) -> MarketSummary:
        if not snapshots:
            raise ValueError("snapshots list must not be empty to build a MarketSummary")

        def _avg(key: str) -> float:
            return sum(s[key] for s in snapshots) / len(snapshots)

        def _min(key: str) -> float:
            return min(s[key] for s in snapshots)

        def _max(key: str) -> float:
            return max(s[key] for s in snapshots)

        return cls(
            market_id=market_id,
            archived_at=archived_at,
            closes_at=closes_at,
            threshold=threshold,
            outcome=outcome,
            snapshots_count=len(snapshots),
            btc_price_min=_min("btc_price"),
            btc_price_max=_max("btc_price"),
            btc_price_avg=_avg("btc_price"),
            btc_price_at_close=snapshots[-1]["btc_price"],
            dtt_min=_min("dtt"),
            dtt_max=_max("dtt"),
            dtt_avg=_avg("dtt"),
            yes_price_min=_min("yes_price"),
            yes_price_max=_max("yes_price"),
            yes_price_avg=_avg("yes_price"),
            no_price_min=_min("no_price"),
            no_price_max=_max("no_price"),
            no_price_avg=_avg("no_price"),
            spread_avg=_avg("spread"),
            book_depth_yes_avg=_avg("book_depth_yes"),
            book_depth_no_avg=_avg("book_depth_no"),
            signals_count=signals_count,
            signals_entered=signals_entered,
            trades_count=trades_count,
            trades_pnl_usd=trades_pnl_usd,
        )
