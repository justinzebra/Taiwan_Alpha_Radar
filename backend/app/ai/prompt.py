"""Shared prompt construction for LLM providers."""
from __future__ import annotations

import json

from app.ai.base import ReportInput

SYSTEM_PROMPT = (
    "你是一位專業的台股投資分析師。根據提供的量化評分結果，撰寫客觀、"
    "精簡、具可操作性的投資分析。不得提供保證獲利的說法，需平衡呈現機會與風險。"
    "務必只回傳合法 JSON，不要加上任何說明文字或 markdown 圍欄。"
)

JSON_SCHEMA_HINT = {
    "summary": "一段 2-3 句的總結",
    "highlights": ["投資亮點1", "投資亮點2"],
    "risks": ["風險提醒1", "風險提醒2"],
    "short_term": "短期(1-4週)觀察重點",
    "mid_term": "中期(1-3月)觀察重點",
}


def build_user_prompt(data: ReportInput) -> str:
    payload = {
        "股票": f"{data.name} ({data.stock_id})",
        "題材": data.theme,
        "AlphaScore": data.total_score,
        "建議": data.recommendation,
        "收盤": data.last_close,
        "漲跌幅%": data.change_pct,
        "各維度評分": [
            {
                "維度": d["label"],
                "分數": d["score"],
                "理由": d["reasons"],
            }
            for d in data.dimensions
        ],
    }
    return (
        "以下是某檔台股的量化分析結果，請據此產生投資報告。\n\n"
        f"分析資料：\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        f"請嚴格以下列 JSON 結構回傳（值需為繁體中文）：\n"
        f"{json.dumps(JSON_SCHEMA_HINT, ensure_ascii=False, indent=2)}"
    )
