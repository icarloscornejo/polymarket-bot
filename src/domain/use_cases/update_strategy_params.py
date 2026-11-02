from __future__ import annotations

from src.domain.repositories.strategy_params_repository import StrategyParamsRepository
from src.domain.value_objects.strategy_params import StrategyParams


class UpdateStrategyParams:
    def __init__(self, repo: StrategyParamsRepository) -> None:
        self._repo = repo

    def execute(self, new_params: StrategyParams, updated_by: str) -> StrategyParams:
        # Validation is enforced by StrategyParams.__post_init__ (raises ValueError if invalid)
        return self._repo.update(new_params, updated_by=updated_by)
