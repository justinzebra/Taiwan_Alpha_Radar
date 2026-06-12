"""Alpha-engine core contracts (Strategy Pattern).

Every scoring dimension implements ``DimensionScorer``. The composite engine is
agnostic to how many dimensions exist or what they measure — it only knows their
weights. Adding a new dimension (e.g. ESG, options-flow) means writing one class
and registering it, with no change to the engine or the API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from app.domain.simulator import Candle, Fundamentals, InstitutionalFlow, NewsItem
from app.domain.universe import StockMeta


@dataclass(frozen=True)
class StockContext:
    """All inputs a dimension may need to score one stock on one date."""

    meta: StockMeta
    as_of: date
    candles: list[Candle]
    flow: InstitutionalFlow
    fundamentals: Fundamentals
    news: list[NewsItem]

    @property
    def closes(self) -> list[float]:
        return [c.close for c in self.candles]

    @property
    def last_close(self) -> float:
        return self.candles[-1].close if self.candles else 0.0


@dataclass
class DimensionResult:
    """Output of a single dimension scorer."""

    key: str
    label: str
    score: float                       # 0-100
    weight: float                      # 0-1, contribution to composite
    reasons: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "score": round(self.score, 1),
            "weight": self.weight,
            "weighted": round(self.score * self.weight, 2),
            "reasons": self.reasons,
            "metrics": self.metrics,
        }


class DimensionScorer(ABC):
    """Strategy interface for one scoring dimension."""

    key: str
    label: str
    weight: float  # 0-1

    @abstractmethod
    def score(self, ctx: StockContext) -> DimensionResult:
        ...

    def _result(
        self, score: float, reasons: list[str], metrics: dict
    ) -> DimensionResult:
        return DimensionResult(
            key=self.key,
            label=self.label,
            score=max(0.0, min(100.0, score)),
            weight=self.weight,
            reasons=reasons,
            metrics=metrics,
        )
