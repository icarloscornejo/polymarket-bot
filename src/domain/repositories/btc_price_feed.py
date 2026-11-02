from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class BTCPriceFeed(ABC):
    """Interface for any BTC price data source."""

    @abstractmethod
    def latest_price(self) -> float:
        """Return the most recently observed BTC price."""
        ...

    @abstractmethod
    def last_tick_at(self) -> datetime | None:
        """Return the timestamp of the last received price tick, or None if never received."""
        ...

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this feed (e.g. 'binance', 'coinbase')."""
        ...
