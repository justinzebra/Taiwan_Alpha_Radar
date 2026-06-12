"""OpenAI-backed report provider.

Falls back to the mock provider on any error (missing key, network, malformed
JSON) so report generation never hard-fails the pipeline.
"""
from __future__ import annotations

import json
import logging

from app.ai.base import AIProvider, ReportInput, ReportOutput
from app.ai.mock_provider import MockAIProvider
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self) -> None:
        self._fallback = MockAIProvider()

    def generate_report(self, data: ReportInput) -> ReportOutput:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set; using mock provider.")
            return self._fallback.generate_report(data)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(data)},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            raw = resp.choices[0].message.content or "{}"
            return _parse(raw, self.name, data, self._fallback)
        except Exception as exc:  # noqa: BLE001 - provider must never crash pipeline
            logger.exception("OpenAI report generation failed: %s", exc)
            return self._fallback.generate_report(data)


def _parse(
    raw: str, provider: str, data: ReportInput, fallback: AIProvider
) -> ReportOutput:
    try:
        parsed = json.loads(raw)
        return ReportOutput(
            provider=provider,
            summary=parsed.get("summary", ""),
            highlights=list(parsed.get("highlights", [])),
            risks=list(parsed.get("risks", [])),
            short_term=parsed.get("short_term", ""),
            mid_term=parsed.get("mid_term", ""),
        )
    except (json.JSONDecodeError, TypeError):
        return fallback.generate_report(data)
