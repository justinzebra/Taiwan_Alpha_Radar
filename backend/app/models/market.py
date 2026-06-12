"""Market-level temperature & index analysis model."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import JSONType


class MarketScore(Base):
    """Overall market temperature for one analysis date.

    ``temperature_score`` is 0-100 (0 = 極度看空, 100 = 極度看多).
    ``indices`` holds per-index snapshots so a single row fully describes the
    dashboard's market section.
    """

    __tablename__ = "market_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    score_date: Mapped[date] = mapped_column(Date, unique=True, index=True)

    temperature_score: Mapped[float] = mapped_column(Float)  # 0-100
    sentiment_label: Mapped[str] = mapped_column(String(16))  # 偏多 / 中性 ...

    advancers: Mapped[int] = mapped_column(default=0)
    decliners: Mapped[int] = mapped_column(default=0)
    total_volume_billion: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(16), default="中")

    # Per-index detail: [{index_id, name, value, change_pct, trend, strength, volume}]
    indices: Mapped[list] = mapped_column(JSONType, default=list)
    # Free-form notes used by the dashboard ("市場風險" etc.)
    notes: Mapped[dict] = mapped_column(JSONType, default=dict)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
