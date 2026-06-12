"""Sector/theme response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class SectorLeader(BaseModel):
    stock_id: str
    name: str
    change_pct: float
    total_score: float


class SectorItem(BaseModel):
    theme: str
    rank: int
    strength_score: float
    avg_change_pct: float
    constituent_count: int
    leaders: list[SectorLeader]


class SectorListResponse(BaseModel):
    as_of: str
    sectors: list[SectorItem]
