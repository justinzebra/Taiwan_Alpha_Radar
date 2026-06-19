"""Walk-forward end-of-day prediction generation and evaluation."""
from __future__ import annotations

import math
from collections import defaultdict

from datetime import date

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.orm import Session

from app.alpha.base import StockContext
from app.alpha.dimensions.technical import TechnicalDimension
from app.domain.simulator import Candle, Fundamentals, InstitutionalFlow
from app.domain.universe import StockMeta
from app.models import DailyPrediction, DailyPrice, PredictionOutcome, Stock
from app.schemas.backtest import (
    BacktestHorizon,
    BacktestSummary,
    DailyPredictionResultItem,
    DailyPredictionResultResponse,
    PredictionGroupOption,
    PredictionItem,
    PredictionListResponse,
)

METHODOLOGY = "technical_eod_v1"
DATA_SOURCE = "twse_tpex_official"

_EMPTY_FLOW = InstitutionalFlow(0, 0, 0, 0, 0)
_EMPTY_FUNDAMENTALS = Fundamentals(0, 0, 0, 0, 0, 0, 0)


def _normalize_group(theme: str | None) -> str:
    return (theme or "").strip()


def _group_options(
    db: Session,
    *,
    prediction_date: date,
    only_evaluated: bool = False,
) -> list[PredictionGroupOption]:
    query = (
        select(Stock.theme, func.count(DailyPrediction.id))
        .join(DailyPrediction, DailyPrediction.stock_id == Stock.stock_id)
        .where(DailyPrediction.methodology == METHODOLOGY)
        .where(DailyPrediction.prediction_date == prediction_date)
        .group_by(Stock.theme)
        .order_by(Stock.theme)
    )
    if only_evaluated:
        query = query.join(
            PredictionOutcome,
            and_(
                PredictionOutcome.prediction_id == DailyPrediction.id,
                PredictionOutcome.horizon_days == 1,
            ),
        )

    rows = db.execute(query).all()
    total = sum(count for _, count in rows)
    return [PredictionGroupOption(value="", label="綜合", count=total)] + [
        PredictionGroupOption(value=theme, label=theme, count=count)
        for theme, count in rows
    ]


def _direction(score: float) -> str:
    if score >= 60:
        return "偏多"
    if score <= 40:
        return "偏空"
    return "中性"


def build_predictions(
    db: Session,
    *,
    lookback_days: int = 120,
    data_source: str = DATA_SOURCE,
) -> int:
    """Generate recent predictions using only information available that day."""
    scorer = TechnicalDimension()
    stocks = db.execute(select(Stock)).scalars().all()
    generated: list[DailyPrediction] = []

    for stock in stocks:
        prices = db.execute(
            select(DailyPrice)
            .where(DailyPrice.stock_id == stock.stock_id)
            .order_by(DailyPrice.trade_date)
        ).scalars().all()
        if len(prices) < 25:
            continue
        start = max(24, len(prices) - lookback_days)
        meta = StockMeta(
            stock.stock_id,
            stock.name,
            stock.name_en,
            stock.sector,
            stock.theme,
            stock.market,
            prices[0].close,
            stock.market_cap_billion,
        )
        for index in range(start, len(prices)):
            if prices[index].close <= 0:
                continue
            window = prices[: index + 1]
            candles = [
                Candle(
                    p.trade_date, p.open, p.high, p.low, p.close, p.volume, p.change_pct
                )
                for p in window
            ]
            context = StockContext(
                meta=meta,
                as_of=prices[index].trade_date,
                candles=candles,
                flow=_EMPTY_FLOW,
                fundamentals=_EMPTY_FUNDAMENTALS,
                news=[],
            )
            score = round(scorer.score(context).score, 1)
            generated.append(
                DailyPrediction(
                    stock_id=stock.stock_id,
                    prediction_date=prices[index].trade_date,
                    methodology=METHODOLOGY,
                    data_source=data_source,
                    signal_score=score,
                    direction=_direction(score),
                    confidence=round(min(100.0, abs(score - 50) * 2), 1),
                    rank=0,
                    entry_close=prices[index].close,
                )
            )

    if not generated:
        return 0

    prediction_dates = {prediction.prediction_date for prediction in generated}
    db.execute(
        delete(DailyPrediction)
        .where(DailyPrediction.methodology == METHODOLOGY)
        .where(DailyPrediction.prediction_date.in_(prediction_dates))
    )
    by_date: dict = defaultdict(list)
    for prediction in generated:
        by_date[prediction.prediction_date].append(prediction)
    for predictions in by_date.values():
        predictions.sort(key=lambda item: item.signal_score, reverse=True)
        for rank, prediction in enumerate(predictions, 1):
            prediction.rank = rank
            db.add(prediction)
    db.commit()
    return len(generated)


