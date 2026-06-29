"""Prediction backtest endpoint."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.backtest import (
    BacktestSummary,
    DailyPredictionResultResponse,
    PredictionListResponse,
    RegimeBacktestResponse,
)
from app.services.backtest import (
    METHODOLOGY_V1,
    get_backtest_summary,
    get_daily_prediction_results,
    get_latest_predictions,
    get_regime_backtest_summary,
)

router = APIRouter()
MethodologyParam = Literal[
    "technical_eod_v1",
    "technical_eod_v2_candidate",
    "technical_eod_v3_institutional",
    "technical_intraday_preview_v1",
    "technical_intraday_preview_v2_candidate",
]


@router.get("/backtest", response_model=BacktestSummary)
def read_backtest(
    methodology: MethodologyParam = Query(METHODOLOGY_V1),
    db: Session = Depends(get_db),
) -> BacktestSummary:
    return get_backtest_summary(db, methodology=methodology)


@router.get("/backtest/regimes", response_model=RegimeBacktestResponse)
def read_regime_backtest(db: Session = Depends(get_db)) -> RegimeBacktestResponse:
    return get_regime_backtest_summary(db)


@router.get("/predictions", response_model=PredictionListResponse)
def read_predictions(
    limit: int = Query(10, ge=1, le=100),
    theme: str | None = Query(None),
    methodology: MethodologyParam = Query(METHODOLOGY_V1),
    db: Session = Depends(get_db),
) -> PredictionListResponse:
    return get_latest_predictions(
        db, limit=limit, theme=theme, methodology=methodology
    )


@router.get("/prediction-results", response_model=DailyPredictionResultResponse)
def read_prediction_results(
    prediction_date: date | None = Query(None, alias="date"),
    limit: int = Query(10, ge=1, le=100),
    theme: str | None = Query(None),
    methodology: MethodologyParam = Query(METHODOLOGY_V1),
    db: Session = Depends(get_db),
) -> DailyPredictionResultResponse:
    return get_daily_prediction_results(
        db,
        prediction_date=prediction_date,
        limit=limit,
        theme=theme,
        methodology=methodology,
    )
