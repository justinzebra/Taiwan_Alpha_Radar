"""Reusable technical features for end-of-day prediction models."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from app.alpha.indicators import momentum_pct, rsi, sma


def _value(item: Any, key: str) -> Any:
    if isinstance(item, Mapping):
        return item[key]
    return getattr(item, key)


def _closes(prices: Sequence[Any]) -> list[float]:
    return [float(_value(price, "close")) for price in prices]


def _volumes(prices: Sequence[Any]) -> list[float]:
    return [float(_value(price, "volume")) for price in prices]


def _dates(prices: Sequence[Any]) -> list[date]:
    return [_value(price, "trade_date") for price in prices]


def calculate_ma_state(prices: Sequence[Any]) -> dict[str, float | str | None]:
    closes = _closes(prices)
    if not closes:
        return {
            "close": None,
            "ma5": None,
            "ma20": None,
            "ma60": None,
            "state": "unknown",
        }

    last = closes[-1]
    ma5 = sma(closes, 5)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60) or (
        sma(closes, len(closes) - 1) if len(closes) > 1 else None
    )
    state = "mixed"
    if ma5 and ma20 and ma60:
        if last > ma5 > ma20 > ma60:
            state = "bull_stack"
        elif last < ma5 < ma20 < ma60:
            state = "bear_stack"
        elif last > ma20:
            state = "above_ma20"
        else:
            state = "below_ma20"
    return {
        "close": last,
        "ma5": ma5,
        "ma20": ma20,
        "ma60": ma60,
        "state": state,
    }


def calculate_momentum_20d(prices: Sequence[Any]) -> float:
    return momentum_pct(_closes(prices), 20) or 0.0


def calculate_rsi_14(prices: Sequence[Any]) -> float:
    return rsi(_closes(prices), 14) or 50.0


def calculate_volume_confirm(prices: Sequence[Any]) -> bool:
    closes = _closes(prices)
    volumes = _volumes(prices)
    if len(closes) < 2 or len(volumes) < 21:
        return False
    volume_avg_20 = sum(volumes[-21:-1]) / 20
    return bool(volume_avg_20 and volumes[-1] > volume_avg_20 * 1.3 and closes[-1] > closes[-2])


def calculate_market_breadth(
    all_stock_prices_by_date: Mapping[date, Sequence[Any]],
    target_date: date,
) -> float:
    """Share of stocks that closed above their previous close on ``target_date``."""
    up_count = 0
    total = 0
    for prices in all_stock_prices_by_date.values():
        sorted_prices = sorted(prices, key=lambda price: _value(price, "trade_date"))
        dates = _dates(sorted_prices)
        try:
            index = dates.index(target_date)
        except ValueError:
            continue
        if index == 0:
            continue
        previous_close = float(_value(sorted_prices[index - 1], "close"))
        current_close = float(_value(sorted_prices[index], "close"))
        if previous_close <= 0 or current_close <= 0:
            continue
        total += 1
        if current_close > previous_close:
            up_count += 1
    return up_count / total if total else 0.0
