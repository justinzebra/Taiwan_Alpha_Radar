"""Mock institutional/chip collector."""
from __future__ import annotations

from datetime import date

from app.collectors.base import InstitutionalCollector
from app.domain.simulator import InstitutionalFlow, simulate_institutional
from app.domain.universe import get_stock


class MockInstitutionalCollector(InstitutionalCollector):
    def fetch_flow(self, stock_id: str, day: date) -> InstitutionalFlow:
        meta = get_stock(stock_id)
        if meta is None:
            return InstitutionalFlow(0, 0, 0, 0.0, 0.0)
        return simulate_institutional(meta, day)
