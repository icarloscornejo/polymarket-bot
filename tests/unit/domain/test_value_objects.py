import pytest

from src.domain.value_objects.price import Price
from src.domain.value_objects.dtt import DTT
from src.domain.value_objects.time_window import TimeWindow
from src.domain.value_objects.strategy_params import StrategyParams


# ---------------------------------------------------------------------------
# Price
# ---------------------------------------------------------------------------

class TestPrice:
    def test_creates_price_when_value_in_range(self) -> None:
        p = Price(0.55)
        assert p.value == 0.55

    def test_creates_price_at_zero(self) -> None:
        p = Price(0.0)
        assert p.value == 0.0

    def test_creates_price_at_one(self) -> None:
        p = Price(1.0)
        assert p.value == 1.0

    def test_raises_when_value_below_zero(self) -> None:
        with pytest.raises(ValueError, match="Price"):
            Price(-0.01)

    def test_raises_when_value_above_one(self) -> None:
        with pytest.raises(ValueError, match="Price"):
            Price(1.001)

    def test_complement_returns_one_minus_value(self) -> None:
        p = Price(0.4)
        assert p.complement().value == pytest.approx(0.6)

    def test_complement_of_complement_returns_original(self) -> None:
        p = Price(0.73)
        assert p.complement().complement().value == pytest.approx(0.73)

    def test_is_frozen_dataclass(self) -> None:
        p = Price(0.5)
        with pytest.raises((AttributeError, TypeError)):
            p.value = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DTT
# ---------------------------------------------------------------------------

class TestDTT:
    def test_value_is_positive_when_btc_above_threshold(self) -> None:
        dtt = DTT(btc_price=50010.0, threshold=50000.0)
        assert dtt.value == pytest.approx(10.0)

    def test_value_is_positive_when_btc_below_threshold(self) -> None:
        dtt = DTT(btc_price=49990.0, threshold=50000.0)
        assert dtt.value == pytest.approx(10.0)

    def test_value_is_zero_when_equal(self) -> None:
        dtt = DTT(btc_price=50000.0, threshold=50000.0)
        assert dtt.value == pytest.approx(0.0)

    def test_implied_side_returns_yes_when_btc_above_threshold(self) -> None:
        dtt = DTT(btc_price=50010.0, threshold=50000.0)
        assert dtt.implied_side == "YES"

    def test_implied_side_returns_no_when_btc_below_threshold(self) -> None:
        dtt = DTT(btc_price=49990.0, threshold=50000.0)
        assert dtt.implied_side == "NO"

    def test_implied_side_returns_yes_when_btc_equals_threshold(self) -> None:
        dtt = DTT(btc_price=50000.0, threshold=50000.0)
        assert dtt.implied_side == "YES"

    def test_is_frozen_dataclass(self) -> None:
        dtt = DTT(btc_price=50010.0, threshold=50000.0)
        with pytest.raises((AttributeError, TypeError)):
            dtt.btc_price = 99999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TimeWindow
# ---------------------------------------------------------------------------

class TestTimeWindow:
    def test_creates_with_valid_range(self) -> None:
        tw = TimeWindow(min_sec=5, max_sec=25)
        assert tw.min_sec == 5
        assert tw.max_sec == 25

    def test_contains_returns_true_when_seconds_in_range(self) -> None:
        tw = TimeWindow(min_sec=5, max_sec=25)
        assert tw.contains(15) is True

    def test_contains_returns_true_at_min_boundary(self) -> None:
        tw = TimeWindow(min_sec=5, max_sec=25)
        assert tw.contains(5) is True

    def test_contains_returns_true_at_max_boundary(self) -> None:
        tw = TimeWindow(min_sec=5, max_sec=25)
        assert tw.contains(25) is True

    def test_contains_returns_false_when_above_max(self) -> None:
        tw = TimeWindow(min_sec=5, max_sec=25)
        assert tw.contains(26) is False

    def test_contains_returns_false_when_below_min(self) -> None:
        tw = TimeWindow(min_sec=5, max_sec=25)
        assert tw.contains(4) is False

    def test_raises_when_min_greater_than_max(self) -> None:
        with pytest.raises(ValueError, match="min_sec"):
            TimeWindow(min_sec=30, max_sec=10)

    def test_accepts_equal_min_and_max(self) -> None:
        tw = TimeWindow(min_sec=10, max_sec=10)
        assert tw.contains(10) is True

    def test_is_frozen_dataclass(self) -> None:
        tw = TimeWindow(min_sec=5, max_sec=25)
        with pytest.raises((AttributeError, TypeError)):
            tw.min_sec = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# StrategyParams
# ---------------------------------------------------------------------------

class TestStrategyParams:
    def _default(self, **overrides: object) -> StrategyParams:
        defaults: dict = {
            "entry_window": TimeWindow(min_sec=5, max_sec=25),
            "min_dtt": 10.0,
            "min_gain_usd": 0.75,
            "position_size_usd": 10.0,
            "snapshot_interval_ms": 1000,
            "logging_window_buffer_sec": 10,
        }
        defaults.update(overrides)
        return StrategyParams(**defaults)

    def test_creates_with_valid_params(self) -> None:
        sp = self._default()
        assert sp.min_dtt == 10.0
        assert sp.position_size_usd == 10.0

    def test_logging_window_max_returns_entry_max_plus_buffer(self) -> None:
        sp = self._default()
        assert sp.logging_window_max_sec == 35

    def test_raises_when_min_dtt_negative(self) -> None:
        with pytest.raises(ValueError, match="min_dtt"):
            self._default(min_dtt=-1.0)

    def test_raises_when_position_size_zero(self) -> None:
        with pytest.raises(ValueError, match="position_size_usd"):
            self._default(position_size_usd=0.0)

    def test_raises_when_position_size_negative(self) -> None:
        with pytest.raises(ValueError, match="position_size_usd"):
            self._default(position_size_usd=-5.0)

    def test_raises_when_snapshot_interval_zero(self) -> None:
        with pytest.raises(ValueError, match="snapshot_interval_ms"):
            self._default(snapshot_interval_ms=0)

    def test_raises_when_min_gain_negative(self) -> None:
        with pytest.raises(ValueError, match="min_gain_usd"):
            self._default(min_gain_usd=-0.1)

    def test_is_frozen_dataclass(self) -> None:
        sp = self._default()
        with pytest.raises((AttributeError, TypeError)):
            sp.min_dtt = 99.0  # type: ignore[misc]
