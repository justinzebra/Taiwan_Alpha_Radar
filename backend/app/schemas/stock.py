"""Stock ranking & detail response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class StockListItem(BaseModel):
    rank: int
    stock_id: str
    name: str
    sector: str
    theme: str
    total_score: float
    change_pct: float
    last_close: float
    recommendation: str


class StockListResponse(BaseModel):
    as_of: str
    total: int
    page: int
    page_size: int
    items: list[StockListItem]


class DimensionDetail(BaseModel):
    key: str
    label: str
    score: float
    weight: float
    weighted: float
    reasons: list[str]
    metrics: dict


class AIReportDetail(BaseModel):
    provider: str
    summary: str
    highlights: list[str]
    risks: list[str]
    short_term: str
    mid_term: str


class PricePoint(BaseModel):
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: float


class StockDetailResponse(BaseModel):
    as_of: str
    stock_id: str
    name: str
    name_en: str
    sector: str
    theme: str
    market: str
    total_score: float
    rank: int
    recommendation: str
    last_close: float
    change_pct: float
    dimensions: list[DimensionDetail]
    ai_report: AIReportDetail | None
    price_history: list[PricePoint]
