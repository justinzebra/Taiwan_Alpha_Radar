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
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai import get_report_engine
from app.alpha import (
    StockScoreEngine,
    aggregate_sectors,
    compute_market_score,
)
from app.alpha.stock_score import StockScoreResult
from app.collectors import get_collectors
from app.collectors.market.intraday_snapshot_collector import (
    TwseMisIntradaySnapshotCollector,
)
from app.config import settings
from app.models import (
    AIReport,
    DailyPrediction,
    DailyPrice,
    DataSourceState,
    MarketScore,
    SectorScore,
    Stock,
    StockScore,
    PredictionOutcome,
)
from app.domain.universe import UNIVERSE
from app.services.backtest import (
    build_all_predictions,
    build_intraday_preview_predictions,
    evaluate_all_predictions,
)

logger = logging.getLogger(__name__)

# How many top stocks get a freshly generated AI report each run.
AI_REPORT_TOP_N = 10


def sync_universe(db: Session) -> None:
    """Ensure every universe stock exists in the ``stocks`` table."""
    existing = {
        stock.stock_id: stock for stock in db.execute(select(Stock)).scalars().all()
    }
    for meta in UNIVERSE:
        stock = existing.get(meta.stock_id)
        if stock is None:
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
            continue
        stock.name = meta.name
        stock.name_en = meta.name_en
        stock.sector = meta.sector
        stock.theme = meta.theme
        stock.market = meta.market
        stock.market_cap_billion = meta.market_cap_billion
    db.commit()


def _persist_prices(db: Session, engine: StockScoreEngine, as_of: date) -> None:
    """Persist the most recent ``price_history_to_store`` candles per stock."""
    store_days = settings.market_history_days
    for meta in UNIVERSE:
        candles = engine.collectors.price.fetch_history(
            meta.stock_id, as_of, settings.market_history_days
        )
        for c in candles[-store_days:]:
            row = db.execute(
                select(DailyPrice)
                .where(DailyPrice.stock_id == meta.stock_id)
                .where(DailyPrice.trade_date == c.trade_date)
            ).scalar_one_or_none()
            if row is None:
                row = DailyPrice(stock_id=meta.stock_id, trade_date=c.trade_date)
                db.add(row)
            row.open = c.open
            row.high = c.high
            row.low = c.low
            row.close = c.close
            row.volume = c.volume
            row.change_pct = c.change_pct
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
    *,
    price_source: str,
    other_sources: str,
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
            notes={
                **market.notes,
                "price_source": price_source,
                "other_sources": other_sources,
                "prediction_methodology": "technical_eod_v1",
            },
        )
    )
    db.commit()


def _prepare_data_source(db: Session, provider: str) -> None:
    state = db.get(DataSourceState, "market_data_provider")
    if state is not None and state.value == provider:
        return
    has_prices = db.execute(select(DailyPrice.id).limit(1)).scalar_one_or_none()
    if has_prices is not None:
        db.execute(delete(PredictionOutcome))
        db.execute(delete(DailyPrediction))
        db.execute(delete(AIReport))
        db.execute(delete(StockScore))
        db.execute(delete(SectorScore))
        db.execute(delete(MarketScore))
        db.execute(delete(DailyPrice))
    if state is None:
        state = DataSourceState(key="market_data_provider", value=provider)
        db.add(state)
    else:
        state.value = provider
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
    _prepare_data_source(db, settings.data_provider)

    collectors = get_collectors(settings.data_provider)
    engine = StockScoreEngine(
        collectors,
        history_days=min(settings.seed_days_of_history, settings.market_history_days),
    )

    latest = collectors.price.fetch_history(UNIVERSE[0].stock_id, as_of, 1)
    if not latest:
        raise RuntimeError(f"No close-price data available on or before {as_of}")
    analysis_date = latest[-1].trade_date
    scores = [r for meta in UNIVERSE if (r := engine.score(meta, analysis_date))]

    _persist_prices(db, engine, analysis_date)
    _persist_stock_scores(db, scores, analysis_date)
    _persist_sector_scores(db, scores, analysis_date)
    _persist_market_score(
        db,
        engine,
        scores,
        analysis_date,
        price_source=collectors.price_source,
        other_sources=collectors.other_sources,
    )
    _persist_ai_reports(db, scores, analysis_date)
    predictions = build_all_predictions(
        db,
        lookback_days=settings.prediction_lookback_days,
        data_source=collectors.price_source,
    )
    outcomes = evaluate_all_predictions(db)
    last_run = db.get(DataSourceState, "pipeline_last_requested_date")
    if last_run is None:
        db.add(
            DataSourceState(
                key="pipeline_last_requested_date", value=as_of.isoformat()
            )
        )
    else:
        last_run.value = as_of.isoformat()
    db.commit()

    summary = {
        "as_of": analysis_date.isoformat(),
        "stocks_scored": len(scores),
        "ai_reports": min(AI_REPORT_TOP_N, len(scores)),
        "price_source": collectors.price_source,
        "predictions": predictions,
        "evaluated_outcomes": outcomes,
    }
    logger.info("Pipeline complete: %s", summary)
    return summary


def run_intraday_preview_pipeline(
    db: Session,
    as_of: date,
    *,
    quote_collector: TwseMisIntradaySnapshotCollector | None = None,
) -> dict:
    """Generate pre-close preview predictions from best-effort quote snapshots."""
    logger.info("Running intraday preview pipeline for %s", as_of)
    sync_universe(db)
    quote_collector = quote_collector or TwseMisIntradaySnapshotCollector()
    now = datetime.now(ZoneInfo("Asia/Taipei")).replace(tzinfo=None)

    preview_candles = {}
    errors: list[str] = []
    for meta in UNIVERSE:
        try:
            snapshot = quote_collector.fetch_snapshot(meta, now)
        except Exception as exc:  # pragma: no cover - network failure path
            errors.append(f"{meta.stock_id}: {exc}")
            continue
        if snapshot is None:
            continue
        if snapshot.candle.trade_date != as_of:
            continue
        preview_candles[meta.stock_id] = snapshot.candle

    if not preview_candles:
        summary = {
            "status": "unavailable",
            "as_of": as_of.isoformat(),
            "price_status": "intraday_preview_unavailable",
            "price_timestamp": now.isoformat(),
            "price_source": quote_collector.source,
            "quote_count": 0,
            "predictions": 0,
            "message": "盤中行情暫時無法取得，未建立未收盤暫估。",
        }
        if errors:
            summary["errors"] = errors[:5]
        logger.info("Intraday preview unavailable: %s", summary)
        return summary

    predictions = build_intraday_preview_predictions(
        db,
        preview_candles_by_stock=preview_candles,
        price_timestamp=now,
        data_source=quote_collector.source,
        lookback_days=settings.prediction_lookback_days,
    )
    summary = {
        "status": "ok",
        "as_of": as_of.isoformat(),
        "price_status": "intraday_preview",
        "price_timestamp": now.isoformat(),
        "price_source": quote_collector.source,
        "quote_count": len(preview_candles),
        "predictions": predictions,
        "message": "已建立未收盤暫估預測。",
    }
    if errors:
        summary["errors"] = errors[:5]
    logger.info("Intraday preview complete: %s", summary)
    return summary
