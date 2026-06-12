"""技術面 — Technical dimension (weight 30%).

Blends trend (price vs moving averages), momentum, RSI positioning and volume
confirmation into a 0-100 score.
"""
from __future__ import annotations

from app.alpha.base import DimensionResult, DimensionScorer, StockContext
from app.alpha.indicators import momentum_pct, rsi, sma


class TechnicalDimension(DimensionScorer):
    key = "technical"
    label = "技術面"
    weight = 0.30

    def score(self, ctx: StockContext) -> DimensionResult:
        closes = ctx.closes
        reasons: list[str] = []
        metrics: dict = {}
        if len(closes) < 25:
            return self._result(50.0, ["資料不足，給予中性分數"], {})

        last = closes[-1]
        ma5 = sma(closes, 5)
        ma20 = sma(closes, 20)
        ma60 = sma(closes, 60) or sma(closes, len(closes) - 1)
        mom20 = momentum_pct(closes, 20) or 0.0
        rsi14 = rsi(closes, 14) or 50.0

        metrics = {
            "close": round(last, 2),
            "ma5": round(ma5, 2) if ma5 else None,
            "ma20": round(ma20, 2) if ma20 else None,
            "ma60": round(ma60, 2) if ma60 else None,
            "momentum_20d_pct": round(mom20, 2),
            "rsi14": round(rsi14, 1),
        }

        score = 50.0

        # Trend structure: bullish stacking of MAs.
        if ma5 and ma20 and ma60:
            if last > ma5 > ma20 > ma60:
                score += 18
                reasons.append("均線多頭排列，趨勢向上")
            elif last < ma5 < ma20 < ma60:
                score -= 18
                reasons.append("均線空頭排列，趨勢轉弱")
            elif last > ma20:
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
        vols = [c.volume for c in ctx.candles]
        if len(vols) >= 21:
            v_avg = sum(vols[-21:-1]) / 20
            if v_avg and vols[-1] > v_avg * 1.3 and closes[-1] > closes[-2]:
                score += 6
                reasons.append("帶量上漲，量價配合")

        return self._result(score, reasons, metrics)
