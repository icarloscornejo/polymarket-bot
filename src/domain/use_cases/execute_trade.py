from __future__ import annotations

from datetime import datetime, timezone

from src.domain.entities.signal import Signal
from src.domain.entities.trade import Trade, TradeMode, TradeStatus
from src.domain.repositories.signal_repository import SignalRepository
from src.domain.repositories.trade_repository import TradeRepository


class ExecuteTrade:
    """Persist a trade for a given signal in PAPER or LIVE mode."""

    def execute(
        self,
        signal: Signal,
        mode: TradeMode,
        trade_repo: TradeRepository,
        signal_repo: SignalRepository,
        order_executor: object,
        position_size_usd: float,
    ) -> Trade:
        signal_repo.save(signal)

        if mode == TradeMode.LIVE:
            token_id = signal.market_id  # simplified; real impl uses yes/no token id
            price = signal.yes_price if signal.side == "YES" else signal.no_price
            order_executor.place_order(  # type: ignore[union-attr]
                token_id=token_id, side=signal.side,
                size=position_size_usd, price=price,
            )

        trade = Trade(
            signal_id=0,  # id assigned by DB layer
            market_id=signal.market_id,
            side=signal.side,
            entry_price=signal.yes_price if signal.side == "YES" else signal.no_price,
            entry_btc_price=signal.btc_price,
            entry_dtt=signal.dtt,
            entry_time_to_close=signal.time_to_close_sec,
            position_size_usd=position_size_usd,
            status=TradeStatus.OPEN,
            exit_price=None,
            resolved_at=None,
            pnl_usd=None,
            pnl_pct=None,
            mode=mode,
            opened_at=datetime.now(tz=timezone.utc),
        )
        return trade_repo.save(trade)
