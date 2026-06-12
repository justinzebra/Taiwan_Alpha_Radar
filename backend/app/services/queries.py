"""Read-side query service.

Builds API response schemas from persisted analysis rows. Keeps all DB-reading
logic in one place so routes stay thin.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AIReport,
    DailyPrice,
    MarketScore,
    SectorScore,
    Stock,
    StockScore,
)
from app.schemas.dashboard import DashboardResponse, DataStatus, ScoreBucket
from app.schemas.market import IndexItem, MarketResponse
from app.schemas.sector import SectorItem, SectorListResponse
from app.schemas.stock import (
    AIReportDetail,
    DimensionDetail,
    PricePoint,
    StockDetailResponse,
    StockListItem,
    StockListResponse,
)


def latest_score_date(db: Session) -> date | None:
    return db.execute(
        select(func.max(StockScore.score_date))
    ).scalar_one_or_none()


def get_market(db: Session) -> MarketResponse | None:
    row = db.execute(
        select(MarketScore).order_by(MarketScore.score_date.desc()).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    return MarketResponse(
        as_of=row.score_date.isoformat(),
        temperature_score=row.temperature_score,
        sentiment=row.sentiment_label,
        risk_level=row.risk_level,
        advancers=row.advancers,
        decliners=row.decliners,
        total_volume_billion=row.total_volume_billion,
        indices=[IndexItem(**i) for i in row.indices],
        notes=row.notes,
    )


def get_sectors(db: Session) -> SectorListResponse:
    as_of = latest_score_date(db)
    if as_of is None:
        return SectorListResponse(as_of="", sectors=[])
    rows = db.execute(
        select(SectorScore)
        .where(SectorScore.score_date == as_of)
        .order_by(SectorScore.rank)
    ).scalars().all()
    return SectorListResponse(
        as_of=as_of.isoformat(),
        sectors=[
            SectorItem(
                theme=r.theme,
                rank=r.rank,
                strength_score=r.strength_score,
                avg_change_pct=r.avg_change_pct,
                constituent_count=r.constituent_count,
                leaders=r.leaders,
            )
            for r in rows
        ],
    )


def _stock_list_item(score: StockScore, stock: Stock) -> StockListItem:
    last_close = 0.0
    change_pct = 0.0
    tech = score.breakdown.get("technical", {}) if score.breakdown else {}
    metrics = tech.get("metrics", {})
    if metrics:
        last_close = metrics.get("close", 0.0)
    return StockListItem(
        rank=score.rank,
        stock_id=score.stock_id,
        name=stock.name,
        sector=stock.sector,
        theme=stock.theme,
        total_score=score.total_score,
        change_pct=change_pct,
        last_close=last_close,
        recommendation=score.recommendation,
    )


def list_stocks(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    sort: str = "rank",
    theme: str | None = None,
) -> StockListResponse:
    as_of = latest_score_date(db)
    if as_of is None:
        return StockListResponse(
            as_of="", total=0, page=page, page_size=page_size, items=[]
        )

    stmt = (
        select(StockScore, Stock)
        .join(Stock, Stock.stock_id == StockScore.stock_id)
        .where(StockScore.score_date == as_of)
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where((Stock.name.ilike(like)) | (Stock.stock_id.ilike(like)))
    if theme:
        stmt = stmt.where(Stock.theme == theme)

    order = {
        "rank": StockScore.rank.asc(),
        "score": StockScore.total_score.desc(),
        "technical": StockScore.technical_score.desc(),
        "institutional": StockScore.institutional_score.desc(),
        "fundamental": StockScore.fundamental_score.desc(),
    }.get(sort, StockScore.rank.asc())
    stmt = stmt.order_by(order)

    rows = db.execute(stmt).all()
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    items = [_stock_list_item(score, stock) for score, stock in page_rows]
    # change_pct comes from latest price row.
    _attach_change_pct(db, items)
    return StockListResponse(
        as_of=as_of.isoformat(),
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


def _attach_change_pct(db: Session, items: list[StockListItem]) -> None:
    if not items:
        return
    ids = [i.stock_id for i in items]
    latest_date = db.execute(
        select(func.max(DailyPrice.trade_date)).where(DailyPrice.stock_id.in_(ids))
    ).scalar_one_or_none()
    if latest_date is None:
        return
    rows = db.execute(
        select(DailyPrice.stock_id, DailyPrice.change_pct, DailyPrice.close)
        .where(DailyPrice.trade_date == latest_date)
        .where(DailyPrice.stock_id.in_(ids))
    ).all()
    by_id = {r.stock_id: (r.change_pct, r.close) for r in rows}
    for item in items:
        if item.stock_id in by_id:
            item.change_pct, item.last_close = by_id[item.stock_id]


def get_stock_detail(db: Session, stock_id: str) -> StockDetailResponse | None:
    as_of = latest_score_date(db)
    if as_of is None:
        return None
    stock = db.get(Stock, stock_id)
    score = db.execute(
        select(StockScore)
        .where(StockScore.stock_id == stock_id)
        .where(StockScore.score_date == as_of)
    ).scalar_one_or_none()
    if stock is None or score is None:
        return None

    dimensions = [
        DimensionDetail(**d) for d in (score.breakdown or {}).values()
    ]
    # Keep canonical dimension order by weight desc.
    dimensions.sort(key=lambda d: d.weight, reverse=True)

    report_row = db.execute(
        select(AIReport)
        .where(AIReport.stock_id == stock_id)
        .where(AIReport.report_date == as_of)
    ).scalar_one_or_none()
    ai_report = None
    if report_row:
        sec = report_row.sections or {}
        ai_report = AIReportDetail(
            provider=report_row.provider,
            summary=report_row.summary,
            highlights=sec.get("highlights", []),
            risks=sec.get("risks", []),
            short_term=sec.get("short_term", ""),
            mid_term=sec.get("mid_term", ""),
        )

    prices = db.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock_id)
        .order_by(DailyPrice.trade_date.asc())
    ).scalars().all()
    price_history = [
        PricePoint(
            trade_date=p.trade_date.isoformat(),
            open=p.open,
            high=p.high,
            low=p.low,
            close=p.close,
            volume=p.volume,
            change_pct=p.change_pct,
        )
        for p in prices
    ]
    last = price_history[-1] if price_history else None

    return StockDetailResponse(
        as_of=as_of.isoformat(),
        stock_id=stock.stock_id,
        name=stock.name,
        name_en=stock.name_en,
        sector=stock.sector,
        theme=stock.theme,
        market=stock.market,
        total_score=score.total_score,
        rank=score.rank,
        recommendation=score.recommendation,
        last_close=last.close if last else 0.0,
        change_pct=last.change_pct if last else 0.0,
        dimensions=dimensions,
        ai_report=ai_report,
        price_history=price_history,
    )


def get_dashboard(db: Session) -> DashboardResponse | None:
    market = get_market(db)
    if market is None:
        return None
    top = list_stocks(db, page=1, page_size=10, sort="rank")
    sectors = get_sectors(db)

    # Score distribution buckets.
    as_of = latest_score_date(db)
    buckets_def = [("80-100", 80, 101), ("60-79", 60, 80), ("40-59", 40, 60), ("0-39", 0, 40)]
    distribution: list[ScoreBucket] = []
    for label, lo, hi in buckets_def:
        count = db.execute(
            select(func.count())
            .select_from(StockScore)
            .where(StockScore.score_date == as_of)
            .where(StockScore.total_score >= lo)
            .where(StockScore.total_score < hi)
        ).scalar_one()
        distribution.append(ScoreBucket(label=label, count=count))

    return DashboardResponse(
        as_of=market.as_of,
        market=market,
        top_stocks=top.items,
        hot_sectors=sectors.sectors[:6],
        score_distribution=distribution,
        data_status=DataStatus(
            price_source=market.notes.get("price_source", "unknown"),
            other_sources=market.notes.get("other_sources", "unknown"),
            prediction_methodology="technical_eod_v1",
            price_data_is_real=market.notes.get("price_source") == "twse_tpex_official",
            full_alpha_is_real=market.notes.get("other_sources") != "mock",
        ),
    )
