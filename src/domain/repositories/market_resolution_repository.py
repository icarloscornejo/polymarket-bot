from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.market_resolution import MarketResolution


class MarketResolutionRepository(ABC):
    @abstractmethod
    def save(self, resolution: MarketResolution) -> MarketResolution: ...

    @abstractmethod
    def get_by_market_id(self, market_id: str) -> MarketResolution | None: ...
