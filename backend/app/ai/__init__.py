"""AI package — report engine + provider factory."""
from __future__ import annotations

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.base import AIProvider
from app.ai.mock_provider import MockAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.report_engine import ReportEngine
from app.config import settings


def get_ai_provider(provider: str | None = None) -> AIProvider:
    """Factory selecting the active LLM provider from config."""
    name = (provider or settings.ai_provider).lower()
    if name == "openai":
        return OpenAIProvider()
    if name == "anthropic":
        return AnthropicProvider()
    return MockAIProvider()


def get_report_engine(provider: str | None = None) -> ReportEngine:
    return ReportEngine(get_ai_provider(provider))


__all__ = ["get_ai_provider", "get_report_engine", "ReportEngine", "AIProvider"]
