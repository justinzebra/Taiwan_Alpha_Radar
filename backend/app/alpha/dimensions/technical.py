"""技術面 — Technical dimension (weight 30%).

Blends trend (price vs moving averages), momentum, RSI positioning and volume
confirmation into a 0-100 score.
"""
from __future__ import annotations

from app.alpha.base import DimensionResult, DimensionScorer, StockContext
from app.alpha.features.technical_features import (
    calculate_ma_state,
    calculate_momentum_20d,
    calculate_rsi_14,
    calculate_volume_confirm,
)


class TechnicalDimension(DimensionScorer):
    key = "technical"
    label = "技術面"
    weight = 0.30

    def score(self, ctx: StockContext) -> DimensionResult:
        reasons: list[str] = []
        metrics: dict = {}
        if len(ctx.candles) < 25:
            return self._result(50.0, ["資料不足，給予中性分數"], {})

        ma = calculate_ma_state(ctx.candles)
        last = ma["close"]
        ma5 = ma["ma5"]
        ma20 = ma["ma20"]
        ma60 = ma["ma60"]
        mom20 = calculate_momentum_20d(ctx.candles)
        rsi14 = calculate_rsi_14(ctx.candles)

        metrics = {
            "close": round(last, 2),
            "ma5": round(ma5, 2) if ma5 else None,
            "ma20": round(ma20, 2) if ma20 else None,
            "ma60": round(ma60, 2) if ma60 else None,
            "momentum_20d_pct": round(mom20, 2),
            "rsi14": round(rsi14, 1),
            "volume_confirm": calculate_volume_confirm(ctx.candles),
        }

        score = 50.0

        # Trend structure: bullish stacking of MAs.
        if ma5 and ma20 and ma60:
            if ma["state"] == "bull_stack":
                score += 18
                reasons.append("均線多頭排列，趨勢向上")
            elif ma["state"] == "bear_stack":
                score -= 18
                reasons.append("均線空頭排列，趨勢轉弱")
            elif ma["state"] == "above_ma20":
                score += 6
                reasons.append("股價站上月線")
            else:
                score -= 6
                reasons.append("股價跌破月線")

        # Momentum.
        score += max(-15, min(15, mom20 * 0.6))
        if mom20 > 8:
            reasons.append(f"近月動能強勁（+{mom20:.1f}%）")
        elif mom20 < -8:
            reasons.append(f"近月動能轉弱（{mom20:.1f}%）")

        # RSI positioning (reward 50-70 strength, penalise overbought/oversold extremes).
        if 50 <= rsi14 <= 70:
            score += 8
            reasons.append("RSI 位於強勢區間")
        elif rsi14 > 80:
            score -= 6
            reasons.append("RSI 過熱，留意回檔")
        elif rsi14 < 30:
            score -= 4
            reasons.append("RSI 弱勢，買盤不足")

        # Volume confirmation.
        if metrics["volume_confirm"]:
            score += 6
            reasons.append("帶量上漲，量價配合")

        return self._result(score, reasons, metrics)
