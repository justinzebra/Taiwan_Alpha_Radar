"""Market analysis response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class IndexItem(BaseModel):
    index_id: str
    name: str
    value: float
    change_pct: float
    trend: str
    strength: float
    volume_billion: float


class MarketResponse(BaseModel):
    as_of: str
    temperature_score: float
    sentiment: str
    risk_level: str
    advancers: int
    decliners: int
    total_volume_billion: float
    indices: list[IndexItem]
    notes: dict
