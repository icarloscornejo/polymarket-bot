"""Tests for bot_runner module-level functions (composition root covered in integration tests)."""
from __future__ import annotations

import pytest

from src.application.bot_runner import get_mode, set_mode
from src.application.event_bus import EventBus, TOPIC_MODE_CHANGED


class TestBotRunner:

    def test_get_mode_returns_paper_by_default(self) -> None:
        import src.application.bot_runner as br
        br._current_mode = "PAPER"
        assert get_mode() == "PAPER"

    def test_set_mode_publishes_event(self) -> None:
        import src.application.bot_runner as br
        bus = EventBus()
        received: list = []
        bus.subscribe(TOPIC_MODE_CHANGED, lambda m: received.append(m))
        set_mode("LIVE", bus)
        assert received == ["LIVE"]
        br._current_mode = "PAPER"

    def test_set_mode_updates_global_mode(self) -> None:
        import src.application.bot_runner as br
        set_mode("LIVE", EventBus())
        assert get_mode() == "LIVE"
        br._current_mode = "PAPER"
