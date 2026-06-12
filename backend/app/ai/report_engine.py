"""AI Report Engine.

Bridges the alpha engine and the AI providers: converts a StockScoreResult into
a ReportInput, delegates to the configured provider, and returns a ReportOutput.
"""
from __future__ import annotations

from app.ai.base import AIProvider, ReportInput, ReportOutput
from app.alpha.stock_score import StockScoreResult
from app.domain.universe import get_stock


class ReportEngine:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def generate(self, score: StockScoreResult) -> ReportOutput:
        meta = get_stock(score.stock_id)
        data = ReportInput(
            stock_id=score.stock_id,
            name=score.name,
            theme=meta.theme if meta else "",
            total_score=score.total_score,
            recommendation=score.recommendation,
            last_close=score.last_close,
            change_pct=score.change_pct,
            dimensions=[d.as_dict() for d in score.dimensions],
        )
        return self.provider.generate_report(data)
