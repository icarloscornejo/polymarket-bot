from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import websockets

from src.domain.repositories.btc_price_feed import BTCPriceFeed

logger = logging.getLogger(__name__)

_BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"
_BACKOFF_MIN = 1.0
_BACKOFF_MAX = 30.0


class BinanceFeed(BTCPriceFeed):
    """BTC price feed from Binance WebSocket (BTCUSDT trade stream)."""

    def __init__(self, url: str = _BINANCE_WS_URL) -> None:
        self._url = url
        self._price: float = 0.0
        self._last_tick: datetime | None = None
        self._backoff_sec: float = _BACKOFF_MIN

    def latest_price(self) -> float:
        return self._price

    def last_tick_at(self) -> datetime | None:
        return self._last_tick

    def source_name(self) -> str:
        return "binance"

    def _handle_message(self, data: dict) -> None:
        if data.get("e") != "trade":
            return
        self._price = float(data["p"])
        self._last_tick = datetime.now(tz=timezone.utc)

    def _on_connection_failure(self) -> None:
        self._backoff_sec = min(self._backoff_sec * 2, _BACKOFF_MAX)

    def _on_connection_success(self) -> None:
        self._backoff_sec = _BACKOFF_MIN

    async def run(self) -> None:
        """Connect to Binance WebSocket and stream prices. Reconnects on failure."""
        while True:
            try:
                async with websockets.connect(self._url) as ws:
                    self._on_connection_success()
                    logger.info("binance_feed connected")
                    async for raw in ws:
                        self._handle_message(json.loads(raw))
            except Exception as exc:
                logger.warning("binance_feed disconnected", exc_info=exc)
                self._on_connection_failure()
                await asyncio.sleep(self._backoff_sec)
