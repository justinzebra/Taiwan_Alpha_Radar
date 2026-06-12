"""風險面 — Risk dimension (weight 10%).

Higher score = lower risk (safer). Penalises high volatility, deep drawdowns and
overbought stretches so the composite favours sustainable setups.
"""
from __future__ import annotations

from app.alpha.base import DimensionResult, DimensionScorer, StockContext
from app.alpha.indicators import annualized_volatility, max_drawdown_pct, rsi


class RiskDimension(DimensionScorer):
    key = "risk"
    label = "風險面"
    weight = 0.10

    def score(self, ctx: StockContext) -> DimensionResult:
        closes = ctx.closes
        reasons: list[str] = []
        if len(closes) < 25:
            return self._result(50.0, ["資料不足，給予中性風險分數"], {})

        vol = annualized_volatility(closes, 20) or 30.0
        mdd = max_drawdown_pct(closes, 60)
        rsi14 = rsi(closes, 14) or 50.0

        metrics = {
            "annualized_vol_pct": round(vol, 1),
            "max_drawdown_60d_pct": round(mdd, 1),
            "rsi14": round(rsi14, 1),
        }

        # Start high (safe) and subtract for each risk factor.
        score = 80.0

        if vol > 60:
            score -= 25
            reasons.append(f"波動度偏高（年化 {vol:.0f}%）")
        elif vol > 40:
            score -= 12
            reasons.append(f"波動度中等（年化 {vol:.0f}%）")
        else:
            reasons.append(f"波動度可控（年化 {vol:.0f}%）")

        if mdd > 25:
            score -= 18
            reasons.append(f"近期最大回檔大（{mdd:.0f}%）")
        elif mdd > 15:
            score -= 8
            reasons.append(f"近期回檔中等（{mdd:.0f}%）")

        if rsi14 > 80:
            score -= 8
            reasons.append("短線過熱，追高風險升高")

        return self._result(score, reasons, metrics)
