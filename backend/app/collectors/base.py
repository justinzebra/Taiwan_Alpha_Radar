"""Collector interfaces (data-source contract).

Each collector type defines the contract the rest of the system relies on.
Swapping the mock data for a real feed (TWSE OpenAPI, broker API, FinMind, ...)
means writing a new implementation of these ABCs and registering it — no caller
changes required.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.domain.simulator import (
    Candle,
    Fundamentals,
    InstitutionalFlow,
    NewsItem,
)


class PriceCollector(ABC):
    """Source of OHLCV history and index data."""

    @abstractmethod
    def fetch_history(self, stock_id: str, end: date, days: int) -> list[Candle]:
        ...

    @abstractmethod
    def fetch_index(self, index_id: str, end: date, days: int) -> list[Candle]:
        ...


class InstitutionalCollector(ABC):
    """Source of three-major-institutions / margin (籌碼) data."""

    @abstractmethod
    def fetch_flow(self, stock_id: str, day: date) -> InstitutionalFlow:
        ...


class FinancialCollector(ABC):
    """Source of fundamental financials (基本面)."""

    @abstractmethod
    def fetch_fundamentals(self, stock_id: str, ref_price: float) -> Fundamentals:
        ...


class NewsCollector(ABC):
    """Source of news / theme catalysts (題材面)."""

    @abstractmethod
    def fetch_news(self, stock_id: str, day: date) -> list[NewsItem]:
        ...
