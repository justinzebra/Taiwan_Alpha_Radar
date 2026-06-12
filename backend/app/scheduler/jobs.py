"""APScheduler setup for the nightly analysis run.

A single cron job runs the daily pipeline after market close. The scheduler is
created lazily and started/stopped from the FastAPI lifespan.
"""
from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.services.cache import cache_clear
from app.services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _daily_job() -> None:
    """Run the pipeline against a fresh DB session."""
    db = SessionLocal()
    try:
        run_daily_pipeline(db, date.today())
        cache_clear()
    except Exception:  # noqa: BLE001
        logger.exception("Scheduled daily pipeline failed")
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if not settings.enable_scheduler or _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    _scheduler.add_job(
        _daily_job,
        trigger=CronTrigger(
            hour=settings.daily_job_hour,
            minute=settings.daily_job_minute,
        ),
        id="daily_analysis",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: daily run at %02d:%02d %s",
        settings.daily_job_hour,
        settings.daily_job_minute,
        settings.scheduler_timezone,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