def evaluate_predictions(
    db: Session, *, horizons: tuple[int, ...] = (1, 3, 5, 10)
) -> int:
    predictions = db.execute(
        select(DailyPrediction).where(DailyPrediction.methodology == METHODOLOGY)
    ).scalars().all()
    prices_by_stock: dict[str, list[DailyPrice]] = {}
    for stock_id in {prediction.stock_id for prediction in predictions}:
        prices_by_stock[stock_id] = db.execute(
            select(DailyPrice)
            .where(DailyPrice.stock_id == stock_id)
            .order_by(DailyPrice.trade_date)
        ).scalars().all()

    raw: dict[tuple, tuple] = {}
    benchmark_groups: dict[tuple, list[float]] = defaultdict(list)
    for prediction in predictions:
        prices = prices_by_stock[prediction.stock_id]
        index = next(
            (i for i, price in enumerate(prices) if price.trade_date == prediction.prediction_date),
            None,
        )
        if index is None:
            continue
        if prediction.entry_close <= 0:
            continue
        for horizon in horizons:
            exit_index = index + horizon
            if exit_index >= len(prices):
                continue
            exit_price = prices[exit_index]
            return_pct = (exit_price.close / prediction.entry_close - 1) * 100
            key = (prediction.id, horizon)
            raw[key] = (prediction, exit_price, return_pct)
            benchmark_groups[(prediction.prediction_date, horizon)].append(return_pct)

    db.execute(delete(PredictionOutcome))
    for (_, horizon), (prediction, exit_price, return_pct) in raw.items():
        benchmark = sum(
            benchmark_groups[(prediction.prediction_date, horizon)]
        ) / len(benchmark_groups[(prediction.prediction_date, horizon)])
        correct = (
            return_pct > 0 if prediction.direction == "偏多"
            else return_pct < 0 if prediction.direction == "偏空"
            else abs(return_pct) < 1
        )
        db.add(
            PredictionOutcome(
                prediction_id=prediction.id,
                horizon_days=horizon,
                exit_date=exit_price.trade_date,
                exit_close=exit_price.close,
                return_pct=round(return_pct, 4),
                benchmark_return_pct=round(benchmark, 4),
                excess_return_pct=round(return_pct - benchmark, 4),
                direction_correct=correct,
            )
        )
    db.commit()
    return len(raw)


def get_backtest_summary(db: Session) -> BacktestSummary:
    predictions = db.execute(
        select(DailyPrediction).where(DailyPrediction.methodology == METHODOLOGY)
    ).scalars().all()
    if not predictions:
        return BacktestSummary(
            methodology=METHODOLOGY,
            data_source=DATA_SOURCE,
            prediction_start="",
            prediction_end="",
            horizons=[],
        )
    prediction_by_id = {prediction.id: prediction for prediction in predictions}
    outcomes = db.execute(select(PredictionOutcome)).scalars().all()
    grouped: dict[int, list[PredictionOutcome]] = defaultdict(list)
    for outcome in outcomes:
        grouped[outcome.horizon_days].append(outcome)

    stock_count = len({prediction.stock_id for prediction in predictions})
    top_count = min(10, max(1, math.ceil(stock_count * 0.25)))
    horizon_rows = []
    for horizon in sorted(grouped):
        rows = grouped[horizon]
        top = [row for row in rows if prediction_by_id[row.prediction_id].rank <= top_count]
        if not top:
            continue
        horizon_rows.append(
            BacktestHorizon(
                horizon_days=horizon,
                evaluated_predictions=len(top),
                top10_average_return_pct=round(
                    sum(row.return_pct for row in top) / len(top), 2
                ),
                benchmark_return_pct=round(
                    sum(row.benchmark_return_pct for row in top) / len(top), 2
                ),
                top10_excess_return_pct=round(
                    sum(row.excess_return_pct for row in top) / len(top), 2
                ),
                top10_win_rate_pct=round(
                    sum(row.return_pct > 0 for row in top) / len(top) * 100, 1
                ),
                direction_accuracy_pct=round(
                    sum(row.direction_correct for row in top) / len(top) * 100, 1
                ),
            )
        )
    dates = [prediction.prediction_date for prediction in predictions]
    return BacktestSummary(
        methodology=METHODOLOGY,
        data_source=predictions[0].data_source,
        prediction_start=min(dates).isoformat(),
        prediction_end=max(dates).isoformat(),
        horizons=horizon_rows,
    )


