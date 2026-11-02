from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.market import Market


class MarketDataFeed(ABC):
    """Interface for discovering active markets and fetching order books."""

    @abstractmethod
    async def discover_active_btc_markets(self) -> list[Market]:
        """Return currently active BTC 5-minute markets."""
        ...

    @abstractmethod
    async def get_order_book(
        self, token_id: str
    ) -> list[tuple[float, float]]:
        """Return top-10 ask levels as [(price, size), ...] sorted best first."""
        ...
