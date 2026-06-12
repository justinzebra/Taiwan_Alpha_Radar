"""族群評分 — Sector/theme strength engine.

Aggregates individual stock scores into per-theme strength, used by the
dashboard's "今日熱門族群" ranking.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.alpha.stock_score import StockScoreResult


@dataclass
class SectorScoreResult:
    theme: str
    strength_score: float
    avg_change_pct: float
    constituent_count: int
    leaders: list[dict] = field(default_factory=list)
    rank: int = 0


def aggregate_sectors(scores: list[StockScoreResult]) -> list[SectorScoreResult]:
    """Group stock scores by theme and rank themes by blended strength."""
    by_theme: dict[str, list[StockScoreResult]] = defaultdict(list)
    for s in scores:
        from app.domain.universe import get_stock

        meta = get_stock(s.stock_id)
        if meta:
            by_theme[meta.theme].append(s)

    results: list[SectorScoreResult] = []
    for theme, members in by_theme.items():
        if not members:
            continue
        avg_score = sum(m.total_score for m in members) / len(members)
        avg_change = sum(m.change_pct for m in members) / len(members)
        # Strength blends average alpha score with day's momentum.
        strength = round(0.7 * avg_score + 0.3 * (50 + avg_change * 4), 1)
        strength = max(0.0, min(100.0, strength))

        leaders = sorted(members, key=lambda m: m.total_score, reverse=True)[:3]
        results.append(
            SectorScoreResult(
                theme=theme,
                strength_score=strength,
                avg_change_pct=round(avg_change, 2),
                constituent_count=len(members),
                leaders=[
                    {
                        "stock_id": m.stock_id,
                        "name": m.name,
                        "change_pct": m.change_pct,
                        "total_score": m.total_score,
                    }
                    for m in leaders
                ],
            )
        )

    results.sort(key=lambda r: r.strength_score, reverse=True)
    for i, r in enumerate(results, start=1):
        r.rank = i
    return results
