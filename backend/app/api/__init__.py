"""API router aggregation."""
from fastapi import APIRouter

from app.api.routes import admin, dashboard, market, sectors, stocks

api_router = APIRouter()
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(market.router, tags=["market"])
api_router.include_router(sectors.router, tags=["sectors"])
api_router.include_router(stocks.router, tags=["stocks"])
api_router.include_router(admin.router, tags=["admin"])
