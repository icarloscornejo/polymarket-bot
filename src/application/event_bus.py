from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

# Topic constants
TOPIC_STRATEGY_PARAMS_UPDATED = "strategy_params.updated"
TOPIC_RUNTIME_SETTINGS_UPDATED = "runtime_settings.updated"
TOPIC_MODE_CHANGED = "mode.changed"
TOPIC_CLEANUP_RAN = "cleanup.ran"


class EventBus:
    """Lightweight in-memory publish/subscribe event bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, dict[int, Callable[[Any], None]]] = defaultdict(dict)
        self._next_token = 0

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> int:
        """Register a handler for a topic. Returns a token for unsubscribing."""
        token = self._next_token
        self._next_token += 1
        self._handlers[topic][token] = handler
        return token

    def unsubscribe(self, token: int) -> None:
        """Remove a previously registered handler by token."""
        for handlers in self._handlers.values():
            handlers.pop(token, None)

    def publish(self, topic: str, payload: Any) -> None:
        """Deliver payload to all handlers subscribed to topic."""
        for handler in list(self._handlers.get(topic, {}).values()):
            handler(payload)
