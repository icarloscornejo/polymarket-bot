from __future__ import annotations

from datetime import datetime

from src.domain.entities.market_resolution import MarketResolution
from src.domain.repositories.market_resolution_repository import MarketResolutionRepository
from src.domain.repositories.trade_repository import TradeRepository


class ResolveMarket:
    """Resolve a closed market: determine outcome and close all open trades."""

    def execute(
        self,
        market_id: str,
        btc_price_at_close: float,
        btc_price_source: str,
        threshold: float,
        resolved_at: datetime,
        trade_repo: TradeRepository,
        resolution_repo: MarketResolutionRepository,
    ) -> MarketResolution:
        if resolution_repo.get_by_market_id(market_id) is not None:
            return resolution_repo.get_by_market_id(market_id)  # type: ignore[return-value]

        outcome = "YES" if btc_price_at_close >= threshold else "NO"

        open_trades = [t for t in trade_repo.list_open() if t.market_id == market_id]
        had_position = len(open_trades) > 0

        for trade in open_trades:
            # YES tokens pay $1 if YES wins; NO tokens pay $1 if NO wins.
            trade_exit = 1.0 if trade.side == outcome else 0.0
            resolved_trade = trade.resolve(exit_price=trade_exit, resolved_at=resolved_at)
            trade_repo.update_status(resolved_trade)

        resolution = MarketResolution(
            market_id=market_id,
            resolved_at=resolved_at,
            threshold=threshold,
            btc_price_at_close=btc_price_at_close,
            btc_price_source=btc_price_source,
            outcome=outcome,
            had_position=had_position,
        )
        return resolution_repo.save(resolution)
