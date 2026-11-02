from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.value_objects.strategy_params import StrategyParams


class StrategyParamsRepository(ABC):
    @abstractmethod
    def get_current(self) -> StrategyParams: ...

    @abstractmethod
    def update(self, new_params: StrategyParams, updated_by: str) -> StrategyParams: ...

    @abstractmethod
    def get_by_id(self, id: int) -> StrategyParams | None: ...
