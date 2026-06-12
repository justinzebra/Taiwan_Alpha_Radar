"""Dashboard aggregate response schema."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.market import MarketResponse
from app.schemas.sector import SectorItem
from app.schemas.stock import StockListItem


class ScoreBucket(BaseModel):
    label: str          # e.g. "80-100"
    count: int


class DataStatus(BaseModel):
    price_source: str
    other_sources: str
    prediction_methodology: str
    price_data_is_real: bool
    full_alpha_is_real: bool


class DashboardResponse(BaseModel):
    as_of: str
    market: MarketResponse
    top_stocks: list[StockListItem]
    hot_sectors: list[SectorItem]
    score_distribution: list[ScoreBucket]
    data_status: DataStatus
