"""市場評分 — Market temperature engine.

Produces the 0-100 market temperature from breadth (advancers/decliners),
index trend/strength, and the distribution of stock alpha scores. This is what
drives the dashboard gauge (極度看空 ... 極度看多).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.alpha.indicators import momentum_pct, sma
from app.alpha.stock_score import StockScoreResult
from app.collectors import CollectorBundle
from app.domain.universe import INDICES


def sentiment_label(score: float) -> str:
    if score >= 80:
        return "極度看多"
    if score >= 60:
        return "偏多"
    if score >= 40:
        return "中性"
    if score >= 20:
        return "偏空"
    return "極度看空"


def risk_label(score: float, breadth: float) -> str:
    # High temperature with thin breadth, or very low temperature, => higher risk.
    if score >= 80 or score <= 25:
        return "高"
    if 45 <= score <= 70 and breadth >= 0.45:
        return "低"
    return "中"


@dataclass
class IndexSnapshot:
    index_id: str
    name: str
    value: float
    change_pct: float
    trend: str
    strength: float
    volume_billion: float


@dataclass
class MarketScoreResult:
    as_of: date
    temperature_score: float
    sentiment: str
    advancers: int
    decliners: int
    total_volume_billion: float
    risk_level: str
    indices: list[IndexSnapshot] = field(default_factory=list)
    notes: dict = field(default_factory=dict)


def _index_snapshot(collectors: CollectorBundle, spec: dict, as_of: date) -> IndexSnapshot:
    candles = collectors.price.fetch_index(spec["index_id"], as_of, 80)
    closes = [c.close for c in candles]
    last = candles[-1]
    ma20 = sma(closes, 20) or last.close
    mom20 = momentum_pct(closes, 20) or 0.0
    trend = "上升" if last.close > ma20 else "下降"
    # Strength 0-100 from how far above/below MA20 + momentum.
    strength = max(0.0, min(100.0, 50 + (last.close / ma20 - 1) * 600 + mom20 * 1.5))
    return IndexSnapshot(
        index_id=spec["index_id"],
        name=spec["name"],
        value=round(last.close, 2),
        change_pct=last.change_pct,
        trend=trend,
        strength=round(strength, 1),
        volume_billion=round(last.volume / 1_000_000_000, 1),
    )


def compute_market_score(
    collectors: CollectorBundle,
    stock_scores: list[StockScoreResult],
    as_of: date,
) -> MarketScoreResult:
    advancers = sum(1 for s in stock_scores if s.change_pct > 0)
    decliners = sum(1 for s in stock_scores if s.change_pct < 0)
    total = len(stock_scores) or 1
    breadth = advancers / total

    indices = [_index_snapshot(collectors, spec, as_of) for spec in INDICES]
    index_strength = sum(i.strength for i in indices) / len(indices) if indices else 50

    avg_alpha = sum(s.total_score for s in stock_scores) / total

    # Temperature blends breadth (40%), index strength (35%), avg alpha (25%).
    temperature = (
        breadth * 100 * 0.40
        + index_strength * 0.35
        + avg_alpha * 0.25
    )
    temperature = round(max(0.0, min(100.0, temperature)), 1)

    total_volume = round(
        sum(i.volume_billion for i in indices)
        + sum(
            (s.last_close for s in stock_scores), 0.0
        ) / 1000,
        1,
    )

    notes = {
        "breadth_pct": round(breadth * 100, 1),
        "avg_alpha": round(avg_alpha, 1),
        "index_strength": round(index_strength, 1),
        "comment": _market_comment(temperature, breadth),
    }

    return MarketScoreResult(
        as_of=as_of,
        temperature_score=temperature,
        sentiment=sentiment_label(temperature),
        advancers=advancers,
        decliners=decliners,
        total_volume_billion=total_volume,
        risk_level=risk_label(temperature, breadth),
        indices=indices,
        notes=notes,
    )


def _market_comment(temperature: float, breadth: float) -> str:
    label = sentiment_label(temperature)
    if temperature >= 70:
        return f"市場情緒{label}，資金動能充沛，留意追高風險與量能是否持續。"
    if temperature >= 45:
        return f"市場情緒{label}，多空交戰，宜選股不選市、聚焦強勢族群。"
    return f"市場情緒{label}，賣壓沉重，建議降低持股、等待量縮止穩。"
