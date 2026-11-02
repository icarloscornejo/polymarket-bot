from __future__ import annotations

from abc import ABC, abstractmethod


class OrderExecutor(ABC):
    """Interface for placing real orders on Polymarket."""

    @abstractmethod
    def place_order(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict:
        """Place an order. Returns exchange response dict."""
        ...
