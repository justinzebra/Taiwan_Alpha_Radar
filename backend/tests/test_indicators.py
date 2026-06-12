"""Unit tests for technical indicators."""
from app.alpha.indicators import (
    clamp,
    max_drawdown_pct,
    momentum_pct,
    rsi,
    sma,
)


def test_sma_returns_none_when_insufficient_data():
    assert sma([1, 2], 5) is None


def test_sma_computes_average_of_last_period():
    # Arrange / Act
    result = sma([1, 2, 3, 4, 5], 3)
    # Assert (4+5+3)/3 -> last 3 = 3,4,5 = 4
    assert result == 4.0


def test_momentum_pct_positive_trend():
    values = [100, 101, 102, 103, 104, 110]
    assert round(momentum_pct(values, 5), 6) == 10.0


def test_rsi_all_gains_returns_100():
    values = list(range(1, 30))
    assert rsi(values, 14) == 100.0


def test_rsi_within_bounds_for_mixed_series():
    values = [10, 11, 10.5, 12, 11.5, 13, 12.5, 14, 13.5, 15, 14, 16, 15.5, 17, 16]
    value = rsi(values, 14)
    assert value is not None
    assert 0 <= value <= 100


def test_max_drawdown_detects_peak_to_trough():
    values = [100, 120, 90, 95]
    # peak 120 -> trough 90 = 25%
    assert round(max_drawdown_pct(values, 60), 1) == 25.0


def test_clamp_bounds():
    assert clamp(150) == 100
    assert clamp(-5) == 0
    assert clamp(42) == 42
