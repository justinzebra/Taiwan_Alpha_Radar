"""Market analysis endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.market import MarketResponse
from app.services import queries

router = APIRouter()


@router.get("/market", response_model=MarketResponse)
def read_market(db: Session = Depends(get_db)) -> MarketResponse:
    data = queries.get_market(db)
    if data is None:
        raise HTTPException(status_code=503, detail="大盤分析尚未就緒")
    return data
