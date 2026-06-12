"""Prediction backtest endpoint."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.backtest import BacktestSummary, PredictionListResponse
from app.services.backtest import get_backtest_summary, get_latest_predictions

router = APIRouter()


@router.get("/backtest", response_model=BacktestSummary)
def read_backtest(db: Session = Depends(get_db)) -> BacktestSummary:
    return get_backtest_summary(db)


@router.get("/predictions", response_model=PredictionListResponse)
def read_predictions(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PredictionListResponse:
    return get_latest_predictions(db, limit=limit)
