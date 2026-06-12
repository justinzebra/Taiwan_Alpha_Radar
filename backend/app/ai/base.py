"""AI provider contracts (Provider Pattern).

The report engine depends only on ``AIProvider``. Concrete providers (OpenAI,
Anthropic, mock) are interchangeable and selected by config, so switching LLM
vendors never touches the engine or the API layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ReportInput:
    """Structured analysis fed to the LLM to generate a report."""

    stock_id: str
    name: str
    theme: str
    total_score: float
    recommendation: str
    last_close: float
    change_pct: float
    dimensions: list[dict] = field(default_factory=list)  # DimensionResult.as_dict()


@dataclass
class ReportOutput:
    """Structured report returned to the API / persisted to DB."""

    provider: str
    summary: str
    highlights: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    short_term: str = ""
    mid_term: str = ""

    def sections(self) -> dict:
        return {
            "highlights": self.highlights,
            "risks": self.risks,
            "short_term": self.short_term,
            "mid_term": self.mid_term,
        }


class AIProvider(ABC):
    """Interface every LLM backend implements."""

    name: str

    @abstractmethod
    def generate_report(self, data: ReportInput) -> ReportOutput:
        ...
