"""AI-generated investment report model."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import JSONType


class AIReport(Base):
    """LLM-generated investment summary for one stock on one date."""

    __tablename__ = "ai_reports"
    __table_args__ = (
        UniqueConstraint("stock_id", "report_date", name="uq_report_stock_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id", ondelete="CASCADE"), index=True
    )
    report_date: Mapped[date] = mapped_column(Date, index=True)

    provider: Mapped[str] = mapped_column(String(16), default="mock")
    summary: Mapped[str] = mapped_column(Text, default="")

    # Structured sections: {highlights: [...], risks: [...], short_term: str, mid_term: str}
    sections: Mapped[dict] = mapped_column(JSONType, default=dict)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
