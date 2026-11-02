"""In-memory fake implementations of domain repositories for use case tests.
These never touch SQLite or any external service.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.daily_summary import DailySummary
from src.domain.entities.market_resolution import MarketResolution
from src.domain.entities.market_summary import MarketSummary
from src.domain.entities.runtime_settings import RuntimeSettings
from src.domain.entities.signal import Signal
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.trade import Trade, TradeMode
from src.domain.repositories.daily_summary_repository import DailySummaryRepository
from src.domain.repositories.market_resolution_repository import MarketResolutionRepository
from src.domain.repositories.market_summary_repository import MarketSummaryRepository
from src.domain.repositories.performance_repository import PerformanceRepository, PerformanceSnapshot
from src.domain.repositories.runtime_settings_repository import RuntimeSettingsRepository
from src.domain.repositories.signal_repository import SignalRepository
from src.domain.repositories.snapshot_repository import SnapshotRepository
from src.domain.repositories.strategy_params_repository import StrategyParamsRepository
from src.domain.repositories.trade_repository import TradeRepository
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow


class FakeSignalRepository(SignalRepository):
    def __init__(self) -> None:
        self.saved: list[Signal] = []

    def save(self, signal: Signal) -> Signal:
        self.saved.append(signal)
        return signal

    def list_recent(self, limit: int = 50) -> list[Signal]:
        return self.saved[-limit:]

    def get_by_id(self, id: int) -> Signal | None:
        return None


class FakeTradeRepository(TradeRepository):
    def __init__(self) -> None:
        self.saved: list[Trade] = []

    def save(self, trade: Trade) -> Trade:
        self.saved.append(trade)
        return trade

    def update_status(self, trade: Trade) -> Trade:
        # Match by market_id + opened_at since Trade has no id field in the domain
        self.saved = [
            trade if (t.market_id == trade.market_id and t.opened_at == trade.opened_at) else t
            for t in self.saved
        ]
        return trade

    def list_open(self, mode: TradeMode | None = None) -> list[Trade]:
        from src.domain.entities.trade import TradeStatus
        trades = [t for t in self.saved if t.status == TradeStatus.OPEN]
        if mode is not None:
            trades = [t for t in trades if t.mode == mode]
        return trades

    def list_by_mode(self, mode: TradeMode) -> list[Trade]:
        return [t for t in self.saved if t.mode == mode]

    def list_resolved_between(self, start_utc: datetime, end_utc: datetime) -> list[Trade]:
        return [
            t for t in self.saved
            if t.resolved_at is not None and start_utc <= t.resolved_at <= end_utc
        ]

    def list_by_market(self, market_id: str) -> list[Trade]:
        return [t for t in self.saved if t.market_id == market_id]

    def sum_invested_between(
        self, start_utc: datetime, end_utc: datetime, mode: TradeMode
    ) -> float:
        return sum(
            t.position_size_usd
            for t in self.list_resolved_between(start_utc, end_utc)
            if t.mode == mode
        )


class FakeSnapshotRepository(SnapshotRepository):
    def __init__(self) -> None:
        self.saved: list[Snapshot] = []

    def save(self, snapshot: Snapshot) -> Snapshot:
        self.saved.append(snapshot)
        return snapshot

    def list_by_market(self, market_id: str, limit: int | None = None) -> list[Snapshot]:
        result = [s for s in self.saved if s.market_id == market_id]
        return result[-limit:] if limit else result

    def list_market_ids_with_snapshots_older_than(self, cutoff_utc: datetime) -> list[str]:
        ids: set[str] = set()
        for s in self.saved:
            if s.timestamp < cutoff_utc:
                ids.add(s.market_id)
        return list(ids)

    def delete_by_market(self, market_id: str) -> int:
        before = len(self.saved)
        self.saved = [s for s in self.saved if s.market_id != market_id]
        return before - len(self.saved)


class FakeMarketResolutionRepository(MarketResolutionRepository):
    def __init__(self) -> None:
        self.saved: list[MarketResolution] = []

    def save(self, resolution: MarketResolution) -> MarketResolution:
        existing = [r for r in self.saved if r.market_id == resolution.market_id]
        if not existing:
            self.saved.append(resolution)
        return resolution

    def get_by_market_id(self, market_id: str) -> MarketResolution | None:
        return next((r for r in self.saved if r.market_id == market_id), None)


class FakeStrategyParamsRepository(StrategyParamsRepository):
    def __init__(self, initial: StrategyParams | None = None) -> None:
        self._current: StrategyParams = initial or StrategyParams(
            entry_window=TimeWindow(min_sec=5, max_sec=25),
            min_dtt=10.0,
            min_gain_usd=0.75,
            position_size_usd=10.0,
            snapshot_interval_ms=1000,
            logging_window_buffer_sec=10,
        )
        self.history: list[StrategyParams] = [self._current]

    def get_current(self) -> StrategyParams:
        return self._current

    def update(self, new_params: StrategyParams, updated_by: str) -> StrategyParams:
        self._current = new_params
        self.history.append(new_params)
        return new_params

    def get_by_id(self, id: int) -> StrategyParams | None:
        if 0 <= id < len(self.history):
            return self.history[id]
        return None


class FakeRuntimeSettingsRepository(RuntimeSettingsRepository):
    def __init__(self, tz: str = "America/El_Salvador") -> None:
        from datetime import timezone
        self._settings = RuntimeSettings(
            timezone=tz,
            updated_at=datetime(2026, 4, 26, 0, 0, 0, tzinfo=timezone.utc),
        )

    def get(self) -> RuntimeSettings:
        return self._settings

    def update_timezone(self, tz: str) -> RuntimeSettings:
        from datetime import timezone
        self._settings = RuntimeSettings(
            timezone=tz,
            updated_at=datetime.now(tz=timezone.utc),
        )
        return self._settings


class FakeMarketSummaryRepository(MarketSummaryRepository):
    def __init__(self) -> None:
        self.saved: list[MarketSummary] = []

    def save(self, summary: MarketSummary) -> MarketSummary:
        if not any(s.market_id == summary.market_id for s in self.saved):
            self.saved.append(summary)
        return summary

    def get_by_market_id(self, market_id: str) -> MarketSummary | None:
        return next((s for s in self.saved if s.market_id == market_id), None)

    def list_by_date_range(
        self, start_utc: datetime, end_utc: datetime
    ) -> list[MarketSummary]:
        return [s for s in self.saved if start_utc <= s.closes_at <= end_utc]


class FakeDailySummaryRepository(DailySummaryRepository):
    def __init__(self) -> None:
        self.saved: list[DailySummary] = []

    def save(self, summary: DailySummary) -> DailySummary:
        if not any(s.date == summary.date for s in self.saved):
            self.saved.append(summary)
        return summary

    def get_by_date(self, date: str) -> DailySummary | None:
        return next((s for s in self.saved if s.date == date), None)

    def list_dates_without_summary(self, date_range: list[str]) -> list[str]:
        existing = {s.date for s in self.saved}
        return [d for d in date_range if d not in existing]


class FakePerformanceRepository(PerformanceRepository):
    def __init__(self) -> None:
        self.saved: list[PerformanceSnapshot] = []

    def save(self, snapshot: PerformanceSnapshot) -> PerformanceSnapshot:
        self.saved.append(snapshot)
        return snapshot

    def latest(self) -> PerformanceSnapshot | None:
        return self.saved[-1] if self.saved else None


class FakeOrderExecutor:
    """Simulates LIVE order execution. Can be configured to succeed or fail."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[dict] = []

    def place_order(
        self, token_id: str, side: str, size: float, price: float
    ) -> dict:
        self.calls.append({"token_id": token_id, "side": side, "size": size, "price": price})
        if self.should_fail:
            raise RuntimeError("Order rejected: insufficient balance")
        return {"order_id": "fake-order-123", "filled": size}
