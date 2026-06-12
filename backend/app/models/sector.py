"""Per-theme/sector score model (今日熱門族群)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import JSONType


class SectorScore(Base):
    """Aggregated strength score for one theme on one analysis date."""

    __tablename__ = "sector_scores"
    __table_args__ = (
        UniqueConstraint("theme", "score_date", name="uq_sector_theme_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    theme: Mapped[str] = mapped_column(String(32), index=True)
    score_date: Mapped[date] = mapped_column(Date, index=True)

    strength_score: Mapped[float] = mapped_column(Float, index=True)
    avg_change_pct: Mapped[float] = mapped_column(Float, default=0.0)
    constituent_count: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # Top constituents: [{stock_id, name, change_pct, total_score}]
    leaders: Mapped[list] = mapped_column(JSONType, default=list)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
