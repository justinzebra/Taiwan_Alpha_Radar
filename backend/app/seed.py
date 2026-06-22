"""Database bootstrap & seeding.

Creates tables (if missing) and runs the pipeline once so the app has data on
first boot. Idempotent: skips the pipeline if today's analysis already exists.
Can be invoked standalone (``python -m app.seed``) or from the app lifespan.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import inspect, text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import DataSourceState, StockScore  # noqa: F401 - ensure models are registered
import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.services.pipeline import run_daily_pipeline, sync_universe

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    _ensure_prediction_columns()
    logger.info("Database tables ensured.")


def _ensure_prediction_columns() -> None:
    """Add nullable v2 columns when an existing DB predates this schema."""
    inspector = inspect(engine)
    if "daily_predictions" not in inspector.get_table_names():
        return
    existing = {
        column["name"] for column in inspector.get_columns("daily_predictions")
    }
    columns = {
        "adjusted_score": "FLOAT",
        "market_breadth": "FLOAT",
        "market_regime": "VARCHAR(32)",
        "quality_tag": "VARCHAR(32)",
        "quality_reason": "VARCHAR(255)",
    }
    missing = [(name, ddl) for name, ddl in columns.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as conn:
        for name, ddl in missing:
            conn.execute(text(f"ALTER TABLE daily_predictions ADD COLUMN {name} {ddl}"))


def seed_if_empty() -> None:
    """Run the pipeline for today if no analysis exists yet."""
    db = SessionLocal()
    try:
        sync_universe(db)
        today = date.today()
        has_analysis = db.query(StockScore).first() is not None
        source_state = db.get(DataSourceState, "market_data_provider")
        last_run = db.get(DataSourceState, "pipeline_last_requested_date")
        source_matches = (
            source_state is not None and source_state.value == settings.data_provider
        )
        already_requested_today = (
            last_run is not None and last_run.value == today.isoformat()
        )
        if has_analysis and source_matches and already_requested_today:
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
