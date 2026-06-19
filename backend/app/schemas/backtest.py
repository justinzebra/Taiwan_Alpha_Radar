"""Backtest response schemas."""
from pydantic import BaseModel


class BacktestHorizon(BaseModel):
    horizon_days: int
    evaluated_predictions: int
    top10_average_return_pct: float
    benchmark_return_pct: float
    top10_excess_return_pct: float
    top10_win_rate_pct: float
    direction_accuracy_pct: float


class BacktestSummary(BaseModel):
    methodology: str
    data_source: str
    prediction_start: str
    prediction_end: str
    horizons: list[BacktestHorizon]


class PredictionItem(BaseModel):
    rank: int
    stock_id: str
    name: str
    theme: str
    signal_score: float
    direction: str
    confidence: float
    entry_close: float


class PredictionGroupOption(BaseModel):
    value: str
    label: str
    count: int


class PredictionListResponse(BaseModel):
    as_of: str
    methodology: str
    data_source: str
    selected_group: str
    available_groups: list[PredictionGroupOption]
    items: list[PredictionItem]


class DailyPredictionResultItem(BaseModel):
    rank: int
    stock_id: str
    name: str
    theme: str
    signal_score: float
    direction: str
    confidence: float
    prediction_close: float
    result_open: float | None
    result_close: float
    return_pct: float
    open_to_close_pct: float | None
    excess_return_pct: float
    direction_correct: bool


class DailyPredictionResultResponse(BaseModel):
    methodology: str
    data_source: str
    selected_group: str
    available_groups: list[PredictionGroupOption]
    available_dates: list[str]
    prediction_date: str
    result_date: str
    evaluated_predictions: int
    positive_count: int
    average_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    win_rate_pct: float
    direction_accuracy_pct: float
    average_open_to_close_pct: float | None
    items: list[DailyPredictionResultItem]
