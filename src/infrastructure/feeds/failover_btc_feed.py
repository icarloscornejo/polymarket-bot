from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from src.domain.repositories.btc_price_feed import BTCPriceFeed

logger = logging.getLogger(__name__)


class FailoverBTCFeed(BTCPriceFeed):
    """Wraps a primary and a fallback BTCPriceFeed.

    Returns the primary price when fresh, switches to fallback when the
    primary has not ticked within failover_threshold_sec seconds.
    Raises RuntimeError when both feeds are stale.
    """

    def __init__(
        self,
        primary: BTCPriceFeed,
        fallback: BTCPriceFeed,
        failover_threshold_sec: float = 3.0,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._threshold = failover_threshold_sec
        self._now_fn = now_fn or (lambda: datetime.now(tz=timezone.utc))
        self._last_active_source: str | None = None

    def _is_fresh(self, feed: BTCPriceFeed) -> bool:
        tick = feed.last_tick_at()
        if tick is None:
            return False
        age = (self._now_fn() - tick).total_seconds()
        return age <= self._threshold

    def _active_feed(self) -> BTCPriceFeed:
        if self._is_fresh(self._primary):
            active = self._primary
        elif self._is_fresh(self._fallback):
            active = self._fallback
        else:
            raise RuntimeError(
                f"Both BTC price feeds are stale "
                f"(primary={self._primary.source_name()}, "
                f"fallback={self._fallback.source_name()})"
            )
        source = active.source_name()
        if source != self._last_active_source:
            if self._last_active_source is not None or source != self._primary.source_name():
                logger.warning(
                    "btc_feed_failover active=%s previous=%s",
                    source,
                    self._last_active_source or "none",
                )
            self._last_active_source = source
        return active

    def latest_price(self) -> float:
        return self._active_feed().latest_price()

    def last_tick_at(self) -> datetime | None:
        try:
            return self._active_feed().last_tick_at()
        except RuntimeError:
            return None

    def source_name(self) -> str:
        try:
            return self._active_feed().source_name()
        except RuntimeError:
            return "none"
