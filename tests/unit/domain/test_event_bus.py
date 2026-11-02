"""TDD tests for the in-memory EventBus."""
from __future__ import annotations

import pytest

from src.application.event_bus import EventBus


class TestEventBus:

    def test_subscriber_receives_published_event(self) -> None:
        bus = EventBus()
        received: list = []
        bus.subscribe("test.topic", lambda payload: received.append(payload))
        bus.publish("test.topic", {"key": "value"})
        assert received == [{"key": "value"}]

    def test_multiple_subscribers_all_receive_event(self) -> None:
        bus = EventBus()
        log1: list = []
        log2: list = []
        bus.subscribe("topic", lambda p: log1.append(p))
        bus.subscribe("topic", lambda p: log2.append(p))
        bus.publish("topic", 42)
        assert log1 == [42]
        assert log2 == [42]

    def test_publish_to_unknown_topic_does_not_raise(self) -> None:
        bus = EventBus()
        bus.publish("no.subscribers", {"data": 1})  # must not raise

    def test_subscriber_on_different_topic_does_not_receive(self) -> None:
        bus = EventBus()
        received: list = []
        bus.subscribe("topic.a", lambda p: received.append(p))
        bus.publish("topic.b", "hello")
        assert received == []

    def test_unsubscribe_removes_handler(self) -> None:
        bus = EventBus()
        received: list = []
        token = bus.subscribe("topic", lambda p: received.append(p))
        bus.unsubscribe(token)
        bus.publish("topic", "should not arrive")
        assert received == []

    def test_multiple_publishes_all_delivered(self) -> None:
        bus = EventBus()
        received: list = []
        bus.subscribe("topic", lambda p: received.append(p))
        bus.publish("topic", 1)
        bus.publish("topic", 2)
        bus.publish("topic", 3)
        assert received == [1, 2, 3]

    def test_subscribe_returns_unique_tokens(self) -> None:
        bus = EventBus()
        t1 = bus.subscribe("topic", lambda p: None)
        t2 = bus.subscribe("topic", lambda p: None)
        assert t1 != t2

    def test_known_topics(self) -> None:
        """The plan specifies these 4 topics must exist as constants."""
        from src.application.event_bus import (
            TOPIC_CLEANUP_RAN,
            TOPIC_MODE_CHANGED,
            TOPIC_RUNTIME_SETTINGS_UPDATED,
            TOPIC_STRATEGY_PARAMS_UPDATED,
        )
        assert TOPIC_STRATEGY_PARAMS_UPDATED == "strategy_params.updated"
        assert TOPIC_RUNTIME_SETTINGS_UPDATED == "runtime_settings.updated"
        assert TOPIC_MODE_CHANGED == "mode.changed"
        assert TOPIC_CLEANUP_RAN == "cleanup.ran"
