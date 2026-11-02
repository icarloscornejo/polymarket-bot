from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    """Implicit probability price in the range [0.0, 1.0]."""

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(f"Price must be in [0.0, 1.0], got {self.value}")

    def complement(self) -> Price:
        """Return the price of the opposite side (1 - value)."""
        return Price(round(1.0 - self.value, 10))
