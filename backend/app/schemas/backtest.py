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


class RegimeBacktestRow(BaseModel):
    methodology: str
    market_regime: str
    market_regime_label: str
    horizon_days: int
    evaluated_predictions: int
    average_market_breadth_pct: float
    top10_average_return_pct: float
    benchmark_return_pct: float
    top10_excess_return_pct: float
    top10_win_rate_pct: float
    direction_accuracy_pct: float


class RegimeBacktestResponse(BaseModel):
    data_source: str
    prediction_start: str
    prediction_end: str
    rows: list[RegimeBacktestRow]


class PredictionItem(BaseModel):
    rank: int
    stock_id: str
    name: str
    theme: str
    signal_score: float
    adjusted_score: float
    direction: str
    confidence: float
    entry_close: float
    market_breadth: float | None = None
    market_regime: str | None = None
    quality_tag: str | None = None
    quality_reason: str | None = None
    institutional_foreign_net: int | None = None
    institutional_trust_net: int | None = None
    institutional_dealer_net: int | None = None
    institutional_total_net: int | None = None
    institutional_intensity: float | None = None
    institutional_tag: str | None = None
    institutional_reason: str | None = None
    is_preview: bool = False
    price_status: str = "final_close"
    price_timestamp: str | None = None


class PredictionGroupOption(BaseModel):
    value: str
    label: str
    count: int


class PredictionListResponse(BaseModel):
    as_of: str
    methodology: str
    data_source: str
    is_preview: bool = False
    price_status: str = "final_close"
    price_timestamp: str | None = None
    selected_group: str
    available_groups: list[PredictionGroupOption]
    items: list[PredictionItem]


class DailyPredictionResultItem(BaseModel):
    rank: int
    stock_id: str
    name: str
    theme: str
    signal_score: float
    adjusted_score: float
    direction: str
    confidence: float
    prediction_close: float
    market_breadth: float | None = None
    market_regime: str | None = None
    quality_tag: str | None = None
    quality_reason: str | None = None
    institutional_foreign_net: int | None = None
    institutional_trust_net: int | None = None
    institutional_dealer_net: int | None = None
    institutional_total_net: int | None = None
    institutional_intensity: float | None = None
    institutional_tag: str | None = None
    institutional_reason: str | None = None
    is_preview: bool = False
    price_status: str = "final_close"
    price_timestamp: str | None = None
    result_open: float | None
    result_close: float
    return_pct: float
    open_to_close_pct: float | None
    excess_return_pct: float
    direction_correct: bool


class DailyPredictionResultResponse(BaseModel):
    methodology: str
    data_source: str
    is_preview: bool = False
    price_status: str = "final_close"
    price_timestamp: str | None = None
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
