"""Prediction backtest endpoint."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.backtest import (
    BacktestSummary,
    DailyPredictionResultResponse,
    PredictionListResponse,
)
from app.services.backtest import (
    get_backtest_summary,
    get_daily_prediction_results,
    get_latest_predictions,
)

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


@router.get("/prediction-results", response_model=DailyPredictionResultResponse)
def read_prediction_results(
    prediction_date: date | None = Query(None, alias="date"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DailyPredictionResultResponse:
    return get_daily_prediction_results(
        db,
        prediction_date=prediction_date,
        limit=limit,
    )
