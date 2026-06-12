"""Mock fundamental/financial collector."""
from __future__ import annotations

from app.collectors.base import FinancialCollector
from app.domain.simulator import Fundamentals, simulate_fundamentals
from app.domain.universe import get_stock


class MockFinancialCollector(FinancialCollector):
    def fetch_fundamentals(self, stock_id: str, ref_price: float) -> Fundamentals:
        meta = get_stock(stock_id)
        if meta is None:
            return Fundamentals(0, 0, 0, 0, 0, 0, 0)
        return simulate_fundamentals(meta, ref_price)
