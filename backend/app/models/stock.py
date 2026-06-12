"""Stock master data model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Stock(Base):
    """Static metadata for a listed company."""

    __tablename__ = "stocks"

    stock_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    name_en: Mapped[str] = mapped_column(String(64), default="")
    sector: Mapped[str] = mapped_column(String(32), index=True)
    theme: Mapped[str] = mapped_column(String(32), index=True)
    market: Mapped[str] = mapped_column(String(8), default="TWSE")
    market_cap_billion: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    prices: Mapped[list["DailyPrice"]] = relationship(  # noqa: F821
        back_populates="stock", cascade="all, delete-orphan"
    )
    scores: Mapped[list["StockScore"]] = relationship(  # noqa: F821
        back_populates="stock", cascade="all, delete-orphan"
    )
