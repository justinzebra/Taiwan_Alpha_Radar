"""Per-stock Alpha Score model.

Stores the composite score plus each of the five dimension sub-scores and the
human-readable reasoning produced by the alpha engine. Dimension breakdown is
kept as JSON so new dimensions can be added without a schema migration.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import JSONType


class StockScore(Base):
    """Composite Alpha Score for one stock on one analysis date."""

    __tablename__ = "stock_scores"
    __table_args__ = (
        UniqueConstraint("stock_id", "score_date", name="uq_score_stock_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id", ondelete="CASCADE"), index=True
    )
    score_date: Mapped[date] = mapped_column(Date, index=True)

    total_score: Mapped[float] = mapped_column(Float, index=True)

    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    institutional_score: Mapped[float] = mapped_column(Float, default=0.0)
    fundamental_score: Mapped[float] = mapped_column(Float, default=0.0)
    thematic_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Full per-dimension payload: {dimension: {score, weight, reasons: [...], metrics: {...}}}
    breakdown: Mapped[dict] = mapped_column(JSONType, default=dict)

    rank: Mapped[int] = mapped_column(default=0, index=True)
    recommendation: Mapped[str] = mapped_column(String(16), default="觀望")

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    stock: Mapped["Stock"] = relationship(back_populates="scores")  # noqa: F821
