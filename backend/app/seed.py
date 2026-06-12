"""Database bootstrap & seeding.

Creates tables (if missing) and runs the pipeline once so the app has data on
first boot. Idempotent: skips the pipeline if today's analysis already exists.
Can be invoked standalone (``python -m app.seed``) or from the app lifespan.
"""
from __future__ import annotations

import logging
from datetime import date

from app.database import Base, SessionLocal, engine
from app.models import StockScore  # noqa: F401 - ensure models are registered
import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")


def seed_if_empty() -> None:
    """Run the pipeline for today if no analysis exists yet."""
    db = SessionLocal()
    try:
        today = date.today()
        exists = (
            db.query(StockScore)
            .filter(StockScore.score_date == today)
            .first()
            is not None
        )
        if exists:
            logger.info("Seed skipped: analysis for %s already present.", today)
            return
        logger.info("Seeding database with analysis for %s ...", today)
        run_daily_pipeline(db, today)
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()
    seed_if_empty()


if __name__ == "__main__":
    main()
