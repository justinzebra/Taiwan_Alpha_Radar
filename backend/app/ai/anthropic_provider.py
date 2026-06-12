"""Anthropic-backed report provider.

Mirrors the OpenAI provider's contract and fallback behaviour so the two are
fully interchangeable via the ``AI_PROVIDER`` setting.
"""
from __future__ import annotations

import logging

from app.ai.base import AIProvider, ReportInput, ReportOutput
from app.ai.mock_provider import MockAIProvider
from app.ai.openai_provider import _parse
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.config import settings

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self) -> None:
        self._fallback = MockAIProvider()

    def generate_report(self, data: ReportInput) -> ReportOutput:
        if not settings.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not set; using mock provider.")
            return self._fallback.generate_report(data)
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(data)}],
            )
            raw = "".join(
                block.text for block in msg.content if block.type == "text"
            ) or "{}"
            return _parse(raw, self.name, data, self._fallback)
        except Exception as exc:  # noqa: BLE001 - provider must never crash pipeline
            logger.exception("Anthropic report generation failed: %s", exc)
            return self._fallback.generate_report(data)
