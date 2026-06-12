"""Dashboard endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services import queries
from app.services.cache import cache_get, cache_set

router = APIRouter()

_CACHE_KEY = "tar:dashboard"


@router.get("/dashboard", response_model=DashboardResponse)
def read_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    cached = cache_get(_CACHE_KEY)
    if cached:
        return DashboardResponse(**cached)
    data = queries.get_dashboard(db)
    if data is None:
        raise HTTPException(status_code=503, detail="分析資料尚未就緒，請稍後再試")
    cache_set(_CACHE_KEY, data.model_dump())
    return data
