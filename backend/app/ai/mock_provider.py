"""Deterministic mock AI provider.

Generates a coherent report directly from the score breakdown with no external
API. This keeps the whole platform runnable out-of-the-box (``docker compose up``
with no API key) and serves as the fallback when a real provider errors.
"""
from __future__ import annotations

from app.ai.base import AIProvider, ReportInput, ReportOutput


def _sorted_dims(dims: list[dict], reverse: bool) -> list[dict]:
    return sorted(dims, key=lambda d: d["score"], reverse=reverse)


class MockAIProvider(AIProvider):
    name = "mock"

    def generate_report(self, data: ReportInput) -> ReportOutput:
        dims = data.dimensions
        strongest = _sorted_dims(dims, reverse=True)[:2]
        weakest = _sorted_dims(dims, reverse=False)[:2]

        highlights = []
        for d in strongest:
            top_reason = d["reasons"][0] if d["reasons"] else f"{d['label']}表現突出"
            highlights.append(f"{d['label']}（{d['score']:.0f} 分）：{top_reason}")

        risks = []
        for d in weakest:
            top_reason = d["reasons"][0] if d["reasons"] else f"{d['label']}相對較弱"
            risks.append(f"{d['label']}（{d['score']:.0f} 分）：{top_reason}")

        risk_dim = next((d for d in dims if d["key"] == "risk"), None)
        if risk_dim and risk_dim["score"] < 50:
            risks.append("波動與回檔風險偏高，建議控制單一持股部位。")

        direction = (
            "偏多看待，可逢拉回分批布局"
            if data.total_score >= 60
            else "中性看待，建議觀察量能與法人動向"
            if data.total_score >= 45
            else "偏空看待，暫不宜追價"
        )

        summary = (
            f"{data.name}（{data.stock_id}）目前 Alpha Score 為 {data.total_score:.0f} 分，"
            f"綜合評等「{data.recommendation}」。所屬{data.theme}題材，{direction}。"
        )

        short_term = (
            f"短期關注 {strongest[0]['label']} 是否延續強勢，"
            f"以及 {data.change_pct:+.1f}% 後的量價變化；"
            "跌破關鍵均線需減碼。"
        )
        mid_term = (
            f"中期觀察題材{data.theme}的基本面兌現程度與法人持續性，"
            "評分若維持 65 分以上可續抱。"
        )

        return ReportOutput(
            provider=self.name,
            summary=summary,
            highlights=highlights,
            risks=risks,
            short_term=short_term,
            mid_term=mid_term,
        )
