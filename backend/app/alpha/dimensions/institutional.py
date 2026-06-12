"""籌碼面 — Institutional / chip dimension (weight 25%).

Scores three-major-institutions net flow, foreign holding and margin trends.
"""
from __future__ import annotations

from app.alpha.base import DimensionResult, DimensionScorer, StockContext


class InstitutionalDimension(DimensionScorer):
    key = "institutional"
    label = "籌碼面"
    weight = 0.25

    def score(self, ctx: StockContext) -> DimensionResult:
        flow = ctx.flow
        reasons: list[str] = []
        net_total = flow.foreign_net + flow.trust_net + flow.dealer_net
        # Normalise net flow against the stock's typical liquidity.
        avg_vol = (
            sum(c.volume for c in ctx.candles[-5:]) / 5 / 1000
            if ctx.candles
            else 1.0
        ) or 1.0
        intensity = net_total / avg_vol  # net (k shares) vs avg vol (k shares)

        metrics = {
            "foreign_net_k": flow.foreign_net,
            "trust_net_k": flow.trust_net,
            "dealer_net_k": flow.dealer_net,
            "foreign_hold_pct": flow.foreign_hold_pct,
            "margin_change_pct": flow.margin_balance_change_pct,
        }

        score = 50.0
        score += max(-22, min(22, intensity * 12))

        if flow.foreign_net > 0 and flow.trust_net > 0:
            score += 10
            reasons.append("外資、投信同步買超，籌碼集中")
        elif flow.foreign_net < 0 and flow.trust_net < 0:
            score -= 10
            reasons.append("外資、投信同步賣超，籌碼鬆動")
        elif flow.foreign_net > 0:
            reasons.append("外資偏多布局")
        elif flow.foreign_net < 0:
            reasons.append("外資調節持股")

        if flow.foreign_hold_pct > 50:
            score += 4
            reasons.append(f"外資持股偏高（{flow.foreign_hold_pct:.0f}%）")

        # Rising margin balance on a falling stock = weak hands risk.
        if flow.margin_balance_change_pct > 4:
            score -= 5
            reasons.append("融資增幅偏大，散戶追高")
        elif flow.margin_balance_change_pct < -4:
            score += 3
            reasons.append("融資退場，浮額清洗")

        if not reasons:
            reasons.append("法人動向中性")
        return self._result(score, reasons, metrics)
