"""Bot entry point (composition root).

Run with:  python -m src.application.bot_runner
"""
from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from src.application.event_bus import EventBus, TOPIC_MODE_CHANGED
from src.application.services.daily_cleanup_scheduler import DailyCleanupScheduler
from src.application.services.market_discovery_service import MarketDiscoveryService
from src.application.services.market_monitor_service import MarketMonitorService
from src.infrastructure.config.settings import Settings, bootstrap
from src.infrastructure.feeds.binance_feed import BinanceFeed
from src.infrastructure.feeds.coinbase_feed import CoinbaseFeed
from src.infrastructure.feeds.failover_btc_feed import FailoverBTCFeed
from src.infrastructure.feeds.polymarket_clob import NullOrderExecutor, PolymarketFeed
from src.infrastructure.logging import configure_logging
from src.infrastructure.persistence.database import make_session_factory
from src.infrastructure.persistence.runtime_settings_repository_impl import RuntimeSettingsRepositoryImpl
from src.infrastructure.persistence.signal_repository_impl import SignalRepositoryImpl
from src.infrastructure.persistence.snapshot_repository_impl import SnapshotRepositoryImpl
from src.infrastructure.persistence.strategy_params_repository_impl import StrategyParamsRepositoryImpl
from src.infrastructure.persistence.trade_repository_impl import TradeRepositoryImpl
from src.domain.entities.market import Market
from src.domain.use_cases.run_daily_cleanup import RunDailyCleanup
from src.infrastructure.persistence.daily_summary_repository_impl import DailySummaryRepositoryImpl
from src.infrastructure.persistence.market_summary_repository_impl import MarketSummaryRepositoryImpl

logger = logging.getLogger(__name__)

# Runtime mode (always starts PAPER per D13)
_current_mode = "PAPER"


def get_mode() -> str:
    return _current_mode


def set_mode(mode: str, bus: EventBus) -> None:
    global _current_mode
    _current_mode = mode
    bus.publish(TOPIC_MODE_CHANGED, mode)
    logger.info("bot_runner mode_changed mode=%s", mode)


async def run(settings: Settings) -> None:  # pragma: no cover
    """Main async entry point. Wires all dependencies and starts the event loop."""
    configure_logging(
        level=settings.logging.level,
        json_output=settings.logging.json,
    )
    logger.info("bot_runner starting mode=PAPER")

    # Database
    Path(settings.storage.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    session_factory = make_session_factory(f"sqlite:///{settings.storage.sqlite_path}")

    # Seed defaults
    with session_factory() as session:
        bootstrap(session, settings)

    # EventBus
    bus = EventBus()

    # Repositories (long-lived session per service)
    session = session_factory()
    snap_repo = SnapshotRepositoryImpl(session)
    trade_repo = TradeRepositoryImpl(session)
    signal_repo = SignalRepositoryImpl(session)
    params_repo = StrategyParamsRepositoryImpl(session)
    rt_repo = RuntimeSettingsRepositoryImpl(session)
    market_summary_repo = MarketSummaryRepositoryImpl(session)
    daily_summary_repo = DailySummaryRepositoryImpl(session)

    # BTC price feeds
    btc_primary = BinanceFeed()
    btc_fallback = CoinbaseFeed()
    btc_feed = FailoverBTCFeed(
        primary=btc_primary,
        fallback=btc_fallback,
        failover_threshold_sec=settings.runtime.btc_feed_failover_threshold_sec,
    )

    # Polymarket feed
    polymarket_feed = PolymarketFeed.for_paper_mode()

    # Active market monitors
    monitors: dict[str, asyncio.Task] = {}

    async def on_market_discovered(market: Market) -> None:
        svc = MarketMonitorService(
            market=market,
            btc_feed=btc_feed,
            polymarket_feed=polymarket_feed,
            snap_repo=snap_repo,
            trade_repo=trade_repo,
            signal_repo=signal_repo,
            params_repo=params_repo,
            bus=bus,
            mode=get_mode(),
        )
        task = asyncio.create_task(_monitor_loop(svc, market.id))
        monitors[market.id] = task
        logger.info("bot_runner monitor_started market=%s", market.id)

    async def on_market_closed(market: Market) -> None:
        task = monitors.pop(market.id, None)
        if task:
            task.cancel()
            logger.info("bot_runner monitor_stopped market=%s", market.id)

    async def _monitor_loop(svc: MarketMonitorService, market_id: str) -> None:
        interval = params_repo.get_current().snapshot_interval_ms / 1000.0
        while True:
            try:
                await svc.tick()
            except Exception as exc:
                logger.error("monitor_loop error market=%s", market_id, exc_info=exc)
            await asyncio.sleep(interval)

    # Discovery service
    discovery = MarketDiscoveryService(
        polymarket_feed=polymarket_feed,
        on_market_discovered=on_market_discovered,
        on_market_closed=on_market_closed,
    )

    async def _discovery_loop() -> None:
        while True:
            try:
                await discovery.tick()
            except Exception as exc:
                logger.error("discovery_loop error", exc_info=exc)
            await asyncio.sleep(settings.runtime.market_discovery_rest_interval_sec)

    # Cleanup scheduler
    rt_settings = rt_repo.get()

    async def _run_cleanup() -> dict:
        return RunDailyCleanup(
            snap_repo=snap_repo,
            market_summary_repo=market_summary_repo,
            daily_repo=daily_summary_repo,
            trade_repo=trade_repo,
            signal_repo=signal_repo,
        ).execute(
            now_utc=__import__("datetime").datetime.now(
                tz=__import__("datetime").timezone.utc
            ),
            retention_days=settings.cleanup.snapshots_retention_days,
            tz=rt_settings.timezone,
        )

    cleanup_scheduler = DailyCleanupScheduler(
        run_hour_local=settings.cleanup.daily_run_hour_local,
        timezone_str=rt_settings.timezone,
        cleanup_fn=_run_cleanup,
        bus=bus,
    )

    # Gather all tasks
    tasks = [
        asyncio.create_task(btc_primary.run(), name="btc_primary"),
        asyncio.create_task(btc_fallback.run(), name="btc_fallback"),
        asyncio.create_task(_discovery_loop(), name="discovery"),
        asyncio.create_task(cleanup_scheduler.run(), name="cleanup"),
    ]

    logger.info("bot_runner started mode=PAPER tasks=%d", len(tasks))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("bot_runner shutting_down")
    finally:
        for t in tasks:
            t.cancel()
        for mid, t in monitors.items():
            t.cancel()
        session.close()
        logger.info("bot_runner stopped")


def main() -> None:  # pragma: no cover
    settings = Settings.load("config.yml")
    settings.validate_for_mode("PAPER")

    loop = asyncio.new_event_loop()

    def _handle_signal() -> None:
        logger.info("bot_runner signal_received shutting_down")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    try:
        loop.run_until_complete(run(settings))
    finally:
        loop.close()


if __name__ == "__main__":  # pragma: no cover
    main()
