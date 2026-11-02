"""Integration tests for the bot end-to-end flow.

Step 11.1 per PLAN.md:
- Generates >= 1 signal + >= 1 trade in PAPER mode.
- Resolves a simulated market with correct PnL.
- Verifies that a strategy params change mid-run is respected.
- Verifies BTC failover when primary feed goes stale.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.application.event_bus import EventBus, TOPIC_STRATEGY_PARAMS_UPDATED
from src.domain.entities.market import Market
from src.domain.entities.signal import ActionTaken, Signal
from src.domain.entities.trade import TradeMode, TradeStatus
from src.domain.repositories.btc_price_feed import BTCPriceFeed
from src.domain.use_cases.evaluate_signal import EvaluateSignal, MarketState
from src.domain.use_cases.execute_trade import ExecuteTrade
from src.domain.use_cases.resolve_market import ResolveMarket
from src.domain.use_cases.update_strategy_params import UpdateStrategyParams
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow
from src.infrastructure.feeds.failover_btc_feed import FailoverBTCFeed
from src.infrastructure.persistence.database import init_schema, seed_defaults
from src.infrastructure.persistence.market_resolution_repository_impl import MarketResolutionRepositoryImpl
from src.infrastructure.persistence.models import SignalEventModel, TradeModel
from src.infrastructure.persistence.signal_repository_impl import SignalRepositoryImpl
from src.infrastructure.persistence.snapshot_repository_impl import SnapshotRepositoryImpl
from src.infrastructure.persistence.strategy_params_repository_impl import StrategyParamsRepositoryImpl
from src.infrastructure.persistence.trade_repository_impl import TradeRepositoryImpl
from src.application.services.market_monitor_service import MarketMonitorService


# ---------------------------------------------------------------------------
# Fake dependencies
# ---------------------------------------------------------------------------

class FakeBTCFeed(BTCPriceFeed):
    """Controllable BTC price feed stub."""

    def __init__(self, price: float, source: str = "binance", fresh: bool = True) -> None:
        self._price = price
        self._source = source
        self._tick_at: datetime | None = (
            datetime.now(tz=timezone.utc) if fresh else None
        )

    def set_stale(self) -> None:
        """Simulate primary feed going offline (no recent tick)."""
        self._tick_at = datetime.now(tz=timezone.utc) - timedelta(seconds=60)

    def latest_price(self) -> float:
        return self._price

    def last_tick_at(self) -> datetime | None:
        return self._tick_at

    def source_name(self) -> str:
        return self._source


class FakePolymarketFeed:
    """Minimal async Polymarket feed stub returning a fixed order book."""

    def __init__(self, yes_price: float = 0.40, book_depth: float = 500.0) -> None:
        self._yes_price = yes_price
        self._book_depth = book_depth

    async def get_order_book(self, token_id: str) -> list[tuple[float, float]]:
        size_per_level = self._book_depth / 10
        return [(self._yes_price, size_per_level)] * 10


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_THRESHOLD = 50000.0
_BTC_PRICE_YES = 50020.0   # BTC above threshold -> YES side, DTT = 20.0
_BTC_PRICE_NO = 49975.0    # BTC below threshold -> NO side, DTT = 25.0
_YES_PRICE = 0.40           # potential_gain = 10 * 0.60/0.40 = 15.0 > 0.75
_NOW = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)

# Market closes in 15 sec from _NOW — inside the 5-25 entry window
_MARKET = Market(
    id="btc-50000-test",
    threshold=_THRESHOLD,
    closes_at=_NOW + timedelta(seconds=15),
    yes_token_id="yes-token-1",
    no_token_id="no-token-1",
    is_active=True,
)


def _default_params() -> StrategyParams:
    return StrategyParams(
        entry_window=TimeWindow(min_sec=5, max_sec=25),
        min_dtt=10.0,
        min_gain_usd=0.75,
        position_size_usd=10.0,
        snapshot_interval_ms=1000,
        logging_window_buffer_sec=10,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_schema(e)
    return e


@pytest.fixture
def session(engine):
    factory = sessionmaker(bind=engine)
    s = factory()
    seed_defaults(s)
    yield s
    s.close()


@pytest.fixture
def repos(session):
    return {
        "snap": SnapshotRepositoryImpl(session),
        "trade": TradeRepositoryImpl(session),
        "signal": SignalRepositoryImpl(session),
        "params": StrategyParamsRepositoryImpl(session),
        "resolution": MarketResolutionRepositoryImpl(session),
    }


@pytest.fixture
def bus():
    return EventBus()


def _monitor(repos: dict, bus: EventBus, btc_price: float = _BTC_PRICE_YES) -> MarketMonitorService:
    btc_feed = FakeBTCFeed(btc_price)
    poly_feed = FakePolymarketFeed(yes_price=_YES_PRICE)
    return MarketMonitorService(
        market=_MARKET,
        btc_feed=btc_feed,
        polymarket_feed=poly_feed,
        snap_repo=repos["snap"],
        trade_repo=repos["trade"],
        signal_repo=repos["signal"],
        params_repo=repos["params"],
        bus=bus,
        mode="PAPER",
        now_fn=lambda: _NOW,
    )


# ---------------------------------------------------------------------------
# Tests: signal and trade generation (PAPER mode)
# ---------------------------------------------------------------------------

class TestSignalAndTradeGeneration:
    @pytest.mark.asyncio
    async def test_tick_generates_signal_when_conditions_met(self, session, repos, bus) -> None:
        """A single tick with BTC above threshold creates exactly 1 signal."""
        svc = _monitor(repos, bus)

        await svc.tick()

        count = session.query(SignalEventModel).count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_tick_generates_paper_trade_when_conditions_met(self, session, repos, bus) -> None:
        """A single tick under PAPER mode creates exactly 1 PAPER trade."""
        svc = _monitor(repos, bus)

        await svc.tick()

        rows = session.query(TradeModel).all()
        assert len(rows) == 1
        assert rows[0].mode == "PAPER"
        assert rows[0].status == "OPEN"

    @pytest.mark.asyncio
    async def test_signal_side_is_yes_when_btc_above_threshold(self, session, repos, bus) -> None:
        svc = _monitor(repos, bus, btc_price=_BTC_PRICE_YES)

        await svc.tick()

        row = session.query(SignalEventModel).first()
        assert row is not None
        assert row.side == "YES"

    @pytest.mark.asyncio
    async def test_signal_side_is_no_when_btc_below_threshold(self, session, repos, bus) -> None:
        poly_feed = FakePolymarketFeed(yes_price=0.60)
        btc_feed = FakeBTCFeed(_BTC_PRICE_NO)
        svc = MarketMonitorService(
            market=_MARKET,
            btc_feed=btc_feed,
            polymarket_feed=poly_feed,
            snap_repo=repos["snap"],
            trade_repo=repos["trade"],
            signal_repo=repos["signal"],
            params_repo=repos["params"],
            bus=bus,
            mode="PAPER",
            now_fn=lambda: _NOW,
        )

        await svc.tick()

        row = session.query(SignalEventModel).first()
        assert row is not None
        assert row.side == "NO"

    @pytest.mark.asyncio
    async def test_trade_entry_price_matches_yes_price(self, session, repos, bus) -> None:
        svc = _monitor(repos, bus)

        await svc.tick()

        row = session.query(TradeModel).first()
        assert row is not None
        assert abs(row.entry_price - _YES_PRICE) < 1e-6

    @pytest.mark.asyncio
    async def test_snapshot_persisted_within_logging_window(self, session, repos, bus) -> None:
        """Market closes in 15 sec; logging_window_max = 25+10 = 35 sec -> snapshot saved."""
        from src.infrastructure.persistence.models import MarketSnapshotModel
        svc = _monitor(repos, bus)

        await svc.tick()

        snap_count = session.query(MarketSnapshotModel).count()
        assert snap_count == 1

    @pytest.mark.asyncio
    async def test_no_signal_when_outside_entry_window(self, session, repos, bus) -> None:
        """Market closes in 100 sec (outside 5-25 window) -> no signal, no trade."""
        far_market = Market(
            id="btc-50000-far",
            threshold=_THRESHOLD,
            closes_at=_NOW + timedelta(seconds=100),
            yes_token_id="yes-token-2",
            no_token_id="no-token-2",
            is_active=True,
        )
        svc = MarketMonitorService(
            market=far_market,
            btc_feed=FakeBTCFeed(_BTC_PRICE_YES),
            polymarket_feed=FakePolymarketFeed(),
            snap_repo=repos["snap"],
            trade_repo=repos["trade"],
            signal_repo=repos["signal"],
            params_repo=repos["params"],
            bus=bus,
            mode="PAPER",
            now_fn=lambda: _NOW,
        )

        await svc.tick()

        assert session.query(SignalEventModel).count() == 0
        assert session.query(TradeModel).count() == 0


# ---------------------------------------------------------------------------
# Tests: market resolution with correct PnL
# ---------------------------------------------------------------------------

class TestMarketResolution:
    @pytest.mark.asyncio
    async def test_resolve_market_yes_outcome_sets_correct_pnl(self, session, repos, bus) -> None:
        """BTC above threshold -> YES wins. Trade on YES side exits at 1.0 -> PnL = +6.0."""
        svc = _monitor(repos, bus)
        await svc.tick()

        resolved_at = _NOW + timedelta(seconds=15)
        ResolveMarket().execute(
            market_id=_MARKET.id,
            btc_price_at_close=50100.0,   # above threshold -> YES
            btc_price_source="binance",
            threshold=_THRESHOLD,
            resolved_at=resolved_at,
            trade_repo=repos["trade"],
            resolution_repo=repos["resolution"],
        )

        row = session.query(TradeModel).first()
        assert row is not None
        assert row.status == "RESOLVED"
        # shares = 10.0 / 0.40 = 25; exit = 1.0 (YES wins) -> PnL = 25*1.0 - 10 = 15.0
        assert row.pnl_usd is not None
        assert abs(row.pnl_usd - 15.0) < 0.01

    @pytest.mark.asyncio
    async def test_resolve_market_no_outcome_sets_loss_on_yes_trade(self, session, repos, bus) -> None:
        """BTC below threshold -> NO wins. YES trade loses."""
        svc = _monitor(repos, bus)
        await svc.tick()

        resolved_at = _NOW + timedelta(seconds=15)
        ResolveMarket().execute(
            market_id=_MARKET.id,
            btc_price_at_close=49900.0,   # below threshold -> NO wins
            btc_price_source="binance",
            threshold=_THRESHOLD,
            resolved_at=resolved_at,
            trade_repo=repos["trade"],
            resolution_repo=repos["resolution"],
        )

        row = session.query(TradeModel).first()
        assert row is not None
        assert row.status == "RESOLVED"
        # shares = 10.0 / 0.40 = 25; exit = 0.0 (YES loses when NO wins) -> PnL = 25*0.0 - 10 = -10.0
        assert row.pnl_usd is not None
        assert abs(row.pnl_usd - (-10.0)) < 0.01

    @pytest.mark.asyncio
    async def test_resolve_market_is_idempotent(self, session, repos, bus) -> None:
        """Calling ResolveMarket twice for the same market does not create duplicate rows."""
        from src.infrastructure.persistence.models import MarketResolutionModel

        svc = _monitor(repos, bus)
        await svc.tick()

        resolved_at = _NOW + timedelta(seconds=15)
        kwargs: dict = dict(
            market_id=_MARKET.id,
            btc_price_at_close=50100.0,
            btc_price_source="binance",
            threshold=_THRESHOLD,
            resolved_at=resolved_at,
            trade_repo=repos["trade"],
            resolution_repo=repos["resolution"],
        )
        ResolveMarket().execute(**kwargs)
        ResolveMarket().execute(**kwargs)

        count = session.query(MarketResolutionModel).count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_had_position_true_when_trade_existed(self, session, repos, bus) -> None:
        from src.infrastructure.persistence.models import MarketResolutionModel

        svc = _monitor(repos, bus)
        await svc.tick()

        ResolveMarket().execute(
            market_id=_MARKET.id,
            btc_price_at_close=50100.0,
            btc_price_source="binance",
            threshold=_THRESHOLD,
            resolved_at=_NOW + timedelta(seconds=15),
            trade_repo=repos["trade"],
            resolution_repo=repos["resolution"],
        )

        row = session.query(MarketResolutionModel).first()
        assert row is not None
        assert row.had_position is True


# ---------------------------------------------------------------------------
# Tests: strategy params change mid-run is respected
# ---------------------------------------------------------------------------

class TestStrategyParamsMidRunChange:
    @pytest.mark.asyncio
    async def test_monitor_picks_up_updated_params_via_event_bus(
        self, session, repos, bus
    ) -> None:
        """After params change (min_dtt raised), the next tick should no longer fire a signal."""
        svc = _monitor(repos, bus)

        # First tick: DTT=20 > min_dtt=10 -> fires
        await svc.tick()
        assert session.query(SignalEventModel).count() == 1

        # Raise min_dtt so current BTC price no longer satisfies it
        new_params = StrategyParams(
            entry_window=TimeWindow(min_sec=5, max_sec=25),
            min_dtt=50.0,   # current DTT is only 20
            min_gain_usd=0.75,
            position_size_usd=10.0,
            snapshot_interval_ms=1000,
            logging_window_buffer_sec=10,
        )
        # Update via use case (persists to DB and publishes event)
        UpdateStrategyParams(repos["params"]).execute(new_params, updated_by="DASHBOARD")
        # Manually publish so monitor service hears it (mirrors bot_runner.py wiring)
        bus.publish(TOPIC_STRATEGY_PARAMS_UPDATED, new_params)

        # Second tick: min_dtt=50 but DTT=20 -> no signal
        await svc.tick()
        assert session.query(SignalEventModel).count() == 1  # still only 1

    @pytest.mark.asyncio
    async def test_monitor_applies_new_position_size_from_updated_params(
        self, session, repos, bus
    ) -> None:
        """Position size change is reflected in the next trade."""
        svc = _monitor(repos, bus)
        await svc.tick()

        row = session.query(TradeModel).first()
        assert row is not None
        assert abs(row.position_size_usd - 10.0) < 0.01

        # Create a fresh market instance 1 sec later so a second signal can fire
        market2 = Market(
            id="btc-50000-test-2",
            threshold=_THRESHOLD,
            closes_at=_NOW + timedelta(seconds=14),
            yes_token_id="yes-token-3",
            no_token_id="no-token-3",
            is_active=True,
        )
        new_params = StrategyParams(
            entry_window=TimeWindow(min_sec=5, max_sec=25),
            min_dtt=10.0,
            min_gain_usd=0.75,
            position_size_usd=25.0,
            snapshot_interval_ms=1000,
            logging_window_buffer_sec=10,
        )
        UpdateStrategyParams(repos["params"]).execute(new_params, updated_by="DASHBOARD")
        bus.publish(TOPIC_STRATEGY_PARAMS_UPDATED, new_params)

        svc2 = MarketMonitorService(
            market=market2,
            btc_feed=FakeBTCFeed(_BTC_PRICE_YES),
            polymarket_feed=FakePolymarketFeed(yes_price=0.30, book_depth=1000.0),
            snap_repo=repos["snap"],
            trade_repo=repos["trade"],
            signal_repo=repos["signal"],
            params_repo=repos["params"],
            bus=bus,
            mode="PAPER",
            now_fn=lambda: _NOW,
        )
        # Prime svc2 with the new params via event bus subscription
        bus.publish(TOPIC_STRATEGY_PARAMS_UPDATED, new_params)
        await svc2.tick()

        rows = session.query(TradeModel).order_by(TradeModel.id.desc()).all()
        assert len(rows) >= 2
        latest = rows[0]
        assert abs(latest.position_size_usd - 25.0) < 0.01


# ---------------------------------------------------------------------------
# Tests: BTC failover when primary feed goes stale
# ---------------------------------------------------------------------------

class TestBTCFailover:
    def _failover_feed(
        self,
        primary: FakeBTCFeed,
        fallback: FakeBTCFeed,
        *,
        failover_threshold_sec: float = 3.0,
    ) -> FailoverBTCFeed:
        now = datetime.now(tz=timezone.utc)
        return FailoverBTCFeed(
            primary=primary,
            fallback=fallback,
            failover_threshold_sec=failover_threshold_sec,
            now_fn=lambda: now,
        )

    def test_primary_active_when_fresh(self) -> None:
        primary = FakeBTCFeed(50020.0, source="binance", fresh=True)
        fallback = FakeBTCFeed(50021.0, source="coinbase", fresh=True)
        feed = self._failover_feed(primary, fallback)

        assert feed.source_name() == "binance"
        assert abs(feed.latest_price() - 50020.0) < 0.01

    def test_failover_to_coinbase_when_primary_stale(self) -> None:
        primary = FakeBTCFeed(50020.0, source="binance", fresh=False)
        fallback = FakeBTCFeed(50021.0, source="coinbase", fresh=True)
        feed = self._failover_feed(primary, fallback)

        assert feed.source_name() == "coinbase"
        assert abs(feed.latest_price() - 50021.0) < 0.01

    def test_failover_happens_mid_run_when_primary_goes_stale(self) -> None:
        """Primary is fresh at start; goes stale after set_stale() is called."""
        now = datetime.now(tz=timezone.utc)
        primary = FakeBTCFeed(50020.0, source="binance", fresh=True)
        fallback = FakeBTCFeed(50019.0, source="coinbase", fresh=True)
        feed = FailoverBTCFeed(
            primary=primary,
            fallback=fallback,
            failover_threshold_sec=3.0,
            now_fn=lambda: now,
        )

        assert feed.source_name() == "binance"

        primary.set_stale()

        assert feed.source_name() == "coinbase"
        assert abs(feed.latest_price() - 50019.0) < 0.01

    def test_raises_when_both_feeds_stale(self) -> None:
        primary = FakeBTCFeed(50020.0, source="binance", fresh=False)
        fallback = FakeBTCFeed(50021.0, source="coinbase", fresh=False)
        feed = self._failover_feed(primary, fallback)

        with pytest.raises(RuntimeError, match="Both BTC price feeds are stale"):
            feed.latest_price()

    @pytest.mark.asyncio
    async def test_monitor_tick_uses_fallback_price_after_failover(
        self, session, repos, bus
    ) -> None:
        """When primary is stale the monitor still ticks using the fallback feed price."""
        now = datetime.now(tz=timezone.utc)
        primary = FakeBTCFeed(50020.0, source="binance", fresh=False)
        fallback = FakeBTCFeed(50025.0, source="coinbase", fresh=True)
        btc_feed = FailoverBTCFeed(
            primary=primary,
            fallback=fallback,
            failover_threshold_sec=3.0,
            now_fn=lambda: now,
        )

        svc = MarketMonitorService(
            market=_MARKET,
            btc_feed=btc_feed,
            polymarket_feed=FakePolymarketFeed(yes_price=_YES_PRICE),
            snap_repo=repos["snap"],
            trade_repo=repos["trade"],
            signal_repo=repos["signal"],
            params_repo=repos["params"],
            bus=bus,
            mode="PAPER",
            now_fn=lambda: _NOW,
        )

        await svc.tick()

        row = session.query(SignalEventModel).first()
        assert row is not None
        assert row.btc_price_source == "coinbase"
        assert abs(row.btc_price - 50025.0) < 0.01

    @pytest.mark.asyncio
    async def test_monitor_tick_skips_gracefully_when_both_feeds_stale(
        self, session, repos, bus
    ) -> None:
        """When both BTC feeds are stale on startup, tick() returns early without persisting
        any snapshot, signal, or trade (no RuntimeError propagates)."""
        now = datetime.now(tz=timezone.utc)
        primary = FakeBTCFeed(50020.0, source="binance", fresh=False)
        fallback = FakeBTCFeed(50021.0, source="coinbase", fresh=False)
        btc_feed = FailoverBTCFeed(
            primary=primary,
            fallback=fallback,
            failover_threshold_sec=3.0,
            now_fn=lambda: now,
        )

        svc = MarketMonitorService(
            market=_MARKET,
            btc_feed=btc_feed,
            polymarket_feed=FakePolymarketFeed(yes_price=_YES_PRICE),
            snap_repo=repos["snap"],
            trade_repo=repos["trade"],
            signal_repo=repos["signal"],
            params_repo=repos["params"],
            bus=bus,
            mode="PAPER",
            now_fn=lambda: _NOW,
        )

        await svc.tick()  # must not raise

        assert session.query(SignalEventModel).count() == 0
        assert session.query(TradeModel).count() == 0
