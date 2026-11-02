"""TDD tests for MarketMonitorService and MarketDiscoveryService."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.domain.fakes import (
    FakeSignalRepository,
    FakeSnapshotRepository,
    FakeStrategyParamsRepository,
    FakeTradeRepository,
)
from src.application.event_bus import EventBus, TOPIC_STRATEGY_PARAMS_UPDATED
from src.application.services.market_monitor_service import MarketMonitorService
from src.application.services.market_discovery_service import MarketDiscoveryService
from src.domain.entities.market import Market
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow

_NOW = datetime(2026, 4, 26, 12, 4, 40, tzinfo=timezone.utc)
_CLOSES_AT = datetime(2026, 4, 26, 12, 5, 0, tzinfo=timezone.utc)  # 20s from _NOW
_BOOK = [(0.5, 100.0)] * 10

_DEFAULT_PARAMS = StrategyParams(
    entry_window=TimeWindow(5, 25),
    min_dtt=10.0,
    min_gain_usd=0.75,
    position_size_usd=10.0,
    snapshot_interval_ms=100,  # fast for tests
    logging_window_buffer_sec=10,
)


def _market(threshold: float = 50000.0) -> Market:
    return Market(
        id="m1", threshold=threshold, closes_at=_CLOSES_AT,
        yes_token_id="yes-1", no_token_id="no-1", is_active=True,
    )


def _fake_btc_feed(price: float = 50020.0) -> MagicMock:
    feed = MagicMock()
    feed.latest_price.return_value = price
    feed.last_tick_at.return_value = _NOW
    feed.source_name.return_value = "binance"
    return feed


def _fake_polymarket_feed(book: list | None = None) -> MagicMock:
    feed = MagicMock()
    feed.get_order_book = AsyncMock(return_value=book or _BOOK)
    feed.discover_active_btc_markets = AsyncMock(return_value=[_market()])
    return feed


# ---------------------------------------------------------------------------
# MarketMonitorService
# ---------------------------------------------------------------------------

class TestMarketMonitorService:

    def _make_service(
        self,
        btc_price: float = 50020.0,
        yes_price: float = 0.4,
        book: list | None = None,
        params: StrategyParams | None = None,
    ) -> tuple[MarketMonitorService, FakeSnapshotRepository, FakeTradeRepository, FakeSignalRepository]:
        snap_repo = FakeSnapshotRepository()
        trade_repo = FakeTradeRepository()
        signal_repo = FakeSignalRepository()
        params_repo = FakeStrategyParamsRepository(initial=params or _DEFAULT_PARAMS)
        bus = EventBus()

        svc = MarketMonitorService(
            market=_market(),
            btc_feed=_fake_btc_feed(btc_price),
            polymarket_feed=_fake_polymarket_feed(book),
            snap_repo=snap_repo,
            trade_repo=trade_repo,
            signal_repo=signal_repo,
            params_repo=params_repo,
            bus=bus,
            mode="PAPER",
            now_fn=lambda: _NOW,
        )
        return svc, snap_repo, trade_repo, signal_repo

    @pytest.mark.asyncio
    async def test_tick_persists_snapshot_within_logging_window(self) -> None:
        # 20s to close, logging window = 25 + 10 = 35s -> 20 < 35 -> should snapshot
        svc, snap_repo, _, _ = self._make_service()
        await svc.tick()
        assert len(snap_repo.saved) == 1

    @pytest.mark.asyncio
    async def test_tick_does_not_persist_snapshot_outside_logging_window(self) -> None:
        # Market closes in 60s, logging window = 35s -> 60 > 35 -> no snapshot
        market_far = Market(
            id="m1", threshold=50000.0,
            closes_at=_NOW + timedelta(seconds=60),
            yes_token_id="y", no_token_id="n", is_active=True,
        )
        snap_repo = FakeSnapshotRepository()
        svc = MarketMonitorService(
            market=market_far,
            btc_feed=_fake_btc_feed(),
            polymarket_feed=_fake_polymarket_feed(),
            snap_repo=snap_repo,
            trade_repo=FakeTradeRepository(),
            signal_repo=FakeSignalRepository(),
            params_repo=FakeStrategyParamsRepository(initial=_DEFAULT_PARAMS),
            bus=EventBus(),
            mode="PAPER",
            now_fn=lambda: _NOW,
        )
        await svc.tick()
        assert len(snap_repo.saved) == 0

    @pytest.mark.asyncio
    async def test_tick_creates_paper_trade_when_signal_fires(self) -> None:
        # dtt=20 >= 10, time_to_close=20 in [5,25], yes_price=0.4 -> gain=(10*0.6/0.4)=15 > 0.75
        svc, _, trade_repo, _ = self._make_service(btc_price=50020.0, yes_price=0.4)
        await svc.tick()
        assert len(trade_repo.saved) == 1
        assert trade_repo.saved[0].mode.value == "PAPER"

    @pytest.mark.asyncio
    async def test_tick_skips_trade_when_dtt_below_min(self) -> None:
        # dtt = 50005 - 50000 = 5 < min_dtt=10 -> SKIP
        svc, _, trade_repo, _ = self._make_service(btc_price=50005.0, yes_price=0.4)
        await svc.tick()
        assert len(trade_repo.saved) == 0

    @pytest.mark.asyncio
    async def test_refreshes_params_on_bus_event(self) -> None:
        snap_repo = FakeSnapshotRepository()
        params_repo = FakeStrategyParamsRepository(initial=_DEFAULT_PARAMS)
        bus = EventBus()
        svc = MarketMonitorService(
            market=_market(),
            btc_feed=_fake_btc_feed(),
            polymarket_feed=_fake_polymarket_feed(),
            snap_repo=snap_repo,
            trade_repo=FakeTradeRepository(),
            signal_repo=FakeSignalRepository(),
            params_repo=params_repo,
            bus=bus,
            mode="PAPER",
            now_fn=lambda: _NOW,
        )

        new_params = StrategyParams(
            entry_window=TimeWindow(5, 25), min_dtt=999.0,
            min_gain_usd=0.75, position_size_usd=10.0,
            snapshot_interval_ms=100, logging_window_buffer_sec=10,
        )
        params_repo.update(new_params, updated_by="DASHBOARD")
        bus.publish(TOPIC_STRATEGY_PARAMS_UPDATED, new_params)

        # After refresh, min_dtt=999 so no signal should fire
        trade_repo = FakeTradeRepository()
        svc._trade_repo = trade_repo
        await svc.tick()
        assert len(trade_repo.saved) == 0


# ---------------------------------------------------------------------------
# MarketDiscoveryService
# ---------------------------------------------------------------------------

class TestMarketDiscoveryService:

    @pytest.mark.asyncio
    async def test_discovers_active_markets_on_tick(self) -> None:
        polymarket_feed = _fake_polymarket_feed()
        svc = MarketDiscoveryService(
            polymarket_feed=polymarket_feed,
            on_market_discovered=AsyncMock(),
            on_market_closed=AsyncMock(),
        )
        await svc.tick()
        assert polymarket_feed.discover_active_btc_markets.called

    @pytest.mark.asyncio
    async def test_calls_on_market_discovered_for_new_market(self) -> None:
        on_discovered = AsyncMock()
        polymarket_feed = _fake_polymarket_feed()
        svc = MarketDiscoveryService(
            polymarket_feed=polymarket_feed,
            on_market_discovered=on_discovered,
            on_market_closed=AsyncMock(),
        )
        await svc.tick()
        on_discovered.assert_called_once_with(_market())

    @pytest.mark.asyncio
    async def test_does_not_rediscover_already_known_market(self) -> None:
        on_discovered = AsyncMock()
        polymarket_feed = _fake_polymarket_feed()
        svc = MarketDiscoveryService(
            polymarket_feed=polymarket_feed,
            on_market_discovered=on_discovered,
            on_market_closed=AsyncMock(),
        )
        await svc.tick()
        await svc.tick()
        on_discovered.assert_called_once()  # not twice

    @pytest.mark.asyncio
    async def test_calls_on_market_closed_when_market_disappears(self) -> None:
        on_closed = AsyncMock()
        market = _market()
        # First tick: market active
        polymarket_feed = _fake_polymarket_feed()
        svc = MarketDiscoveryService(
            polymarket_feed=polymarket_feed,
            on_market_discovered=AsyncMock(),
            on_market_closed=on_closed,
        )
        await svc.tick()
        # Second tick: market gone
        polymarket_feed.discover_active_btc_markets = AsyncMock(return_value=[])
        await svc.tick()
        on_closed.assert_called_once_with(market)
