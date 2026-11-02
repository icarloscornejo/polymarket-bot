from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.domain.repositories.market_data_feed import MarketDataFeed
from src.domain.repositories.order_executor import OrderExecutor

logger = logging.getLogger(__name__)


class NullOrderExecutor(OrderExecutor):
    """PAPER mode executor: logs orders without submitting them to the exchange."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def place_order(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict:
        call = {"token_id": token_id, "side": side, "size": size, "price": price}
        self.calls.append(call)
        logger.info("null_order_executor paper_trade token=%s side=%s size=%s price=%s",
                    token_id, side, size, price)
        return {"order_id": f"PAPER-{len(self.calls):04d}", "filled": size, "mode": "PAPER"}


class PolymarketFeed(MarketDataFeed):
    """Fetches active BTC markets and order books from Polymarket's CLOB and Gamma APIs."""

    def __init__(
        self,
        clob_client: Any | None = None,
        order_executor: OrderExecutor | None = None,
        gamma_base_url: str = "https://gamma-api.polymarket.com",
    ) -> None:
        self._clob_client = clob_client
        self.order_executor = order_executor or NullOrderExecutor()
        self._gamma_base_url = gamma_base_url

    @classmethod
    def for_paper_mode(cls) -> PolymarketFeed:
        """Factory for PAPER mode: no CLOB auth required, NullOrderExecutor."""
        return cls(clob_client=None, order_executor=NullOrderExecutor())

    @classmethod
    def for_live_mode(cls, clob_client: Any, order_executor: OrderExecutor) -> PolymarketFeed:
        """Factory for LIVE mode: requires authenticated CLOB client."""
        return cls(clob_client=clob_client, order_executor=order_executor)

    @staticmethod
    def _normalize_book_levels(
        raw_levels: list[dict],
        side: str,
    ) -> list[tuple[float, float]]:
        """Convert raw CLOB levels to sorted (price, size) tuples, top 10 only.

        For asks: sorted ascending (lowest ask first = best price for buyer).
        For bids: sorted descending (highest bid first = best price for seller).
        """
        parsed = [(float(level["price"]), float(level["size"])) for level in raw_levels]
        reverse = side == "bids"
        parsed.sort(key=lambda x: x[0], reverse=reverse)
        return parsed[:10]

    async def discover_active_btc_markets(self):  # type: ignore[override]
        """Fetch active BTC 5-minute markets from Gamma REST API."""
        import httpx
        url = f"{self._gamma_base_url}/markets"
        params = {
            "active": "true",
            "tag_slug": "btc",
            "limit": 100,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        from src.domain.entities.market import Market
        markets: list[Market] = []
        for item in data:
            try:
                markets.append(Market(
                    id=item["conditionId"],
                    threshold=float(item.get("threshold", 0)),
                    closes_at=datetime.fromisoformat(item["endDate"]).replace(tzinfo=timezone.utc),
                    yes_token_id=item.get("clobTokenIds", ["", ""])[0],
                    no_token_id=item.get("clobTokenIds", ["", ""])[1],
                    is_active=item.get("active", False),
                ))
            except (KeyError, ValueError, IndexError):
                logger.warning("polymarket_feed skipped malformed market item=%s", item.get("conditionId"))
        return markets

    async def get_order_book(self, token_id: str) -> list[tuple[float, float]]:
        """Fetch top-10 ask levels for the given token from the CLOB."""
        if self._clob_client is None:
            logger.debug("polymarket_feed no clob_client configured, returning empty book")
            return []
        book = self._clob_client.get_order_book(token_id)
        asks = getattr(book, "asks", []) or []
        return self._normalize_book_levels(
            [{"price": a.price, "size": a.size} for a in asks],
            side="asks",
        )
