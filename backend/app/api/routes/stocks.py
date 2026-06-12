"""Stock ranking & detail endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.stock import StockDetailResponse, StockListResponse
from app.services import queries

router = APIRouter()


@router.get("/stocks", response_model=StockListResponse)
def list_stocks(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="股票名稱或代號"),
    sort: str = Query("rank", pattern="^(rank|score|technical|institutional|fundamental)$"),
    theme: str | None = Query(None, description="篩選題材族群"),
) -> StockListResponse:
    return queries.list_stocks(
        db, page=page, page_size=page_size, search=search, sort=sort, theme=theme
    )


@router.get("/stocks/{stock_id}", response_model=StockDetailResponse)
def get_stock(stock_id: str, db: Session = Depends(get_db)) -> StockDetailResponse:
    data = queries.get_stock_detail(db, stock_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"找不到股票 {stock_id} 的分析資料")
    return data
