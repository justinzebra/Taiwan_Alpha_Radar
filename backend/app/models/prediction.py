"""Daily end-of-day predictions and their forward-return outcomes."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyPrediction(Base):
    __tablename__ = "daily_predictions"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "prediction_date", "methodology",
            name="uq_prediction_stock_date_method",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id", ondelete="CASCADE"), index=True
    )
    prediction_date: Mapped[date] = mapped_column(Date, index=True)
    methodology: Mapped[str] = mapped_column(String(32), index=True)
    data_source: Mapped[str] = mapped_column(String(32))
    signal_score: Mapped[float] = mapped_column(Float)
    adjusted_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction: Mapped[str] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer, index=True)
    entry_close: Mapped[float] = mapped_column(Float)
    market_breadth: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_preview: Mapped[bool] = mapped_column(Boolean, default=False)
    price_status: Mapped[str] = mapped_column(String(32), default="final_close")
    price_timestamp: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "prediction_id", "horizon_days", name="uq_prediction_outcome_horizon"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("daily_predictions.id", ondelete="CASCADE"), index=True
    )
    horizon_days: Mapped[int] = mapped_column(Integer, index=True)
    exit_date: Mapped[date] = mapped_column(Date)
    exit_close: Mapped[float] = mapped_column(Float)
    return_pct: Mapped[float] = mapped_column(Float)
    benchmark_return_pct: Mapped[float] = mapped_column(Float)
    excess_return_pct: Mapped[float] = mapped_column(Float)
    direction_correct: Mapped[bool] = mapped_column(Boolean)


class DataSourceState(Base):
    __tablename__ = "data_source_state"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
