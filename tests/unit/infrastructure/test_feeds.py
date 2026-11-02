"""Unit tests for infrastructure feed implementations.
WebSocket connections are mocked. Actual connectivity is tested in smoke run (Phase 11).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.feeds.binance_feed import BinanceFeed
from src.infrastructure.feeds.coinbase_feed import CoinbaseFeed
from src.infrastructure.feeds.failover_btc_feed import FailoverBTCFeed
from src.infrastructure.feeds.polymarket_clob import NullOrderExecutor, PolymarketFeed

_NOW = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

def _binance_msg(price: float) -> str:
    return json.dumps({"e": "trade", "p": str(price), "T": 1745668800000})

def _coinbase_msg(price: float) -> str:
    return json.dumps({"type": "match", "price": str(price), "time": "2026-04-26T12:00:00Z"})


# ---------------------------------------------------------------------------
# BinanceFeed
# ---------------------------------------------------------------------------
class TestBinanceFeed:
    def test_source_name_is_binance(self) -> None:
        assert BinanceFeed().source_name() == "binance"

    def test_latest_price_is_zero_before_tick(self) -> None:
        assert BinanceFeed().latest_price() == 0.0

    def test_last_tick_at_none_before_tick(self) -> None:
        assert BinanceFeed().last_tick_at() is None

    def test_parse_trade_updates_price(self) -> None:
        feed = BinanceFeed()
        feed._handle_message(json.loads(_binance_msg(50000.0)))
        assert feed.latest_price() == pytest.approx(50000.0)

    def test_parse_trade_updates_last_tick_at(self) -> None:
        feed = BinanceFeed()
        feed._handle_message(json.loads(_binance_msg(50000.0)))
        assert feed.last_tick_at() is not None

    def test_multiple_messages_keeps_latest(self) -> None:
        feed = BinanceFeed()
        feed._handle_message(json.loads(_binance_msg(50000.0)))
        feed._handle_message(json.loads(_binance_msg(50500.0)))
        assert feed.latest_price() == pytest.approx(50500.0)

    def test_unknown_event_type_ignored(self) -> None:
        feed = BinanceFeed()
        feed._handle_message({"e": "kline"})
        assert feed.latest_price() == 0.0

    def test_backoff_starts_at_one(self) -> None:
        assert BinanceFeed()._backoff_sec == 1.0

    def test_backoff_doubles_on_failure(self) -> None:
        feed = BinanceFeed()
        feed._on_connection_failure()
        assert feed._backoff_sec == 2.0
        feed._on_connection_failure()
        assert feed._backoff_sec == 4.0

    def test_backoff_caps_at_30(self) -> None:
        feed = BinanceFeed()
        for _ in range(10):
            feed._on_connection_failure()
        assert feed._backoff_sec == 30.0

    def test_backoff_resets_on_success(self) -> None:
        feed = BinanceFeed()
        for _ in range(5):
            feed._on_connection_failure()
        feed._on_connection_success()
        assert feed._backoff_sec == 1.0

    @pytest.mark.asyncio
    async def test_run_parses_message_and_updates_price(self) -> None:
        feed = BinanceFeed()
        msg = _binance_msg(51000.0)

        class FakeWS:
            """Sends one message then raises ConnectionError to trigger reconnect."""
            def __init__(self) -> None:
                self._sent = False

            async def __aenter__(self) -> "FakeWS":
                return self

            async def __aexit__(self, *_) -> None:
                pass

            def __aiter__(self) -> "FakeWS":
                return self

            async def __anext__(self) -> str:
                if not self._sent:
                    self._sent = True
                    return msg
                raise ConnectionError("server closed")  # triggers except + await sleep

        def fake_connect(url, **kwargs):
            return FakeWS()

        with patch("src.infrastructure.feeds.binance_feed.websockets.connect", side_effect=fake_connect):
            with patch("src.infrastructure.feeds.binance_feed.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError  # stop after first reconnect sleep
                try:
                    await feed.run()
                except asyncio.CancelledError:
                    pass

        assert feed.latest_price() == pytest.approx(51000.0)

    @pytest.mark.asyncio
    async def test_run_reconnects_after_failure(self) -> None:
        feed = BinanceFeed()
        connect_count = 0

        def fail_always(url, **kwargs):
            nonlocal connect_count
            connect_count += 1
            raise ConnectionError("dropped")

        with patch("src.infrastructure.feeds.binance_feed.websockets.connect", side_effect=fail_always):
            with patch("src.infrastructure.feeds.binance_feed.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError]  # allow one retry
                try:
                    await feed.run()
                except asyncio.CancelledError:
                    pass

        assert connect_count >= 2
        assert feed._backoff_sec > 1.0


# ---------------------------------------------------------------------------
# CoinbaseFeed
# ---------------------------------------------------------------------------
class TestCoinbaseFeed:
    def test_source_name_is_coinbase(self) -> None:
        assert CoinbaseFeed().source_name() == "coinbase"

    def test_latest_price_is_zero_before_tick(self) -> None:
        assert CoinbaseFeed().latest_price() == 0.0

    def test_parse_match_updates_price(self) -> None:
        feed = CoinbaseFeed()
        feed._handle_message(json.loads(_coinbase_msg(49500.0)))
        assert feed.latest_price() == pytest.approx(49500.0)

    def test_parse_match_updates_last_tick_at(self) -> None:
        feed = CoinbaseFeed()
        feed._handle_message(json.loads(_coinbase_msg(49500.0)))
        assert feed.last_tick_at() is not None

    def test_non_match_message_ignored(self) -> None:
        feed = CoinbaseFeed()
        feed._handle_message({"type": "subscriptions"})
        assert feed.latest_price() == 0.0

    def test_backoff_behavior(self) -> None:
        feed = CoinbaseFeed()
        feed._on_connection_failure()
        feed._on_connection_failure()
        assert feed._backoff_sec == 4.0
        feed._on_connection_success()
        assert feed._backoff_sec == 1.0

    @pytest.mark.asyncio
    async def test_run_parses_match_and_updates_price(self) -> None:
        feed = CoinbaseFeed()
        msg = _coinbase_msg(48500.0)

        class FakeWS:
            def __init__(self) -> None:
                self._sent = False

            async def __aenter__(self) -> "FakeWS":
                return self

            async def __aexit__(self, *_) -> None:
                pass

            async def send(self, data: str) -> None:
                pass

            def __aiter__(self) -> "FakeWS":
                return self

            async def __anext__(self) -> str:
                if not self._sent:
                    self._sent = True
                    return msg
                raise ConnectionError("server closed")

        def fake_connect(url, **kwargs):
            return FakeWS()

        with patch("src.infrastructure.feeds.coinbase_feed.websockets.connect", side_effect=fake_connect):
            with patch("src.infrastructure.feeds.coinbase_feed.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError
                try:
                    await feed.run()
                except asyncio.CancelledError:
                    pass

        assert feed.latest_price() == pytest.approx(48500.0)

    @pytest.mark.asyncio
    async def test_run_reconnects_after_failure(self) -> None:
        feed = CoinbaseFeed()
        connect_count = 0

        def fail_always(url, **kwargs):
            nonlocal connect_count
            connect_count += 1
            raise ConnectionError("dropped")

        with patch("src.infrastructure.feeds.coinbase_feed.websockets.connect", side_effect=fail_always):
            with patch("src.infrastructure.feeds.coinbase_feed.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError]
                try:
                    await feed.run()
                except asyncio.CancelledError:
                    pass

        assert connect_count >= 2
        assert feed._backoff_sec > 1.0


# ---------------------------------------------------------------------------
# FailoverBTCFeed
# ---------------------------------------------------------------------------
class _FakeFeed:
    def __init__(self, price: float = 0.0, last_tick: datetime | None = None, name: str = "fake") -> None:
        self._price = price
        self._last_tick = last_tick
        self._name = name

    def latest_price(self) -> float: return self._price
    def last_tick_at(self) -> datetime | None: return self._last_tick
    def source_name(self) -> str: return self._name


class TestFailoverBTCFeed:
    def _fresh(self, price: float = 50000.0, name: str = "binance") -> _FakeFeed:
        return _FakeFeed(price=price, last_tick=_NOW, name=name)

    def _stale(self, price: float = 49000.0, name: str = "coinbase") -> _FakeFeed:
        return _FakeFeed(price=price, last_tick=_NOW - timedelta(seconds=10), name=name)

    def test_returns_primary_price_when_fresh(self) -> None:
        feed = FailoverBTCFeed(self._fresh(50000.0), self._fresh(49000.0, "coinbase"), now_fn=lambda: _NOW)
        assert feed.latest_price() == pytest.approx(50000.0)

    def test_returns_fallback_when_primary_stale(self) -> None:
        feed = FailoverBTCFeed(self._stale(50000.0, "binance"), self._fresh(49000.0, "coinbase"), now_fn=lambda: _NOW)
        assert feed.latest_price() == pytest.approx(49000.0)

    def test_source_name_follows_active_feed(self) -> None:
        feed = FailoverBTCFeed(self._stale(name="binance"), self._fresh(name="coinbase"), now_fn=lambda: _NOW)
        assert feed.source_name() == "coinbase"

    def test_primary_no_tick_is_stale(self) -> None:
        primary = _FakeFeed(price=50000.0, last_tick=None, name="binance")
        feed = FailoverBTCFeed(primary, self._fresh(49000.0, "coinbase"), now_fn=lambda: _NOW)
        assert feed.latest_price() == pytest.approx(49000.0)

    def test_raises_when_both_stale(self) -> None:
        feed = FailoverBTCFeed(self._stale(), self._stale(), now_fn=lambda: _NOW)
        with pytest.raises(RuntimeError, match="stale"):
            feed.latest_price()

    def test_last_tick_at_returns_active_tick(self) -> None:
        feed = FailoverBTCFeed(self._stale(), self._fresh(), now_fn=lambda: _NOW)
        assert feed.last_tick_at() == _NOW

    def test_last_tick_at_returns_none_when_both_stale(self) -> None:
        feed = FailoverBTCFeed(self._stale(), self._stale(), now_fn=lambda: _NOW)
        assert feed.last_tick_at() is None

    def test_source_name_returns_none_str_when_both_stale(self) -> None:
        feed = FailoverBTCFeed(self._stale(), self._stale(), now_fn=lambda: _NOW)
        assert feed.source_name() == "none"

    def test_fallback_used_without_warning_when_same_source_name(self) -> None:
        """When primary and fallback share the same source name, the warning is skipped.
        Both feeds named 'binance' -> warning branch (43->49) is not taken.
        """
        primary = _FakeFeed(price=50000.0, last_tick=None, name="binance")    # stale (no tick)
        fallback = _FakeFeed(price=49500.0, last_tick=_NOW, name="binance")   # fresh, same name
        feed = FailoverBTCFeed(primary, fallback, now_fn=lambda: _NOW)

        # Should return fallback price without raising or logging a warning.
        assert feed.latest_price() == pytest.approx(49500.0)
        assert feed.source_name() == "binance"


# ---------------------------------------------------------------------------
# NullOrderExecutor
# ---------------------------------------------------------------------------
class TestNullOrderExecutor:
    def test_place_order_does_not_raise(self) -> None:
        assert NullOrderExecutor().place_order("t1", "YES", 10.0, 0.55) is not None

    def test_returns_dict_with_order_id(self) -> None:
        assert "order_id" in NullOrderExecutor().place_order("t1", "YES", 10.0, 0.55)

    def test_records_calls(self) -> None:
        ex = NullOrderExecutor()
        ex.place_order("t1", "YES", 10.0, 0.55)
        ex.place_order("t2", "NO", 10.0, 0.47)
        assert len(ex.calls) == 2


# ---------------------------------------------------------------------------
# PolymarketFeed
# ---------------------------------------------------------------------------
class TestPolymarketFeed:
    def test_normalize_top_10(self) -> None:
        raw = [{"price": str(0.5 - i * 0.01), "size": "100"} for i in range(15)]
        assert len(PolymarketFeed._normalize_book_levels(raw, "asks")) == 10

    def test_normalize_asks_ascending(self) -> None:
        raw = [{"price": "0.55", "size": "100"}, {"price": "0.50", "size": "200"}]
        result = PolymarketFeed._normalize_book_levels(raw, "asks")
        assert result[0][0] <= result[1][0]

    def test_normalize_bids_descending(self) -> None:
        raw = [{"price": "0.40", "size": "100"}, {"price": "0.45", "size": "200"}]
        result = PolymarketFeed._normalize_book_levels(raw, "bids")
        assert result[0][0] >= result[1][0]

    def test_normalize_float_tuples(self) -> None:
        result = PolymarketFeed._normalize_book_levels([{"price": "0.52", "size": "150"}], "asks")
        assert result[0] == pytest.approx((0.52, 150.0))

    def test_normalize_empty_returns_empty(self) -> None:
        assert PolymarketFeed._normalize_book_levels([], "asks") == []

    def test_paper_mode_uses_null_executor(self) -> None:
        assert isinstance(PolymarketFeed.for_paper_mode().order_executor, NullOrderExecutor)

    def test_live_mode_sets_clob_and_executor(self) -> None:
        from src.domain.repositories.order_executor import OrderExecutor
        class FakeEx(OrderExecutor):
            def place_order(self, token_id, side, size, price): return {}
        mock_clob = MagicMock()
        feed = PolymarketFeed.for_live_mode(mock_clob, FakeEx())
        assert feed._clob_client is mock_clob
        assert not isinstance(feed.order_executor, NullOrderExecutor)

    @pytest.mark.asyncio
    async def test_discover_parses_valid_market(self) -> None:
        feed = PolymarketFeed.for_paper_mode()
        fake_data = [{"conditionId": "c1", "threshold": "50000",
                      "endDate": "2026-04-26T12:05:00",
                      "clobTokenIds": ["yes-1", "no-1"], "active": True}]
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_data
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mock_client
            markets = await feed.discover_active_btc_markets()
        assert len(markets) == 1
        assert markets[0].id == "c1"

    @pytest.mark.asyncio
    async def test_discover_skips_malformed(self) -> None:
        feed = PolymarketFeed.for_paper_mode()
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"conditionId": "bad"}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mock_client
            markets = await feed.discover_active_btc_markets()
        assert markets == []

    @pytest.mark.asyncio
    async def test_get_order_book_returns_empty_without_clob(self) -> None:
        result = await PolymarketFeed.for_paper_mode().get_order_book("token-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_order_book_normalizes_clob_response(self) -> None:
        mock_level = MagicMock()
        mock_level.price = "0.55"
        mock_level.size = "100"
        mock_book = MagicMock()
        mock_book.asks = [mock_level]
        mock_clob = MagicMock()
        mock_clob.get_order_book.return_value = mock_book
        result = await PolymarketFeed(clob_client=mock_clob).get_order_book("token-1")
        assert result[0] == pytest.approx((0.55, 100.0))