def get_latest_predictions(
    db: Session,
    limit: int = 10,
    theme: str | None = None,
) -> PredictionListResponse:
    latest = db.execute(
        select(func.max(DailyPrediction.prediction_date)).where(
            DailyPrediction.methodology == METHODOLOGY
        )
    ).scalar_one_or_none()
    selected_group = _normalize_group(theme)
    if latest is None:
        return PredictionListResponse(
            as_of="",
            methodology=METHODOLOGY,
            data_source=DATA_SOURCE,
            selected_group=selected_group,
            available_groups=[],
            items=[],
        )
    query = (
        select(DailyPrediction, Stock)
        .join(Stock, Stock.stock_id == DailyPrediction.stock_id)
        .where(DailyPrediction.methodology == METHODOLOGY)
        .where(DailyPrediction.prediction_date == latest)
        .order_by(DailyPrediction.rank)
    )
    if selected_group:
        query = query.where(Stock.theme == selected_group)
    rows = db.execute(query.limit(limit)).all()
    return PredictionListResponse(
        as_of=latest.isoformat(),
        methodology=METHODOLOGY,
        data_source=rows[0][0].data_source if rows else DATA_SOURCE,
        selected_group=selected_group,
        available_groups=_group_options(db, prediction_date=latest),
        items=[
            PredictionItem(
                rank=rank,
                stock_id=prediction.stock_id,
                name=stock.name,
                theme=stock.theme,
                signal_score=prediction.signal_score,
                direction=prediction.direction,
                confidence=prediction.confidence,
                entry_close=prediction.entry_close,
            )
            for rank, (prediction, stock) in enumerate(rows, 1)
        ],
    )


