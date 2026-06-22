"""Walk-forward end-of-day prediction generation and evaluation."""
from __future__ import annotations

import math
from collections import defaultdict

from datetime import date

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.orm import Session

from app.alpha.base import StockContext
from app.alpha.dimensions.technical import TechnicalDimension
from app.alpha.features.technical_features import (
    calculate_market_breadth,
    calculate_rsi_14,
    calculate_volume_confirm,
)
from app.alpha.indicators import clamp
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

METHODOLOGY_V1 = "technical_eod_v1"
METHODOLOGY_V2_CANDIDATE = "technical_eod_v2_candidate"
METHODOLOGY = METHODOLOGY_V1
SUPPORTED_METHODOLOGIES = {METHODOLOGY_V1, METHODOLOGY_V2_CANDIDATE}
DATA_SOURCE = "twse_tpex_official"

_EMPTY_FLOW = InstitutionalFlow(0, 0, 0, 0, 0)
_EMPTY_FUNDAMENTALS = Fundamentals(0, 0, 0, 0, 0, 0, 0)


def _normalize_group(theme: str | None) -> str:
    return (theme or "").strip()


def _group_options(
    db: Session,
    *,
    prediction_date: date,
    methodology: str = METHODOLOGY_V1,
    only_evaluated: bool = False,
) -> list[PredictionGroupOption]:
    query = (
        select(Stock.theme, func.count(DailyPrediction.id))
        .join(DailyPrediction, DailyPrediction.stock_id == Stock.stock_id)
        .where(DailyPrediction.methodology == methodology)
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


def _normalize_methodology(methodology: str) -> str:
    if methodology not in SUPPORTED_METHODOLOGIES:
        raise ValueError(f"Unsupported methodology: {methodology}")
    return methodology


def _market_regime(market_breadth: float) -> str:
    if market_breadth >= 0.6:
        return "risk_on"
    if market_breadth >= 0.5:
        return "neutral_positive"
    return "risk_off"


def _quality_tag(
    *,
    signal_score: float,
    market_breadth: float,
    rsi_14: float,
    volume_confirm: bool,
) -> str:
    if (
        signal_score >= 60
        and market_breadth >= 0.5
        and 50 <= rsi_14 <= 70
        and volume_confirm
    ):
        return "high_quality"
    if signal_score >= 60 and market_breadth >= 0.5:
        return "market_supported"
    if signal_score >= 60 and market_breadth < 0.5:
        return "watch_only"
    return "neutral"


def _quality_reason(
    *,
    signal_score: float,
    market_breadth: float,
    rsi_14: float,
    volume_confirm: bool,
    quality_tag: str,
) -> str:
    breadth_pct = round(market_breadth * 100)
    if quality_tag == "high_quality":
        return (
            f"市場廣度達 {breadth_pct}%，個股技術分數偏多，"
            "RSI 位於健康強勢區間，且有量價確認。"
        )
    if quality_tag == "market_supported":
        parts = [f"市場廣度達 {breadth_pct}%，個股技術分數偏多。"]
        if not 50 <= rsi_14 <= 70:
            parts.append("RSI 未落在 50 至 70 的健康強勢區間。")
        if not volume_confirm:
            parts.append("量價確認尚未成立。")
        return "".join(parts)
    if quality_tag == "watch_only":
        return (
            f"個股技術分數偏多，但市場廣度僅 {breadth_pct}%，"
            "屬於弱勢環境下的觀察訊號。"
        )
    return "技術分數尚未達偏多門檻，維持中性觀察。"


def _adjusted_score(
    signal_score: float,
    *,
    market_breadth: float,
    quality_tag: str,
) -> float:
    adjusted = signal_score
    if market_breadth < 0.5:
        adjusted -= 8
    if quality_tag == "high_quality":
        adjusted += 6
    elif quality_tag == "market_supported":
        adjusted += 3
    elif quality_tag == "watch_only":
        adjusted -= 5
    return round(clamp(adjusted), 1)


def _prediction_item(
    prediction: DailyPrediction,
    stock: Stock,
    *,
    rank: int,
) -> PredictionItem:
    return PredictionItem(
        rank=rank,
        stock_id=prediction.stock_id,
        name=stock.name,
        theme=stock.theme,
        signal_score=prediction.signal_score,
        adjusted_score=(
            prediction.adjusted_score
            if prediction.adjusted_score is not None
            else prediction.signal_score
        ),
        direction=prediction.direction,
        confidence=prediction.confidence,
        entry_close=prediction.entry_close,
        market_breadth=prediction.market_breadth,
        market_regime=prediction.market_regime,
        quality_tag=prediction.quality_tag,
        quality_reason=prediction.quality_reason,
    )


def build_predictions(
    db: Session,
    *,
    lookback_days: int = 120,
    data_source: str = DATA_SOURCE,
    methodology: str = METHODOLOGY_V1,
) -> int:
    """Generate recent predictions using only information available that day."""
    methodology = _normalize_methodology(methodology)
    scorer = TechnicalDimension()
    stocks = db.execute(select(Stock)).scalars().all()
    generated: list[DailyPrediction] = []
    prices_by_stock: dict[str, list[DailyPrice]] = {}

    for stock in stocks:
        prices_by_stock[stock.stock_id] = db.execute(
            select(DailyPrice)
            .where(DailyPrice.stock_id == stock.stock_id)
            .order_by(DailyPrice.trade_date)
        ).scalars().all()

    market_breadth_by_date: dict[date, float] = {}
    if methodology == METHODOLOGY_V2_CANDIDATE:
        dates = {
            price.trade_date
            for prices in prices_by_stock.values()
            for price in prices
        }
        market_breadth_by_date = {
            current_date: calculate_market_breadth(prices_by_stock, current_date)
            for current_date in dates
        }

    for stock in stocks:
        prices = prices_by_stock[stock.stock_id]
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
            adjusted_score = score
            market_breadth = None
            market_regime = None
            quality_tag = None
            quality_reason = None
            if methodology == METHODOLOGY_V2_CANDIDATE:
                market_breadth = market_breadth_by_date.get(prices[index].trade_date, 0.0)
                rsi_14 = calculate_rsi_14(window)
                volume_confirm = calculate_volume_confirm(window)
                market_regime = _market_regime(market_breadth)
                quality_tag = _quality_tag(
                    signal_score=score,
                    market_breadth=market_breadth,
                    rsi_14=rsi_14,
                    volume_confirm=volume_confirm,
                )
                quality_reason = _quality_reason(
                    signal_score=score,
                    market_breadth=market_breadth,
                    rsi_14=rsi_14,
                    volume_confirm=volume_confirm,
                    quality_tag=quality_tag,
                )
                adjusted_score = _adjusted_score(
                    score,
                    market_breadth=market_breadth,
                    quality_tag=quality_tag,
                )
            generated.append(
                DailyPrediction(
                    stock_id=stock.stock_id,
                    prediction_date=prices[index].trade_date,
                    methodology=methodology,
                    data_source=data_source,
                    signal_score=score,
                    adjusted_score=adjusted_score,
                    direction=_direction(score),
                    confidence=round(min(100.0, abs(score - 50) * 2), 1),
                    rank=0,
                    entry_close=prices[index].close,
                    market_breadth=market_breadth,
                    market_regime=market_regime,
                    quality_tag=quality_tag,
                    quality_reason=quality_reason,
                )
            )

    if not generated:
        return 0

    prediction_dates = {prediction.prediction_date for prediction in generated}
    existing_ids = db.execute(
        select(DailyPrediction.id)
        .where(DailyPrediction.methodology == methodology)
        .where(DailyPrediction.prediction_date.in_(prediction_dates))
    ).scalars().all()
    if existing_ids:
        db.execute(
            delete(PredictionOutcome).where(
                PredictionOutcome.prediction_id.in_(existing_ids)
            )
        )
    db.execute(
        delete(DailyPrediction)
        .where(DailyPrediction.methodology == methodology)
        .where(DailyPrediction.prediction_date.in_(prediction_dates))
    )
    by_date: dict = defaultdict(list)
    for prediction in generated:
        by_date[prediction.prediction_date].append(prediction)
    for predictions in by_date.values():
        rank_key = (
            (lambda item: item.adjusted_score or item.signal_score)
            if methodology == METHODOLOGY_V2_CANDIDATE
            else (lambda item: item.signal_score)
        )
        predictions.sort(key=rank_key, reverse=True)
        for rank, prediction in enumerate(predictions, 1):
            prediction.rank = rank
            db.add(prediction)
    db.commit()
    return len(generated)


def build_all_predictions(
    db: Session,
    *,
    lookback_days: int = 120,
    data_source: str = DATA_SOURCE,
) -> int:
    total = 0
    for methodology in (METHODOLOGY_V1, METHODOLOGY_V2_CANDIDATE):
        total += build_predictions(
            db,
            lookback_days=lookback_days,
            data_source=data_source,
            methodology=methodology,
        )
    return total


def evaluate_predictions(
    db: Session,
    *,
    horizons: tuple[int, ...] = (1, 3, 5, 10),
    methodology: str = METHODOLOGY_V1,
) -> int:
    methodology = _normalize_methodology(methodology)
    predictions = db.execute(
        select(DailyPrediction).where(DailyPrediction.methodology == methodology)
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
            (
                i
                for i, price in enumerate(prices)
                if price.trade_date == prediction.prediction_date
            ),
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

    prediction_ids = [prediction.id for prediction in predictions]
    if prediction_ids:
        db.execute(
            delete(PredictionOutcome).where(
                PredictionOutcome.prediction_id.in_(prediction_ids)
            )
        )
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


def evaluate_all_predictions(
    db: Session,
    *,
    horizons: tuple[int, ...] = (1, 3, 5, 10),
) -> int:
    total = 0
    for methodology in (METHODOLOGY_V1, METHODOLOGY_V2_CANDIDATE):
        total += evaluate_predictions(
            db,
            horizons=horizons,
            methodology=methodology,
        )
    return total


def get_backtest_summary(
    db: Session,
    *,
    methodology: str = METHODOLOGY_V1,
) -> BacktestSummary:
    methodology = _normalize_methodology(methodology)
    predictions = db.execute(
        select(DailyPrediction).where(DailyPrediction.methodology == methodology)
    ).scalars().all()
    if not predictions:
        return BacktestSummary(
            methodology=methodology,
            data_source=DATA_SOURCE,
            prediction_start="",
            prediction_end="",
            horizons=[],
        )
    prediction_by_id = {prediction.id: prediction for prediction in predictions}
    outcomes = db.execute(
        select(PredictionOutcome)
        .join(DailyPrediction, DailyPrediction.id == PredictionOutcome.prediction_id)
        .where(DailyPrediction.methodology == methodology)
    ).scalars().all()
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
        methodology=methodology,
        data_source=predictions[0].data_source,
        prediction_start=min(dates).isoformat(),
        prediction_end=max(dates).isoformat(),
        horizons=horizon_rows,
    )


def get_latest_predictions(
    db: Session,
    limit: int = 10,
    theme: str | None = None,
    methodology: str = METHODOLOGY_V1,
) -> PredictionListResponse:
    methodology = _normalize_methodology(methodology)
    latest = db.execute(
        select(func.max(DailyPrediction.prediction_date)).where(
            DailyPrediction.methodology == methodology
        )
    ).scalar_one_or_none()
    selected_group = _normalize_group(theme)
    if latest is None:
        return PredictionListResponse(
            as_of="",
            methodology=methodology,
            data_source=DATA_SOURCE,
            selected_group=selected_group,
            available_groups=[],
            items=[],
        )
    query = (
        select(DailyPrediction, Stock)
        .join(Stock, Stock.stock_id == DailyPrediction.stock_id)
        .where(DailyPrediction.methodology == methodology)
        .where(DailyPrediction.prediction_date == latest)
        .order_by(DailyPrediction.rank)
    )
    if selected_group:
        query = query.where(Stock.theme == selected_group)
    rows = db.execute(query.limit(limit)).all()
    return PredictionListResponse(
        as_of=latest.isoformat(),
        methodology=methodology,
        data_source=rows[0][0].data_source if rows else DATA_SOURCE,
        selected_group=selected_group,
        available_groups=_group_options(
            db, prediction_date=latest, methodology=methodology
        ),
        items=[
            _prediction_item(prediction, stock, rank=rank)
            for rank, (prediction, stock) in enumerate(rows, 1)
        ],
    )


def get_daily_prediction_results(
    db: Session,
    *,
    prediction_date: date | None = None,
    limit: int = 10,
    theme: str | None = None,
    methodology: str = METHODOLOGY_V1,
) -> DailyPredictionResultResponse:
    """Return one prediction day's next-session results and summary."""
    methodology = _normalize_methodology(methodology)
    selected_group = _normalize_group(theme)
    available_dates = db.execute(
        select(DailyPrediction.prediction_date)
        .join(Stock, Stock.stock_id == DailyPrediction.stock_id)
        .join(
            PredictionOutcome,
            PredictionOutcome.prediction_id == DailyPrediction.id,
        )
        .where(DailyPrediction.methodology == methodology)
        .where(PredictionOutcome.horizon_days == 1)
        .where(True if not selected_group else Stock.theme == selected_group)
        .distinct()
        .order_by(desc(DailyPrediction.prediction_date))
    ).scalars().all()
    available_iso = [value.isoformat() for value in available_dates]
    target_date = prediction_date or (available_dates[0] if available_dates else None)

    if target_date is None:
        return DailyPredictionResultResponse(
            methodology=methodology,
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
        .where(DailyPrediction.methodology == methodology)
        .where(DailyPrediction.prediction_date == target_date)
        .where(True if not selected_group else Stock.theme == selected_group)
        .order_by(DailyPrediction.rank)
        .limit(limit)
    ).all()

    if not rows:
        return DailyPredictionResultResponse(
            methodology=methodology,
            data_source=DATA_SOURCE,
            selected_group=selected_group,
            available_groups=_group_options(
                db,
                prediction_date=target_date,
                methodology=methodology,
                only_evaluated=True,
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
        .where(DailyPrediction.methodology == methodology)
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
                adjusted_score=(
                    prediction.adjusted_score
                    if prediction.adjusted_score is not None
                    else prediction.signal_score
                ),
                direction=prediction.direction,
                confidence=prediction.confidence,
                prediction_close=prediction.entry_close,
                market_breadth=prediction.market_breadth,
                market_regime=prediction.market_regime,
                quality_tag=prediction.quality_tag,
                quality_reason=prediction.quality_reason,
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
        methodology=methodology,
        data_source=rows[0][0].data_source,
        selected_group=selected_group,
        available_groups=_group_options(
            db,
            prediction_date=target_date,
            methodology=methodology,
            only_evaluated=True,
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
