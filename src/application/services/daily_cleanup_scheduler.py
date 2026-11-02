from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta, timezone
from typing import Any

import pytz

from src.application.event_bus import EventBus, TOPIC_CLEANUP_RAN, TOPIC_RUNTIME_SETTINGS_UPDATED

logger = logging.getLogger(__name__)


class DailyCleanupScheduler:
    """Async service that fires RunDailyCleanup at a fixed local time every day."""

    def __init__(
        self,
        run_hour_local: int,
        timezone_str: str,
        cleanup_fn: Callable[[], Coroutine[Any, Any, dict]],
        bus: EventBus,
    ) -> None:
        self._run_hour = run_hour_local
        self._timezone_str = timezone_str
        self._cleanup_fn = cleanup_fn
        self._bus = bus

        bus.subscribe(TOPIC_RUNTIME_SETTINGS_UPDATED, self._on_settings_updated)

    def _on_settings_updated(self, settings: Any) -> None:
        self._timezone_str = settings.timezone
        logger.info("cleanup_scheduler timezone_changed tz=%s", self._timezone_str)

    def _next_run_utc(self) -> datetime:
        local_tz = pytz.timezone(self._timezone_str)
        now_local = datetime.now(tz=timezone.utc).astimezone(local_tz)
        target_local = now_local.replace(
            hour=self._run_hour, minute=0, second=0, microsecond=0
        )
        if target_local <= now_local:
            target_local += timedelta(days=1)
        return target_local.astimezone(pytz.utc).replace(tzinfo=timezone.utc)

    async def run(self) -> None:
        """Loop forever, sleeping until the next scheduled run time."""
        while True:
            next_run = self._next_run_utc()
            sleep_sec = (next_run - datetime.now(tz=timezone.utc)).total_seconds()
            logger.info("cleanup_scheduler sleeping_until=%s seconds=%.0f", next_run, sleep_sec)
            await asyncio.sleep(max(sleep_sec, 0))

            try:
                result = await self._cleanup_fn()
                logger.info("cleanup_scheduler completed result=%s", result)
                self._bus.publish(TOPIC_CLEANUP_RAN, result)
            except Exception as exc:
                logger.error("cleanup_scheduler failed", exc_info=exc)