def get_daily_prediction_results(
    db: Session,
    *,
    prediction_date: date | None = None,
    limit: int = 10,
    theme: str | None = None,
) -> DailyPredictionResultResponse:
    """Return one prediction day's next-session results and summary."""
    selected_group = _normalize_group(theme)
    available_dates = db.execute(
        select(DailyPrediction.prediction_date)
        .join(Stock, Stock.stock_id == DailyPrediction.stock_id)
        .join(
            PredictionOutcome,
            PredictionOutcome.prediction_id == DailyPrediction.id,
        )
        .where(DailyPrediction.methodology == METHODOLOGY)
        .where(PredictionOutcome.horizon_days == 1)
        .where(True if not selected_group else Stock.theme == selected_group)
        .distinct()
        .order_by(desc(DailyPrediction.prediction_date))
    ).scalars().all()
    available_iso = [value.isoformat() for value in available_dates]
    target_date = prediction_date or (available_dates[0] if available_dates else None)

    if target_date is None:
        return DailyPredictionResultResponse(
            methodology=METHODOLOGY,
            data_source=DATA_SOURCE,
            selected_group=selected_group,
            available_groups=[],
            available_dates=[],
            prediction_date="",
            result_date="",
            evaluated_predictions=0,
            positive_count=0,
            average_return_pct=0,
            benchmark_return_pct=0,
            excess_return_pct=0,
            win_rate_pct=0,
            direction_accuracy_pct=0,
            average_open_to_close_pct=None,
            items=[],
        )

    rows = db.execute(
        select(DailyPrediction, Stock, PredictionOutcome, DailyPrice)
        .join(Stock, Stock.stock_id == DailyPrediction.stock_id)
        .join(
            PredictionOutcome,
            and_(
                PredictionOutcome.prediction_id == DailyPrediction.id,
                PredictionOutcome.horizon_days == 1,
            ),
        )
        .outerjoin(
            DailyPrice,
            and_(
                DailyPrice.stock_id == DailyPrediction.stock_id,
                DailyPrice.trade_date == PredictionOutcome.exit_date,
            ),
        )
        .where(DailyPrediction.methodology == METHODOLOGY)
        .where(DailyPrediction.prediction_date == target_date)
        .where(True if not selected_group else Stock.theme == selected_group)
        .order_by(DailyPrediction.rank)
        .limit(limit)
    ).all()

    if not rows:
        return DailyPredictionResultResponse(
            methodology=METHODOLOGY,
            data_source=DATA_SOURCE,
            selected_group=selected_group,
            available_groups=_group_options(
                db, prediction_date=target_date, only_evaluated=True
            ),
            available_dates=available_iso,
            prediction_date=target_date.isoformat(),
            result_date="",
            evaluated_predictions=0,
            positive_count=0,
            average_return_pct=0,
            benchmark_return_pct=0,
            excess_return_pct=0,
            win_rate_pct=0,
            direction_accuracy_pct=0,
            average_open_to_close_pct=None,
            items=[],
        )

    all_group_rows = db.execute(
        select(DailyPrediction, PredictionOutcome)
        .join(Stock, Stock.stock_id == DailyPrediction.stock_id)
        .join(
            PredictionOutcome,
            and_(
                PredictionOutcome.prediction_id == DailyPrediction.id,
                PredictionOutcome.horizon_days == 1,
            ),
        )
        .where(DailyPrediction.methodology == METHODOLOGY)
        .where(DailyPrediction.prediction_date == target_date)
        .where(True if not selected_group else Stock.theme == selected_group)
    ).all()

    items = []
    open_to_close_values = []
    for rank, (prediction, stock, outcome, result_price) in enumerate(rows, 1):
        open_to_close = None
        if result_price is not None and result_price.open > 0:
            open_to_close = (outcome.exit_close / result_price.open - 1) * 100
            open_to_close_values.append(open_to_close)
        items.append(
            DailyPredictionResultItem(
                rank=rank,
                stock_id=prediction.stock_id,
                name=stock.name,
                theme=stock.theme,
                signal_score=prediction.signal_score,
                direction=prediction.direction,
                confidence=prediction.confidence,
                prediction_close=prediction.entry_close,
                result_open=result_price.open if result_price is not None else None,
                result_close=outcome.exit_close,
                return_pct=round(outcome.return_pct, 2),
                open_to_close_pct=(
                    round(open_to_close, 2) if open_to_close is not None else None
                ),
                excess_return_pct=round(outcome.excess_return_pct, 2),
                direction_correct=outcome.direction_correct,
            )
        )

    outcomes = [row[1] for row in all_group_rows]
    displayed_outcomes = [row[2] for row in rows]
    count = len(outcomes)
    return DailyPredictionResultResponse(
        methodology=METHODOLOGY,
        data_source=rows[0][0].data_source,
        selected_group=selected_group,
        available_groups=_group_options(
            db, prediction_date=target_date, only_evaluated=True
        ),
        available_dates=available_iso,
        prediction_date=target_date.isoformat(),
        result_date=displayed_outcomes[0].exit_date.isoformat(),
        evaluated_predictions=len(displayed_outcomes),
        positive_count=sum(outcome.return_pct > 0 for outcome in displayed_outcomes),
        average_return_pct=round(
            sum(outcome.return_pct for outcome in displayed_outcomes)
            / len(displayed_outcomes),
            2,
        ),
        benchmark_return_pct=round(
            sum(outcome.return_pct for outcome in outcomes) / count,
            2,
        ),
        excess_return_pct=round(
            sum(outcome.return_pct for outcome in displayed_outcomes)
            / len(displayed_outcomes)
            - sum(outcome.return_pct for outcome in outcomes)
            / count,
            2,
        ),
        win_rate_pct=round(
            sum(outcome.return_pct > 0 for outcome in displayed_outcomes)
            / len(displayed_outcomes)
            * 100,
            1,
        ),
        direction_accuracy_pct=round(
            sum(outcome.direction_correct for outcome in displayed_outcomes)
            / len(displayed_outcomes)
            * 100,
            1,
        ),
        average_open_to_close_pct=(
            round(sum(open_to_close_values) / len(open_to_close_values), 2)
            if open_to_close_values
            else None
        ),
        items=items,
    )
