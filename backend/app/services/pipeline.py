"""Daily analysis pipeline.

The single orchestration entry point used by both the scheduler (nightly run)
and the seed script (first boot). Steps:

  1. Score every stock in the universe (alpha engine).
  2. Rank and persist stock scores.
  3. Aggregate and persist sector/theme scores.
  4. Compute and persist market temperature.
  5. Generate AI reports for the top-ranked stocks.

Persistence is upsert-by-(entity, date), so re-running for the same date is
idempotent.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.ai import get_report_engine
from app.alpha import (
    StockScoreEngine,
    aggregate_sectors,
    compute_market_score,
)
from app.alpha.stock_score import StockScoreResult
from app.collectors import get_collectors
from app.config import settings
from app.models import (
    AIReport,
    DailyPrice,
    MarketScore,
    SectorScore,
    Stock,
    StockScore,
)
from app.domain.universe import UNIVERSE

logger = logging.getLogger(__name__)

# How many top stocks get a freshly generated AI report each run.
AI_REPORT_TOP_N = 10


def sync_universe(db: Session) -> None:
    """Ensure every universe stock exists in the ``stocks`` table."""
    existing = {s.stock_id for s in db.query(Stock.stock_id).all()}
    for meta in UNIVERSE:
        if meta.stock_id not in existing:
            db.add(
                Stock(
                    stock_id=meta.stock_id,
                    name=meta.name,
                    name_en=meta.name_en,
                    sector=meta.sector,
                    theme=meta.theme,
                    market=meta.market,
                    market_cap_billion=meta.market_cap_billion,
                )
            )
    db.commit()


def _persist_prices(db: Session, engine: StockScoreEngine, as_of: date) -> None:
    """Persist the most recent ``price_history_to_store`` candles per stock."""
    store_days = 60
    db.execute(delete(DailyPrice))
    for meta in UNIVERSE:
        candles = engine.collectors.price.fetch_history(
            meta.stock_id, as_of, settings.seed_days_of_history
        )
        for c in candles[-store_days:]:
            db.add(
                DailyPrice(
                    stock_id=meta.stock_id,
                    trade_date=c.trade_date,
                    open=c.open,
                    high=c.high,
                    low=c.low,
                    close=c.close,
                    volume=c.volume,
                    change_pct=c.change_pct,
                )
            )
    db.commit()


def _persist_stock_scores(
    db: Session, scores: list[StockScoreResult], as_of: date
) -> None:
    db.execute(delete(StockScore).where(StockScore.score_date == as_of))
    ranked = sorted(scores, key=lambda s: s.total_score, reverse=True)
    for rank, s in enumerate(ranked, start=1):
        db.add(
            StockScore(
                stock_id=s.stock_id,
                score_date=as_of,
                total_score=s.total_score,
                technical_score=s.dimension_score("technical"),
                institutional_score=s.dimension_score("institutional"),
                fundamental_score=s.dimension_score("fundamental"),
                thematic_score=s.dimension_score("thematic"),
                risk_score=s.dimension_score("risk"),
                breakdown=s.breakdown(),
                rank=rank,
                recommendation=s.recommendation,
            )
        )
    db.commit()


def _persist_sector_scores(
    db: Session, scores: list[StockScoreResult], as_of: date
) -> None:
    db.execute(delete(SectorScore).where(SectorScore.score_date == as_of))
    for sec in aggregate_sectors(scores):
        db.add(
            SectorScore(
                theme=sec.theme,
                score_date=as_of,
                strength_score=sec.strength_score,
                avg_change_pct=sec.avg_change_pct,
                constituent_count=sec.constituent_count,
                rank=sec.rank,
                leaders=sec.leaders,
            )
        )
    db.commit()


def _persist_market_score(
    db: Session,
    engine: StockScoreEngine,
    scores: list[StockScoreResult],
    as_of: date,
) -> None:
    market = compute_market_score(engine.collectors, scores, as_of)
    db.execute(delete(MarketScore).where(MarketScore.score_date == as_of))
    db.add(
        MarketScore(
            score_date=as_of,
            temperature_score=market.temperature_score,
            sentiment_label=market.sentiment,
            advancers=market.advancers,
            decliners=market.decliners,
            total_volume_billion=market.total_volume_billion,
            risk_level=market.risk_level,
            indices=[
                {
                    "index_id": i.index_id,
                    "name": i.name,
                    "value": i.value,
                    "change_pct": i.change_pct,
                    "trend": i.trend,
                    "strength": i.strength,
                    "volume_billion": i.volume_billion,
                }
                for i in market.indices
            ],
            notes=market.notes,
        )
    )
    db.commit()


def _persist_ai_reports(
    db: Session, scores: list[StockScoreResult], as_of: date
) -> None:
    engine = get_report_engine()
    top = sorted(scores, key=lambda s: s.total_score, reverse=True)[:AI_REPORT_TOP_N]
    db.execute(delete(AIReport).where(AIReport.report_date == as_of))
    for s in top:
        report = engine.generate(s)
        db.add(
            AIReport(
                stock_id=s.stock_id,
                report_date=as_of,
                provider=report.provider,
                summary=report.summary,
                sections=report.sections(),
            )
        )
    db.commit()


def run_daily_pipeline(db: Session, as_of: date) -> dict:
    """Execute the full pipeline for ``as_of`` and return a run summary."""
    logger.info("Running daily pipeline for %s", as_of)
    sync_universe(db)

    # Data source is independent of the AI provider; mock feed for v1.
    collectors = get_collectors("mock")
    engine = StockScoreEngine(collectors)

    scores = [r for meta in UNIVERSE if (r := engine.score(meta, as_of))]

    _persist_prices(db, engine, as_of)
    _persist_stock_scores(db, scores, as_of)
    _persist_sector_scores(db, scores, as_of)
    _persist_market_score(db, engine, scores, as_of)
    _persist_ai_reports(db, scores, as_of)

    summary = {
        "as_of": as_of.isoformat(),
        "stocks_scored": len(scores),
        "ai_reports": min(AI_REPORT_TOP_N, len(scores)),
    }
    logger.info("Pipeline complete: %s", summary)
    return summary
