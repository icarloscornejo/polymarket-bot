from __future__ import annotations

from src.domain.repositories.strategy_params_repository import StrategyParamsRepository
from src.domain.value_objects.strategy_params import StrategyParams


class GetCurrentStrategyParams:
    def __init__(self, repo: StrategyParamsRepository) -> None:
        self._repo = repo

    def execute(self) -> StrategyParams:
        return self._repo.get_current()
