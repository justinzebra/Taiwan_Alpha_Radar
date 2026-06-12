"""Dashboard aggregate response schema."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.market import MarketResponse
from app.schemas.sector import SectorItem
from app.schemas.stock import StockListItem


class ScoreBucket(BaseModel):
    label: str          # e.g. "80-100"
    count: int


class DashboardResponse(BaseModel):
    as_of: str
    market: MarketResponse
    top_stocks: list[StockListItem]
    hot_sectors: list[SectorItem]
    score_distribution: list[ScoreBucket]
