from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Snapshot:
    """A single observation within the logging window of an active market."""

    timestamp: datetime
    market_id: str
    time_to_close_sec: int
    btc_price: float
    btc_price_source: str
    threshold: float
    dtt: float
    yes_price: float
    no_price: float
    spread: float
    book_depth_yes: float
    book_depth_no: float
    book_levels_yes: tuple[tuple[float, float], ...]
    book_levels_no: tuple[tuple[float, float], ...]
    potential_gain_yes: float
    potential_gain_no: float
    strategy_params_id: int

    @classmethod
    def from_market_state(
        cls,
        *,
        timestamp: datetime,
        market_id: str,
        time_to_close_sec: int,
        btc_price: float,
        btc_price_source: str,
        threshold: float,
        yes_price: float,
        no_price: float,
        book_levels_yes: list[tuple[float, float]],
        book_levels_no: list[tuple[float, float]],
        position_size_usd: float,
        strategy_params_id: int,
    ) -> Snapshot:
        """Construct a Snapshot computing all derived fields."""
        dtt = abs(btc_price - threshold)
        spread = yes_price + no_price - 1.0
        book_depth_yes = sum(price * size for price, size in book_levels_yes)
        book_depth_no = sum(price * size for price, size in book_levels_no)
        potential_gain_yes = position_size_usd * (1.0 - yes_price) / yes_price if yes_price > 0 else 0.0
        potential_gain_no = position_size_usd * (1.0 - no_price) / no_price if no_price > 0 else 0.0

        return cls(
            timestamp=timestamp,
            market_id=market_id,
            time_to_close_sec=time_to_close_sec,
            btc_price=btc_price,
            btc_price_source=btc_price_source,
            threshold=threshold,
            dtt=dtt,
            yes_price=yes_price,
            no_price=no_price,
            spread=spread,
            book_depth_yes=book_depth_yes,
            book_depth_no=book_depth_no,
            book_levels_yes=tuple(book_levels_yes),
            book_levels_no=tuple(book_levels_no),
            potential_gain_yes=potential_gain_yes,
            potential_gain_no=potential_gain_no,
            strategy_params_id=strategy_params_id,
        )
