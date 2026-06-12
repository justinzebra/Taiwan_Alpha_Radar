"""Mock price collector backed by the deterministic simulator."""
from __future__ import annotations

from datetime import date

from app.collectors.base import PriceCollector
from app.domain.simulator import Candle, simulate_prices, trading_days
from app.domain.universe import INDICES, StockMeta, get_stock


class MockPriceCollector(PriceCollector):
    """Generates reproducible OHLCV from the universe anchors."""

    def fetch_history(self, stock_id: str, end: date, days: int) -> list[Candle]:
        meta = get_stock(stock_id)
        if meta is None:
            return []
        return simulate_prices(meta, end, days)

    def fetch_index(self, index_id: str, end: date, days: int) -> list[Candle]:
        spec = next((i for i in INDICES if i["index_id"] == index_id), None)
        if spec is None:
            return []
        # Reuse the price simulator by treating the index as a pseudo-stock.
        pseudo = StockMeta(
            stock_id=index_id,
            name=spec["name"],
            name_en=index_id,
            sector="INDEX",
            theme="INDEX",
            market="INDEX",
            base_price=spec["base_value"],
            market_cap_billion=50_000.0,  # large -> smoother, lower vol relative move
        )
        return simulate_prices(pseudo, end, days)
