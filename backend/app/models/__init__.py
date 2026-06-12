"""SQLAlchemy ORM models.

Importing this package registers every model on the shared Base metadata so
``Base.metadata.create_all`` sees all tables.
"""
from app.models.market import MarketScore
from app.models.price import DailyPrice
from app.models.prediction import DailyPrediction, DataSourceState, PredictionOutcome
from app.models.report import AIReport
from app.models.score import StockScore
from app.models.sector import SectorScore
from app.models.stock import Stock

__all__ = [
    "Stock",
    "DailyPrice",
    "StockScore",
    "SectorScore",
    "MarketScore",
    "AIReport",
    "DailyPrediction",
    "PredictionOutcome",
    "DataSourceState",
]
