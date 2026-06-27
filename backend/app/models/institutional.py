"""Daily three-major-institution net flow model."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyInstitutionalFlow(Base):
    """One trading day of institutional net buy/sell for a single stock."""

    __tablename__ = "daily_institutional_flows"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "trade_date", name="uq_institutional_stock_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id", ondelete="CASCADE"), index=True
    )
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    data_source: Mapped[str] = mapped_column(String(64), default="mock")
    foreign_net: Mapped[int] = mapped_column(Integer, default=0)
    trust_net: Mapped[int] = mapped_column(Integer, default=0)
    dealer_net: Mapped[int] = mapped_column(Integer, default=0)
    total_net: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

