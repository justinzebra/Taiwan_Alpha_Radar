"""Collector registry.

Returns the active set of collectors based on configuration. The default mock
bundle is still useful for offline demos; ``official_close`` uses official
TWSE/TPEx close prices and end-of-day institutional flows.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.collectors.base import (
    FinancialCollector,
    InstitutionalCollector,
    NewsCollector,
    PriceCollector,
)
from app.collectors.financial.mock_financial_collector import MockFinancialCollector
from app.collectors.institutional.mock_institutional_collector import (
    MockInstitutionalCollector,
)
from app.collectors.institutional.official_institutional_collector import (
    OfficialInstitutionalCollector,
)
from app.collectors.market.mock_price_collector import MockPriceCollector
from app.collectors.market.official_close_collector import OfficialClosePriceCollector
from app.collectors.news.mock_news_collector import MockNewsCollector


@dataclass(frozen=True)
class CollectorBundle:
    """The full set of data sources the pipeline needs."""

    price: PriceCollector
    institutional: InstitutionalCollector
    financial: FinancialCollector
    news: NewsCollector
    price_source: str = "mock"
    other_sources: str = "mock"


def get_collectors(provider: str = "mock") -> CollectorBundle:
    """Factory for the active collector bundle.

    To add another real feed: implement the ABCs and branch on ``provider`` here.
    """
    if provider == "mock":
        return CollectorBundle(
            price=MockPriceCollector(),
            institutional=MockInstitutionalCollector(),
            financial=MockFinancialCollector(),
            news=MockNewsCollector(),
            price_source="mock",
            other_sources="mock",
        )
    if provider == "official_close":
        return CollectorBundle(
            price=OfficialClosePriceCollector(),
            institutional=OfficialInstitutionalCollector(),
            financial=MockFinancialCollector(),
            news=MockNewsCollector(),
            price_source="twse_tpex_official",
            other_sources="institutional:twse_tpex_official; financial/news:mock",
        )
    raise ValueError(f"Unknown data provider: {provider!r}")
