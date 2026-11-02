from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DTT:
    """Distance To Threshold: absolute USD distance between BTC price and market threshold."""

    btc_price: float
    threshold: float

    @property
    def value(self) -> float:
        """Absolute distance, always >= 0."""
        return abs(self.btc_price - self.threshold)

    @property
    def implied_side(self) -> str:
        """YES if BTC is at or above threshold, NO if below."""
        return "YES" if self.btc_price >= self.threshold else "NO"
