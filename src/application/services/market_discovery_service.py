from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from src.domain.entities.market import Market

logger = logging.getLogger(__name__)


class MarketDiscoveryService:
    """Polls Polymarket for active BTC markets and tracks additions/removals."""

    def __init__(
        self,
        polymarket_feed: Any,
        on_market_discovered: Callable[[Market], Coroutine[Any, Any, None]],
        on_market_closed: Callable[[Market], Coroutine[Any, Any, None]],
    ) -> None:
        self._feed = polymarket_feed
        self._on_discovered = on_market_discovered
        self._on_closed = on_market_closed
        self._known: dict[str, Market] = {}

    async def tick(self) -> None:
        """Fetch current active markets and fire callbacks for changes."""
        active_markets = await self._feed.discover_active_btc_markets()
        active_by_id = {m.id: m for m in active_markets}

        for market in active_markets:
            if market.id not in self._known:
                self._known[market.id] = market
                await self._on_discovered(market)
                logger.info("market_discovery new market=%s", market.id)

        closed_ids = [mid for mid in self._known if mid not in active_by_id]
        for mid in closed_ids:
            market = self._known.pop(mid)
            await self._on_closed(market)
            logger.info("market_discovery closed market=%s", mid)
