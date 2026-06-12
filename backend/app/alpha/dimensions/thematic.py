"""題材面 — Thematic / catalyst dimension (weight 15%).

Scores how strongly a stock rides a hot market theme, using news sentiment plus
a theme heat prior. Theme heat is data-driven at the engine level (passed in via
context metric) but falls back to a static prior here for single-stock scoring.
"""
from __future__ import annotations

from app.alpha.base import DimensionResult, DimensionScorer, StockContext

# Static heat prior for themes (0-1). The sector engine can override these with
# live relative strength, but this keeps single-stock scoring self-contained.
_THEME_HEAT = {
    "AI": 0.95,
    "光通訊": 0.85,
    "散熱": 0.80,
    "機器人": 0.78,
    "半導體": 0.70,
    "電動車": 0.55,
    "金融": 0.45,
    "傳產": 0.40,
}


class ThematicDimension(DimensionScorer):
    key = "thematic"
    label = "題材面"
    weight = 0.15

    def score(self, ctx: StockContext) -> DimensionResult:
        reasons: list[str] = []
        heat = _THEME_HEAT.get(ctx.meta.theme, 0.5)

        news_sentiment = (
            sum(n.sentiment for n in ctx.news) / len(ctx.news)
            if ctx.news
            else 0.0
        )

        metrics = {
            "theme": ctx.meta.theme,
            "theme_heat": heat,
            "news_count": len(ctx.news),
            "news_sentiment": round(news_sentiment, 2),
        }

        # Base from theme heat (40-90).
        score = 40 + heat * 50
        if heat >= 0.8:
            reasons.append(f"{ctx.meta.theme} 為當前市場主流題材")
        elif heat <= 0.45:
            reasons.append(f"{ctx.meta.theme} 題材熱度偏低")

        # News sentiment adjustment.
        score += news_sentiment * 12
        if news_sentiment > 0.4:
            reasons.append("近期利多消息密集")
        elif news_sentiment < 0:
            reasons.append("近期消息面偏空")

        if ctx.news:
            reasons.append(f"代表性題材：{ctx.news[0].title.split('）')[-1]}")

        return self._result(score, reasons, metrics)
