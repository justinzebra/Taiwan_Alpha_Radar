"""Composite Alpha Score engine (個股評分).

Builds a StockContext from the collector bundle, runs every registered
dimension, and combines them by weight into a 0-100 Alpha Score with a
recommendation label and full breakdown.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.alpha.base import DimensionResult, StockContext
from app.alpha.dimensions import ALL_DIMENSIONS
from app.collectors import CollectorBundle
from app.config import settings
from app.domain.universe import StockMeta


@dataclass
class StockScoreResult:
    """Full scoring output for one stock."""

    stock_id: str
    name: str
    as_of: date
    total_score: float
    dimensions: list[DimensionResult] = field(default_factory=list)
    recommendation: str = "觀望"
    last_close: float = 0.0
    change_pct: float = 0.0

    def dimension_score(self, key: str) -> float:
        for d in self.dimensions:
            if d.key == key:
                return d.score
        return 0.0

    def breakdown(self) -> dict:
        return {d.key: d.as_dict() for d in self.dimensions}


def _recommendation(total: float) -> str:
    if total >= 80:
        return "強力推薦"
    if total >= 70:
        return "推薦"
    if total >= 55:
        return "區間偏多"
    if total >= 45:
        return "觀望"
    return "偏空"


class StockScoreEngine:
    """Runs the dimension strategies and composes the Alpha Score."""

    def __init__(self, collectors: CollectorBundle, history_days: int | None = None):
        self.collectors = collectors
        self.history_days = history_days or settings.seed_days_of_history
        self.dimensions = ALL_DIMENSIONS

    def build_context(self, meta: StockMeta, as_of: date) -> StockContext | None:
        candles = self.collectors.price.fetch_history(
            meta.stock_id, as_of, self.history_days
        )
        if not candles:
            return None
        ref_price = candles[-1].close
        return StockContext(
            meta=meta,
            as_of=as_of,
            candles=candles,
            flow=self.collectors.institutional.fetch_flow(meta.stock_id, as_of),
            fundamentals=self.collectors.financial.fetch_fundamentals(
                meta.stock_id, ref_price
            ),
            news=self.collectors.news.fetch_news(meta.stock_id, as_of),
        )

    def score(self, meta: StockMeta, as_of: date) -> StockScoreResult | None:
        ctx = self.build_context(meta, as_of)
        if ctx is None:
            return None

        results = [dim.score(ctx) for dim in self.dimensions]
        total = sum(r.score * r.weight for r in results)

        return StockScoreResult(
            stock_id=meta.stock_id,
            name=meta.name,
            as_of=as_of,
            total_score=round(total, 1),
            dimensions=results,
            recommendation=_recommendation(total),
            last_close=ctx.last_close,
            change_pct=ctx.candles[-1].change_pct if ctx.candles else 0.0,
        )
