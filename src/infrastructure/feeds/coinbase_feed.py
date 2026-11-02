from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import websockets

from src.domain.repositories.btc_price_feed import BTCPriceFeed

logger = logging.getLogger(__name__)

_COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"
_SUBSCRIBE_MSG = json.dumps({
    "type": "subscribe",
    "product_ids": ["BTC-USD"],
    "channels": ["matches"],
})
_BACKOFF_MIN = 1.0
_BACKOFF_MAX = 30.0


class CoinbaseFeed(BTCPriceFeed):
    """BTC price feed from Coinbase WebSocket (BTC-USD match stream)."""

    def __init__(self, url: str = _COINBASE_WS_URL) -> None:
        self._url = url
        self._price: float = 0.0
        self._last_tick: datetime | None = None
        self._backoff_sec: float = _BACKOFF_MIN

    def latest_price(self) -> float:
        return self._price

    def last_tick_at(self) -> datetime | None:
        return self._last_tick

    def source_name(self) -> str:
        return "coinbase"

    def _handle_message(self, data: dict) -> None:
        if data.get("type") != "match":
            return
        self._price = float(data["price"])
        self._last_tick = datetime.now(tz=timezone.utc)

    def _on_connection_failure(self) -> None:
        self._backoff_sec = min(self._backoff_sec * 2, _BACKOFF_MAX)

    def _on_connection_success(self) -> None:
        self._backoff_sec = _BACKOFF_MIN

    async def run(self) -> None:
        """Connect to Coinbase WebSocket and stream prices. Reconnects on failure."""
        while True:
            try:
                async with websockets.connect(self._url) as ws:
                    await ws.send(_SUBSCRIBE_MSG)
                    self._on_connection_success()
                    logger.info("coinbase_feed connected")
                    async for raw in ws:
                        self._handle_message(json.loads(raw))
            except Exception as exc:
                logger.warning("coinbase_feed disconnected", exc_info=exc)
                self._on_connection_failure()
                await asyncio.sleep(self._backoff_sec)
