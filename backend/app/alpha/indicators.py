"""Pure technical-indicator helpers.

Small, dependency-free functions operating on closing-price lists. Kept pure so
they are trivially unit-testable and reusable across dimensions.
"""
from __future__ import annotations


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def momentum_pct(values: list[float], period: int) -> float | None:
    """Percentage change over the last ``period`` bars."""
    if len(values) <= period or values[-period - 1] == 0:
        return None
    return (values[-1] / values[-period - 1] - 1) * 100


def rsi(values: list[float], period: int = 14) -> float | None:
    """Classic Wilder-style RSI on closing prices."""
    if len(values) <= period:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        delta = values[i] - values[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100 - (100 / (1 + rs))


def annualized_volatility(values: list[float], lookback: int = 20) -> float | None:
    """Annualised stdev of daily returns over ``lookback`` bars, in percent."""
    if len(values) <= lookback:
        return None
    rets = [
        values[i] / values[i - 1] - 1
        for i in range(-lookback, 0)
        if values[i - 1] != 0
    ]
    if not rets:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return (var ** 0.5) * (252 ** 0.5) * 100


def max_drawdown_pct(values: list[float], lookback: int = 60) -> float:
    """Largest peak-to-trough drop over ``lookback`` bars, as a positive percent."""
    window = values[-lookback:] if len(values) > lookback else values
    if not window:
        return 0.0
    peak = window[0]
    mdd = 0.0
    for v in window:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return mdd * 100


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
