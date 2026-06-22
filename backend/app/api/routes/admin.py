"""Admin/ops endpoints — manual pipeline trigger & health.

The manual trigger is handy for demos: it regenerates the full day's analysis on
demand instead of waiting for the scheduled nightly run.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import cache_clear
from app.services.pipeline import run_daily_pipeline, run_intraday_preview_pipeline

router = APIRouter()


@router.post("/admin/run-pipeline")
def trigger_pipeline(db: Session = Depends(get_db)) -> dict:
    today = datetime.now(ZoneInfo("Asia/Taipei")).date()
    summary = run_daily_pipeline(db, today)
    preview = run_intraday_preview_pipeline(db, today)
    cache_clear()
    return {"status": "ok", "summary": summary, "preview": preview}
