"""基本面 — Fundamental dimension (weight 20%).

Scores valuation (PE/PB), profitability (ROE/margin) and growth (revenue YoY).
"""
from __future__ import annotations

from app.alpha.base import DimensionResult, DimensionScorer, StockContext


class FundamentalDimension(DimensionScorer):
    key = "fundamental"
    label = "基本面"
    weight = 0.20

    def score(self, ctx: StockContext) -> DimensionResult:
        f = ctx.fundamentals
        reasons: list[str] = []
        metrics = {
            "eps_ttm": f.eps_ttm,
            "pe": f.pe_ratio,
            "pb": f.pb_ratio,
            "roe_pct": f.roe_pct,
            "yield_pct": f.yield_pct,
            "revenue_yoy_pct": f.revenue_yoy_pct,
            "gross_margin_pct": f.gross_margin_pct,
        }

        score = 50.0

        # Profitability.
        if f.roe_pct >= 20:
            score += 14
            reasons.append(f"ROE 優異（{f.roe_pct:.0f}%）")
        elif f.roe_pct >= 12:
            score += 6
            reasons.append(f"ROE 穩健（{f.roe_pct:.0f}%）")
        elif f.roe_pct < 6:
            score -= 8
            reasons.append("ROE 偏低，獲利能力不足")

        # Growth.
        if f.revenue_yoy_pct >= 20:
            score += 12
            reasons.append(f"營收年增強勁（+{f.revenue_yoy_pct:.0f}%）")
        elif f.revenue_yoy_pct < 0:
            score -= 8
            reasons.append(f"營收年減（{f.revenue_yoy_pct:.0f}%）")

        # Valuation (penalise extreme PE, reward reasonable).
        if 0 < f.pe_ratio <= 15:
            score += 8
            reasons.append("本益比偏低，評價具吸引力")
        elif f.pe_ratio > 40:
            score -= 8
            reasons.append("本益比偏高，評價已反映期待")

        # Margin quality.
        if f.gross_margin_pct >= 40:
            score += 5
            reasons.append("毛利率高，產品競爭力強")

        # Dividend support.
        if f.yield_pct >= 4:
            score += 3
            reasons.append(f"殖利率佳（{f.yield_pct:.1f}%）")

        if not reasons:
            reasons.append("基本面中性")
        return self._result(score, reasons, metrics)
