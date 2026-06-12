"""Admin/ops endpoints — manual pipeline trigger & health.

The manual trigger is handy for demos: it regenerates the full day's analysis on
demand instead of waiting for the scheduled nightly run.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import cache_clear
from app.services.pipeline import run_daily_pipeline

router = APIRouter()


@router.post("/admin/run-pipeline")
def trigger_pipeline(db: Session = Depends(get_db)) -> dict:
    summary = run_daily_pipeline(db, date.today())
    cache_clear()
    return {"status": "ok", "summary": summary}
