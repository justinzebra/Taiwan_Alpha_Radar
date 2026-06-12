"""FastAPI application entry point.

Wires CORS, the API router, the scheduler, and DB bootstrap/seed into the app
lifespan so ``docker compose up`` yields a fully populated, running platform.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.scheduler.jobs import shutdown_scheduler, start_scheduler
from app.seed import init_db, seed_if_empty

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("taiwan_alpha_radar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s ...", settings.app_name)
    init_db()
    if settings.auto_seed_on_startup:
        try:
            seed_if_empty()
        except Exception:  # noqa: BLE001 - app should still start if seed fails
            logger.exception("Seeding failed; API will return 503 until data exists.")
    start_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="台股 AI 選股分析平台 — 每日選股決策平台 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
    }
