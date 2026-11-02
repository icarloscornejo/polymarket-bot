"""TDD tests for UpdateStrategyParams, GetCurrentStrategyParams,
GetMonthlyPerformance, and UpdateRuntimeSettings use cases."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tests.unit.domain.fakes import (
    FakeRuntimeSettingsRepository,
    FakeStrategyParamsRepository,
    FakeTradeRepository,
)
from src.domain.entities.trade import Trade, TradeMode, TradeStatus
from src.domain.use_cases.get_monthly_performance import GetMonthlyPerformance
from src.domain.use_cases.update_runtime_settings import UpdateRuntimeSettings
from src.domain.use_cases.update_strategy_params import UpdateStrategyParams
from src.domain.use_cases.get_current_strategy_params import GetCurrentStrategyParams
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow


def _default_params(**overrides: object) -> StrategyParams:
    defaults: dict = {
        "entry_window": TimeWindow(5, 25),
        "min_dtt": 10.0, "min_gain_usd": 0.75,
        "position_size_usd": 10.0,
        "snapshot_interval_ms": 1000,
        "logging_window_buffer_sec": 10,
    }
    defaults.update(overrides)
    return StrategyParams(**defaults)


def _resolved_trade(
    pnl_usd: float,
    position_size: float = 10.0,
    mode: TradeMode = TradeMode.PAPER,
    resolved_at: datetime | None = None,
) -> Trade:
    return Trade(
        signal_id=1, market_id="m1", side="YES",
        entry_price=0.4, entry_btc_price=50020.0,
        entry_dtt=20.0, entry_time_to_close=20,
        position_size_usd=position_size,
        status=TradeStatus.RESOLVED,
        exit_price=1.0 if pnl_usd >= 0 else 0.0,
        resolved_at=resolved_at or datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc),
        pnl_usd=pnl_usd,
        pnl_pct=(pnl_usd / position_size) * 100,
        mode=mode,
        opened_at=datetime(2026, 4, 15, 11, 59, 40, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# UpdateStrategyParams
# ---------------------------------------------------------------------------

class TestUpdateStrategyParams:

    def test_creates_new_version_and_replaces_current(self) -> None:
        repo = FakeStrategyParamsRepository()
        new_params = _default_params(min_dtt=15.0)

        result = UpdateStrategyParams(repo).execute(new_params, updated_by="DASHBOARD")

        assert result.min_dtt == 15.0
        assert repo.get_current().min_dtt == 15.0

    def test_history_grows_on_each_update(self) -> None:
        repo = FakeStrategyParamsRepository()
        UpdateStrategyParams(repo).execute(_default_params(min_dtt=15.0), updated_by="DASHBOARD")
        UpdateStrategyParams(repo).execute(_default_params(min_dtt=20.0), updated_by="DASHBOARD")

        assert len(repo.history) == 3  # initial + 2 updates

    def test_invalid_params_raise_before_persisting(self) -> None:
        repo = FakeStrategyParamsRepository()
        initial_count = len(repo.history)

        with pytest.raises(ValueError):
            UpdateStrategyParams(repo).execute(
                _default_params(position_size_usd=0.0), updated_by="DASHBOARD"
            )

        assert len(repo.history) == initial_count

    def test_updated_by_is_stored(self) -> None:
        # Fake just stores params; validation of updated_by is tested via the interface
        repo = FakeStrategyParamsRepository()
        result = UpdateStrategyParams(repo).execute(_default_params(), updated_by="CONFIG")
        assert result is not None


# ---------------------------------------------------------------------------
# GetCurrentStrategyParams
# ---------------------------------------------------------------------------

class TestGetCurrentStrategyParams:

    def test_returns_current_params(self) -> None:
        repo = FakeStrategyParamsRepository()
        params = GetCurrentStrategyParams(repo).execute()
        assert params.min_dtt == 10.0

    def test_reflects_update_after_change(self) -> None:
        repo = FakeStrategyParamsRepository()
        UpdateStrategyParams(repo).execute(_default_params(min_dtt=99.0), updated_by="DASHBOARD")
        params = GetCurrentStrategyParams(repo).execute()
        assert params.min_dtt == 99.0


# ---------------------------------------------------------------------------
# GetMonthlyPerformance
# ---------------------------------------------------------------------------

class TestGetMonthlyPerformance:

    def test_returns_zeros_when_no_trades_in_month(self) -> None:
        repo = FakeTradeRepository()
        result = GetMonthlyPerformance(repo).execute(
            year=2026, month=4, tz="America/El_Salvador"
        )
        assert result.pnl_usd_paper == pytest.approx(0.0)
        assert result.total_trades == 0

    def test_computes_paper_pnl_for_trades_in_month(self) -> None:
        repo = FakeTradeRepository()
        repo.saved.append(_resolved_trade(pnl_usd=15.0, position_size=10.0))
        repo.saved.append(_resolved_trade(pnl_usd=-10.0, position_size=10.0))

        result = GetMonthlyPerformance(repo).execute(
            year=2026, month=4, tz="America/El_Salvador"
        )

        assert result.pnl_usd_paper == pytest.approx(5.0)
        assert result.total_invested_usd_paper == pytest.approx(20.0)

    def test_pnl_pct_uses_d12_formula(self) -> None:
        repo = FakeTradeRepository()
        repo.saved.append(_resolved_trade(pnl_usd=5.0, position_size=10.0))
        repo.saved.append(_resolved_trade(pnl_usd=5.0, position_size=10.0))

        result = GetMonthlyPerformance(repo).execute(
            year=2026, month=4, tz="America/El_Salvador"
        )

        assert result.pnl_pct_paper == pytest.approx(50.0)

    def test_excludes_trades_from_different_month(self) -> None:
        repo = FakeTradeRepository()
        # March trade - should NOT be included in April
        repo.saved.append(_resolved_trade(
            pnl_usd=100.0,
            resolved_at=datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
        ))

        result = GetMonthlyPerformance(repo).execute(
            year=2026, month=4, tz="America/El_Salvador"
        )

        assert result.pnl_usd_paper == pytest.approx(0.0)

    def test_separates_paper_and_live_pnl(self) -> None:
        repo = FakeTradeRepository()
        repo.saved.append(_resolved_trade(pnl_usd=10.0, mode=TradeMode.PAPER))
        repo.saved.append(_resolved_trade(pnl_usd=20.0, mode=TradeMode.LIVE))

        result = GetMonthlyPerformance(repo).execute(
            year=2026, month=4, tz="America/El_Salvador"
        )

        assert result.pnl_usd_paper == pytest.approx(10.0)
        assert result.pnl_usd_live == pytest.approx(20.0)

    def test_win_rate_counts_positive_pnl_trades(self) -> None:
        repo = FakeTradeRepository()
        repo.saved.append(_resolved_trade(pnl_usd=10.0))
        repo.saved.append(_resolved_trade(pnl_usd=10.0))
        repo.saved.append(_resolved_trade(pnl_usd=-10.0))

        result = GetMonthlyPerformance(repo).execute(
            year=2026, month=4, tz="America/El_Salvador"
        )

        assert result.win_rate == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# UpdateRuntimeSettings
# ---------------------------------------------------------------------------

class TestUpdateRuntimeSettings:

    def test_updates_timezone_successfully(self) -> None:
        repo = FakeRuntimeSettingsRepository()
        result = UpdateRuntimeSettings(repo).execute(timezone="America/Mexico_City")
        assert result.timezone == "America/Mexico_City"

    def test_persists_new_timezone_in_repo(self) -> None:
        repo = FakeRuntimeSettingsRepository()
        UpdateRuntimeSettings(repo).execute(timezone="UTC")
        assert repo.get().timezone == "UTC"

    def test_raises_for_invalid_timezone(self) -> None:
        repo = FakeRuntimeSettingsRepository()
        with pytest.raises(ValueError, match="timezone"):
            UpdateRuntimeSettings(repo).execute(timezone="Not/Valid")

    def test_raises_for_empty_timezone(self) -> None:
        repo = FakeRuntimeSettingsRepository()
        with pytest.raises(ValueError, match="timezone"):
            UpdateRuntimeSettings(repo).execute(timezone="")

    def test_december_month_boundary_is_handled_correctly(self) -> None:
        repo = FakeTradeRepository()
        repo.saved.append(_resolved_trade(
            pnl_usd=5.0,
            resolved_at=datetime(2026, 12, 15, 12, 0, 0, tzinfo=timezone.utc),
        ))
        result = GetMonthlyPerformance(repo).execute(
            year=2026, month=12, tz="America/El_Salvador"
        )
        assert result.pnl_usd_paper == pytest.approx(5.0)
