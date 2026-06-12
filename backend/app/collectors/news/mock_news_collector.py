"""Mock news/theme collector."""
from __future__ import annotations

from datetime import date

from app.collectors.base import NewsCollector
from app.domain.simulator import NewsItem, simulate_news
from app.domain.universe import get_stock


class MockNewsCollector(NewsCollector):
    def fetch_news(self, stock_id: str, day: date) -> list[NewsItem]:
        meta = get_stock(stock_id)
        if meta is None:
            return []
        return simulate_news(meta, day)
