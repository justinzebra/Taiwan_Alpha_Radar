"""Collector registry.

Returns the active set of collectors based on configuration. Today everything
is the mock provider; flipping to a real feed is a one-line change here once a
real collector is implemented.
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
from app.collectors.market.mock_price_collector import MockPriceCollector
from app.collectors.news.mock_news_collector import MockNewsCollector


@dataclass(frozen=True)
class CollectorBundle:
    """The full set of data sources the pipeline needs."""

    price: PriceCollector
    institutional: InstitutionalCollector
    financial: FinancialCollector
    news: NewsCollector


def get_collectors(provider: str = "mock") -> CollectorBundle:
    """Factory for the active collector bundle.

    To add a real feed: implement the four ABCs and branch on ``provider`` here.
    """
    if provider == "mock":
        return CollectorBundle(
            price=MockPriceCollector(),
            institutional=MockInstitutionalCollector(),
            financial=MockFinancialCollector(),
            news=MockNewsCollector(),
        )
    raise ValueError(f"Unknown data provider: {provider!r}")
