"""Structural tests for domain repository interfaces (ABC enforcement)."""
from __future__ import annotations

import importlib
import inspect
from abc import ABC
from types import ModuleType

import pytest


def _load(module_path: str) -> ModuleType:
    return importlib.import_module(module_path)


def _get_abc_class(module_path: str, class_name: str) -> type:
    mod = _load(module_path)
    cls = getattr(mod, class_name)
    assert issubclass(cls, ABC), f"{class_name} must extend ABC"
    return cls


def _abstract_methods(cls: type) -> set[str]:
    return {
        name for name, member in inspect.getmembers(cls)
        if getattr(member, "__isabstractmethod__", False)
    }


def _assert_no_infra_imports(module_path: str) -> None:
    """Verify domain repository source code does not contain infra import statements."""
    import importlib.util, pathlib
    spec = importlib.util.find_spec(module_path)
    assert spec and spec.origin, f"Cannot find module {module_path}"
    source = pathlib.Path(spec.origin).read_text()
    infra_keywords = ["sqlalchemy", "fastapi", "httpx", "websockets"]
    for kw in infra_keywords:
        assert kw not in source, (
            f"{module_path} must not import {kw}, but found it in source"
        )


# ---------------------------------------------------------------------------
# SignalRepository
# ---------------------------------------------------------------------------

class TestSignalRepository:
    MODULE = "src.domain.repositories.signal_repository"
    CLASS = "SignalRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        assert _abstract_methods(cls) >= {"save", "list_recent", "get_by_id"}

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)

    def test_concrete_subclass_without_methods_raises(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        class Incomplete(cls): pass  # type: ignore[abstract]
        with pytest.raises(TypeError):
            Incomplete()


# ---------------------------------------------------------------------------
# TradeRepository
# ---------------------------------------------------------------------------

class TestTradeRepository:
    MODULE = "src.domain.repositories.trade_repository"
    CLASS = "TradeRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        required = {
            "save", "update_status", "list_open", "list_by_mode",
            "list_resolved_between", "sum_invested_between",
        }
        assert _abstract_methods(cls) >= required

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)


# ---------------------------------------------------------------------------
# SnapshotRepository
# ---------------------------------------------------------------------------

class TestSnapshotRepository:
    MODULE = "src.domain.repositories.snapshot_repository"
    CLASS = "SnapshotRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        required = {
            "save", "list_by_market",
            "list_market_ids_with_snapshots_older_than", "delete_by_market",
        }
        assert _abstract_methods(cls) >= required

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)


# ---------------------------------------------------------------------------
# MarketResolutionRepository
# ---------------------------------------------------------------------------

class TestMarketResolutionRepository:
    MODULE = "src.domain.repositories.market_resolution_repository"
    CLASS = "MarketResolutionRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        assert _abstract_methods(cls) >= {"save", "get_by_market_id"}

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)


# ---------------------------------------------------------------------------
# PerformanceRepository
# ---------------------------------------------------------------------------

class TestPerformanceRepository:
    MODULE = "src.domain.repositories.performance_repository"
    CLASS = "PerformanceRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        assert _abstract_methods(cls) >= {"save", "latest"}

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)


# ---------------------------------------------------------------------------
# StrategyParamsRepository
# ---------------------------------------------------------------------------

class TestStrategyParamsRepository:
    MODULE = "src.domain.repositories.strategy_params_repository"
    CLASS = "StrategyParamsRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        assert _abstract_methods(cls) >= {"get_current", "update", "get_by_id"}

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)


# ---------------------------------------------------------------------------
# RuntimeSettingsRepository
# ---------------------------------------------------------------------------

class TestRuntimeSettingsRepository:
    MODULE = "src.domain.repositories.runtime_settings_repository"
    CLASS = "RuntimeSettingsRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        assert _abstract_methods(cls) >= {"get", "update_timezone"}

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)


# ---------------------------------------------------------------------------
# MarketSummaryRepository
# ---------------------------------------------------------------------------

class TestMarketSummaryRepository:
    MODULE = "src.domain.repositories.market_summary_repository"
    CLASS = "MarketSummaryRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        assert _abstract_methods(cls) >= {"save", "get_by_market_id", "list_by_date_range"}

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)


# ---------------------------------------------------------------------------
# DailySummaryRepository
# ---------------------------------------------------------------------------

class TestDailySummaryRepository:
    MODULE = "src.domain.repositories.daily_summary_repository"
    CLASS = "DailySummaryRepository"

    def test_is_abstract_base_class(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        cls = _get_abc_class(self.MODULE, self.CLASS)
        assert _abstract_methods(cls) >= {"save", "get_by_date", "list_dates_without_summary"}

    def test_no_infra_imports(self) -> None:
        _assert_no_infra_imports(self.MODULE)
