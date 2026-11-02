"""TDD tests for DailyCleanupScheduler."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

from src.application.event_bus import EventBus, TOPIC_CLEANUP_RAN, TOPIC_RUNTIME_SETTINGS_UPDATED
from src.application.services.daily_cleanup_scheduler import DailyCleanupScheduler


_NOW_UTC = datetime(2026, 4, 26, 14, 0, 0, tzinfo=timezone.utc)  # 08:00 El Salvador (UTC-6)


class TestDailyCleanupScheduler:

    def _make_scheduler(
        self,
        run_hour_local: int = 3,
        tz: str = "America/El_Salvador",
        cleanup_fn: AsyncMock | None = None,
    ) -> DailyCleanupScheduler:
        return DailyCleanupScheduler(
            run_hour_local=run_hour_local,
            timezone_str=tz,
            cleanup_fn=cleanup_fn or AsyncMock(return_value={"markets_processed": 1}),
            bus=EventBus(),
        )

    def test_calculates_next_run_in_future(self) -> None:
        sched = self._make_scheduler(run_hour_local=3, tz="America/El_Salvador")
        with freeze_time(_NOW_UTC):
            next_run = sched._next_run_utc()
        # Current local time is 08:00, next 03:00 is tomorrow
        assert next_run > _NOW_UTC

    def test_next_run_is_always_in_future(self) -> None:
        sched = self._make_scheduler(run_hour_local=3)
        with freeze_time(_NOW_UTC):
            next_run = sched._next_run_utc()
        assert (next_run - _NOW_UTC).total_seconds() > 0

    @pytest.mark.asyncio
    async def test_invokes_cleanup_when_fired(self) -> None:
        cleanup_fn = AsyncMock(return_value={"markets_processed": 2})
        sched = self._make_scheduler(cleanup_fn=cleanup_fn)

        with patch("src.application.services.daily_cleanup_scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError]
            try:
                await sched.run()
            except asyncio.CancelledError:
                pass

        cleanup_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_publishes_cleanup_ran_event(self) -> None:
        bus = EventBus()
        events: list = []
        bus.subscribe(TOPIC_CLEANUP_RAN, lambda p: events.append(p))

        cleanup_fn = AsyncMock(return_value={"markets_processed": 3})
        sched = DailyCleanupScheduler(
            run_hour_local=3,
            timezone_str="America/El_Salvador",
            cleanup_fn=cleanup_fn,
            bus=bus,
        )

        with patch("src.application.services.daily_cleanup_scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError]
            try:
                await sched.run()
            except asyncio.CancelledError:
                pass

        assert len(events) == 1
        assert events[0]["markets_processed"] == 3

    @pytest.mark.asyncio
    async def test_resilient_to_cleanup_failure(self) -> None:
        """If cleanup raises, scheduler logs and retries tomorrow."""
        cleanup_fn = AsyncMock(side_effect=[RuntimeError("db error"), asyncio.CancelledError])
        sched = self._make_scheduler(cleanup_fn=cleanup_fn)

        with patch("src.application.services.daily_cleanup_scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, asyncio.CancelledError]
            try:
                await sched.run()
            except asyncio.CancelledError:
                pass

        assert cleanup_fn.call_count >= 1

    def test_next_run_is_today_when_run_hour_not_yet_reached(self) -> None:
        """When the target local hour hasn't passed yet, next run is today (no +1 day)."""
        # _NOW_UTC = 14:00 UTC = 08:00 El Salvador; run_hour=22 hasn't passed yet.
        sched = self._make_scheduler(run_hour_local=22, tz="America/El_Salvador")
        with freeze_time(_NOW_UTC):
            next_run = sched._next_run_utc()
        # 22:00 El Salvador = 04:00 UTC next day; but still "today" in local terms (no +1 day).
        # Importantly, the gap should be < 24h from _NOW_UTC.
        gap_hours = (next_run - _NOW_UTC).total_seconds() / 3600
        assert gap_hours < 24
        # Also verify it is in the future (not tomorrow's run + 1 day):
        assert next_run > _NOW_UTC

    @pytest.mark.asyncio
    async def test_recalculates_next_run_when_timezone_changes(self) -> None:
        bus = EventBus()
        sched = DailyCleanupScheduler(
            run_hour_local=3,
            timezone_str="America/El_Salvador",
            cleanup_fn=AsyncMock(return_value={}),
            bus=bus,
        )
        original_tz = sched._timezone_str
        bus.publish(TOPIC_RUNTIME_SETTINGS_UPDATED, MagicMock(timezone="America/Mexico_City"))
        assert sched._timezone_str == "America/Mexico_City"
        assert sched._timezone_str != original_tz
