"""Walk-forward end-of-day prediction generation and evaluation."""
from __future__ import annotations

import math
from collections import defaultdict

from datetime import date, datetime, timedelta
from typing import Any

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
from app.domain.universe import StockMeta, all_hot_topics, stocks_for_topic
from app.models import (
    DailyInstitutionalFlow,
    DailyPrediction,
    DailyPrice,
    PredictionOutcome,
    Stock,
)
from app.schemas.backtest import (
    BacktestHorizon,
    BacktestSummary,
    DailyPredictionResultItem,
    DailyPredictionResultResponse,
    PredictionGroupOption,
    PredictionItem,
    PredictionListResponse,
    RegimeBacktestResponse,
    RegimeBacktestRow,
)

METHODOLOGY_V1 = "technical_eod_v1"
METHODOLOGY_V2_CANDIDATE = "technical_eod_v2_candidate"
METHODOLOGY_V3_INSTITUTIONAL = "technical_eod_v3_institutional"
METHODOLOGY_INTRADAY_PREVIEW_V1 = "technical_intraday_preview_v1"
METHODOLOGY_INTRADAY_PREVIEW_V2_CANDIDATE = "technical_intraday_preview_v2_candidate"
METHODOLOGY = METHODOLOGY_V1
SUPPORTED_METHODOLOGIES = {
    METHODOLOGY_V1,
    METHODOLOGY_V2_CANDIDATE,
    METHODOLOGY_V3_INSTITUTIONAL,
    METHODOLOGY_INTRADAY_PREVIEW_V1,
    METHODOLOGY_INTRADAY_PREVIEW_V2_CANDIDATE,
}
DATA_SOURCE = "twse_tpex_official"
REGIME_LABELS = {
    "risk_on": "風險偏多",
    "neutral_positive": "中性偏多",
    "risk_off": "風險偏低",
}
REGIME_ORDER = {
    "risk_on": 0,
    "neutral_positive": 1,
    "risk_off": 2,
}
MODEL_ORDER = {
    METHODOLOGY_V1: 0,
    METHODOLOGY_V2_CANDIDATE: 1,
    METHODOLOGY_V3_INSTITUTIONAL: 2,
}

_EMPTY_FLOW = InstitutionalFlow(0, 0, 0, 0, 0)
_EMPTY_FUNDAMENTALS = Fundamentals(0, 0, 0, 0, 0, 0, 0)


def _normalize_group(theme: str | None) -> str:
    return (theme or "").strip()


def _group_filter(selected_group: str):
    if selected_group.startswith("topic:"):
        stock_ids = stocks_for_topic(selected_group.removeprefix("topic:"))
        return Stock.stock_id.in_(stock_ids or ["__none__"])
    return Stock.theme == selected_group


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

    theme_rows = db.execute(query).all()
    total = sum(count for _, count in theme_rows)
    options = [PredictionGroupOption(value="", label="綜合", count=total)] + [
        PredictionGroupOption(value=theme, label=theme, count=count)
        for theme, count in theme_rows
    ]
    for topic in all_hot_topics():
        stock_ids = stocks_for_topic(topic)
        if not stock_ids:
            continue
        topic_query = (
            select(func.count(DailyPrediction.id))
            .where(DailyPrediction.methodology == methodology)
            .where(DailyPrediction.prediction_date == prediction_date)
            .where(DailyPrediction.stock_id.in_(stock_ids))
        )
        if only_evaluated:
            topic_query = topic_query.join(
                PredictionOutcome,
                and_(
                    PredictionOutcome.prediction_id == DailyPrediction.id,
                    PredictionOutcome.horizon_days == 1,
                ),
            )
        count = db.execute(topic_query).scalar_one()
        if count:
            options.append(
                PredictionGroupOption(
                    value=f"topic:{topic}",
                    label=topic,
                    count=count,
                )
            )
    return options


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


def _is_v2_methodology(methodology: str) -> bool:
    return methodology in {
        METHODOLOGY_V2_CANDIDATE,
        METHODOLOGY_V3_INSTITUTIONAL,
        METHODOLOGY_INTRADAY_PREVIEW_V2_CANDIDATE,
    }


def _is_v3_methodology(methodology: str) -> bool:
    return methodology == METHODOLOGY_V3_INSTITUTIONAL


def _is_preview_methodology(methodology: str) -> bool:
    return methodology in {
        METHODOLOGY_INTRADAY_PREVIEW_V1,
        METHODOLOGY_INTRADAY_PREVIEW_V2_CANDIDATE,
    }


def _market_regime(market_breadth: float) -> str:
    if market_breadth >= 0.6:
        return "risk_on"
    if market_breadth >= 0.5:
        return "neutral_positive"
    return "risk_off"


def _market_breadth_by_date(
    db: Session,
    prediction_dates: set[date],
) -> dict[date, tuple[float, str]]:
    if not prediction_dates:
        return {}
    min_date = min(prediction_dates)
    max_date = max(prediction_dates)
    prices = db.execute(
        select(DailyPrice)
        .where(DailyPrice.trade_date <= max_date)
        # Keep a short lookback before min_date so the earliest prediction
        # date still has a previous close to compare against.
        .where(DailyPrice.trade_date >= min_date - timedelta(days=7))
        .order_by(DailyPrice.stock_id, DailyPrice.trade_date)
    ).scalars().all()
    by_stock: dict[str, list[DailyPrice]] = defaultdict(list)
    for price in prices:
        by_stock[price.stock_id].append(price)

    up_counts: dict[date, int] = defaultdict(int)
    total_counts: dict[date, int] = defaultdict(int)
    for stock_prices in by_stock.values():
        for index in range(1, len(stock_prices)):
            current = stock_prices[index]
            if current.trade_date not in prediction_dates:
                continue
            previous = stock_prices[index - 1]
            if previous.close <= 0:
                continue
            total_counts[current.trade_date] += 1
            if current.close > previous.close:
                up_counts[current.trade_date] += 1

    result = {}
    for current_date in prediction_dates:
        total = total_counts[current_date]
        breadth = up_counts[current_date] / total if total else 0.0
        result[current_date] = (breadth, _market_regime(breadth))
    return result


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


def _institutional_signal(
    *,
    flow: DailyInstitutionalFlow | None,
    prices: list[Any],
) -> tuple[float, str | None, str | None, float | None]:
    if flow is None:
        return 0.0, None, None, None
    avg_volume_k = (
        sum(float(price.volume) for price in prices[-5:]) / len(prices[-5:]) / 1000
        if prices
        else 1.0
    ) or 1.0
    intensity = flow.total_net / avg_volume_k
    adjustment = round(max(-12.0, min(12.0, intensity * 10)), 1)
    if flow.total_net > 0 and flow.foreign_net > 0 and flow.trust_net > 0:
        adjustment += 5
        tag = "institutional_accumulation"
        reason = "外資與投信同步買超，法人買盤支持。"
    elif flow.total_net < 0 and flow.foreign_net < 0 and flow.trust_net < 0:
        adjustment -= 5
        tag = "institutional_distribution"
        reason = "外資與投信同步賣超，法人籌碼轉弱。"
    elif flow.total_net > 0:
        tag = "net_buy"
        reason = "三大法人合計買超，籌碼偏多。"
    elif flow.total_net < 0:
        tag = "net_sell"
        reason = "三大法人合計賣超，籌碼偏空。"
    else:
        tag = "neutral"
        reason = "三大法人合計買賣超接近中性。"
    return round(adjustment, 1), tag, reason, round(intensity, 3)


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
        institutional_foreign_net=prediction.institutional_foreign_net,
        institutional_trust_net=prediction.institutional_trust_net,
        institutional_dealer_net=prediction.institutional_dealer_net,
        institutional_total_net=prediction.institutional_total_net,
        institutional_intensity=prediction.institutional_intensity,
        institutional_tag=prediction.institutional_tag,
        institutional_reason=prediction.institutional_reason,
        is_preview=bool(prediction.is_preview),
        price_status=prediction.price_status or "final_close",
        price_timestamp=(
            prediction.price_timestamp.isoformat()
            if prediction.price_timestamp is not None
            else None
        ),
    )


def _to_candle(price: Any) -> Candle:
    if isinstance(price, Candle):
        return price
    return Candle(
        price.trade_date,
        price.open,
        price.high,
        price.low,
        price.close,
        price.volume,
        price.change_pct,
    )


def build_predictions(
    db: Session,
    *,
    lookback_days: int = 120,
    data_source: str = DATA_SOURCE,
    methodology: str = METHODOLOGY_V1,
    prices_by_stock_override: dict[str, list[Any]] | None = None,
    is_preview: bool = False,
    price_status: str = "final_close",
    price_timestamp: datetime | None = None,
) -> int:
    """Generate recent predictions using only information available that day."""
    methodology = _normalize_methodology(methodology)
    scorer = TechnicalDimension()
    stocks = db.execute(select(Stock)).scalars().all()
    generated: list[DailyPrediction] = []
    prices_by_stock: dict[str, list[DailyPrice]] = {}

    if prices_by_stock_override is None:
        for stock in stocks:
            prices_by_stock[stock.stock_id] = db.execute(
                select(DailyPrice)
                .where(DailyPrice.stock_id == stock.stock_id)
                .order_by(DailyPrice.trade_date)
            ).scalars().all()
    else:
        prices_by_stock = prices_by_stock_override

    market_breadth_by_date: dict[date, float] = {}
    if _is_v2_methodology(methodology):
        dates = {
            price.trade_date
            for prices in prices_by_stock.values()
            for price in prices
        }
        market_breadth_by_date = {
            current_date: calculate_market_breadth(prices_by_stock, current_date)
            for current_date in dates
        }
    institutional_flows: dict[tuple[str, date], DailyInstitutionalFlow] = {}
    if _is_v3_methodology(methodology):
        flows = db.execute(select(DailyInstitutionalFlow)).scalars().all()
        institutional_flows = {
            (flow.stock_id, flow.trade_date): flow for flow in flows
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
            candles = [_to_candle(p) for p in window]
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
            institutional_adjustment = 0.0
            institutional_foreign_net = None
            institutional_trust_net = None
            institutional_dealer_net = None
            institutional_total_net = None
            institutional_intensity = None
            institutional_tag = None
            institutional_reason = None
            if _is_v2_methodology(methodology):
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
            if _is_v3_methodology(methodology):
                flow = institutional_flows.get(
                    (stock.stock_id, prices[index].trade_date)
                )
                (
                    institutional_adjustment,
                    institutional_tag,
                    institutional_reason,
                    institutional_intensity,
                ) = _institutional_signal(flow=flow, prices=window)
                adjusted_score = round(clamp(adjusted_score + institutional_adjustment), 1)
                if flow is not None:
                    institutional_foreign_net = flow.foreign_net
                    institutional_trust_net = flow.trust_net
                    institutional_dealer_net = flow.dealer_net
                    institutional_total_net = flow.total_net
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
                    institutional_foreign_net=institutional_foreign_net,
                    institutional_trust_net=institutional_trust_net,
                    institutional_dealer_net=institutional_dealer_net,
                    institutional_total_net=institutional_total_net,
                    institutional_intensity=institutional_intensity,
                    institutional_tag=institutional_tag,
                    institutional_reason=institutional_reason,
                    is_preview=is_preview,
                    price_status=price_status,
                    price_timestamp=price_timestamp,
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
            if _is_v2_methodology(methodology)
            else (lambda item: item.signal_score)
        )
        predictions.sort(key=rank_key, reverse=True)
        for rank, prediction in enumerate(predictions, 1):
            prediction.rank = rank
            db.add(prediction)
    db.commit()
    return len(generated)


def build_intraday_preview_predictions(
    db: Session,
    *,
    preview_candles_by_stock: dict[str, Candle],
    price_timestamp: datetime,
    data_source: str,
    lookback_days: int = 120,
) -> int:
    """Generate pre-close preview predictions without writing preview prices."""
    if not preview_candles_by_stock:
        return 0

    stocks = db.execute(select(Stock)).scalars().all()
    prices_by_stock: dict[str, list[Any]] = {}
    for stock in stocks:
        history = db.execute(
            select(DailyPrice)
            .where(DailyPrice.stock_id == stock.stock_id)
            .order_by(DailyPrice.trade_date)
        ).scalars().all()
        preview = preview_candles_by_stock.get(stock.stock_id)
        if preview is None or not history:
            prices_by_stock[stock.stock_id] = []
            continue
        usable = [price for price in history if price.trade_date < preview.trade_date]
        usable.append(preview)
        prices_by_stock[stock.stock_id] = usable

    total = 0
    for methodology in (
        METHODOLOGY_INTRADAY_PREVIEW_V1,
        METHODOLOGY_INTRADAY_PREVIEW_V2_CANDIDATE,
    ):
        total += build_predictions(
            db,
            lookback_days=lookback_days,
            data_source=data_source,
            methodology=methodology,
            prices_by_stock_override=prices_by_stock,
            is_preview=True,
            price_status="intraday_preview",
            price_timestamp=price_timestamp,
        )
    return total


def build_all_predictions(
    db: Session,
    *,
    lookback_days: int = 120,
    data_source: str = DATA_SOURCE,
) -> int:
    total = 0
    for methodology in (
        METHODOLOGY_V1,
        METHODOLOGY_V2_CANDIDATE,
        METHODOLOGY_V3_INSTITUTIONAL,
    ):
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
    for methodology in (
        METHODOLOGY_V1,
        METHODOLOGY_V2_CANDIDATE,
        METHODOLOGY_V3_INSTITUTIONAL,
    ):
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
    start_date: date | None = None,
) -> BacktestSummary:
    methodology = _normalize_methodology(methodology)
    prediction_query = select(DailyPrediction).where(
        DailyPrediction.methodology == methodology
    )
    if start_date is not None:
        prediction_query = prediction_query.where(
            DailyPrediction.prediction_date >= start_date
        )
    predictions = db.execute(prediction_query).scalars().all()
    if not predictions:
        return BacktestSummary(
            methodology=methodology,
            data_source=DATA_SOURCE,
            prediction_start="",
            prediction_end="",
            horizons=[],
        )
    prediction_by_id = {prediction.id: prediction for prediction in predictions}
    outcome_query = (
        select(PredictionOutcome)
        .join(DailyPrediction, DailyPrediction.id == PredictionOutcome.prediction_id)
        .where(DailyPrediction.methodology == methodology)
        .where(DailyPrediction.id.in_(prediction_by_id.keys()))
    )
    outcomes = db.execute(outcome_query).scalars().all()
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


def get_regime_backtest_summary(
    db: Session,
    *,
    start_date: date | None = None,
) -> RegimeBacktestResponse:
    methodologies = (
        METHODOLOGY_V1,
        METHODOLOGY_V2_CANDIDATE,
        METHODOLOGY_V3_INSTITUTIONAL,
    )
    prediction_query = (
        select(DailyPrediction)
        .where(DailyPrediction.methodology.in_(methodologies))
        .where(DailyPrediction.is_preview.is_(False))
    )
    if start_date is not None:
        prediction_query = prediction_query.where(
            DailyPrediction.prediction_date >= start_date
        )
    predictions = db.execute(prediction_query).scalars().all()
    if not predictions:
        return RegimeBacktestResponse(
            data_source=DATA_SOURCE,
            prediction_start="",
            prediction_end="",
            rows=[],
        )

    prediction_by_id = {prediction.id: prediction for prediction in predictions}
    prediction_dates = {prediction.prediction_date for prediction in predictions}
    regimes_by_date = _market_breadth_by_date(db, prediction_dates)

    outcomes = db.execute(
        select(PredictionOutcome)
        .join(DailyPrediction, DailyPrediction.id == PredictionOutcome.prediction_id)
        .where(DailyPrediction.id.in_(prediction_by_id.keys()))
    ).scalars().all()
    grouped: dict[tuple[str, str, int], list[tuple[PredictionOutcome, float]]] = (
        defaultdict(list)
    )
    for outcome in outcomes:
        prediction = prediction_by_id.get(outcome.prediction_id)
        if prediction is None or prediction.rank > 10:
            continue
        breadth, regime = regimes_by_date.get(
            prediction.prediction_date,
            (0.0, "risk_off"),
        )
        grouped[
            (prediction.methodology, regime, outcome.horizon_days)
        ].append((outcome, breadth))

    rows = []
    for (methodology, regime, horizon), items in grouped.items():
        if not items:
            continue
        regime_outcomes = [item[0] for item in items]
        breadth_values = [item[1] for item in items]
        rows.append(
            RegimeBacktestRow(
                methodology=methodology,
                market_regime=regime,
                market_regime_label=REGIME_LABELS.get(regime, regime),
                horizon_days=horizon,
                evaluated_predictions=len(regime_outcomes),
                average_market_breadth_pct=round(
                    sum(breadth_values) / len(breadth_values) * 100,
                    1,
                ),
                top10_average_return_pct=round(
                    sum(row.return_pct for row in regime_outcomes)
                    / len(regime_outcomes),
                    2,
                ),
                benchmark_return_pct=round(
                    sum(row.benchmark_return_pct for row in regime_outcomes)
                    / len(regime_outcomes),
                    2,
                ),
                top10_excess_return_pct=round(
                    sum(row.excess_return_pct for row in regime_outcomes)
                    / len(regime_outcomes),
                    2,
                ),
                top10_win_rate_pct=round(
                    sum(row.return_pct > 0 for row in regime_outcomes)
                    / len(regime_outcomes)
                    * 100,
                    1,
                ),
                direction_accuracy_pct=round(
                    sum(row.direction_correct for row in regime_outcomes)
                    / len(regime_outcomes)
                    * 100,
                    1,
                ),
            )
        )

    dates = [prediction.prediction_date for prediction in predictions]
    rows.sort(
        key=lambda row: (
            REGIME_ORDER.get(row.market_regime, 99),
            row.horizon_days,
            MODEL_ORDER.get(row.methodology, 99),
        )
    )
    return RegimeBacktestResponse(
        data_source=predictions[0].data_source,
        prediction_start=min(dates).isoformat(),
        prediction_end=max(dates).isoformat(),
        rows=rows,
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
            is_preview=_is_preview_methodology(methodology),
            price_status=(
                "intraday_preview"
                if _is_preview_methodology(methodology)
                else "final_close"
            ),
            price_timestamp=None,
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
        query = query.where(_group_filter(selected_group))
    rows = db.execute(query.limit(limit)).all()
    return PredictionListResponse(
        as_of=latest.isoformat(),
        methodology=methodology,
        data_source=rows[0][0].data_source if rows else DATA_SOURCE,
        is_preview=bool(rows[0][0].is_preview) if rows else _is_preview_methodology(methodology),
        price_status=(
            rows[0][0].price_status or "final_close"
            if rows
            else (
                "intraday_preview"
                if _is_preview_methodology(methodology)
                else "final_close"
            )
        ),
        price_timestamp=(
            rows[0][0].price_timestamp.isoformat()
            if rows and rows[0][0].price_timestamp is not None
            else None
        ),
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
        .where(True if not selected_group else _group_filter(selected_group))
        .distinct()
        .order_by(desc(DailyPrediction.prediction_date))
    ).scalars().all()
    available_iso = [value.isoformat() for value in available_dates]
    target_date = prediction_date or (available_dates[0] if available_dates else None)

    if target_date is None:
        return DailyPredictionResultResponse(
            methodology=methodology,
            data_source=DATA_SOURCE,
            is_preview=_is_preview_methodology(methodology),
            price_status=(
                "intraday_preview"
                if _is_preview_methodology(methodology)
                else "final_close"
            ),
            price_timestamp=None,
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
        .where(True if not selected_group else _group_filter(selected_group))
        .order_by(DailyPrediction.rank)
        .limit(limit)
    ).all()

    if not rows:
        return DailyPredictionResultResponse(
            methodology=methodology,
            data_source=DATA_SOURCE,
            is_preview=_is_preview_methodology(methodology),
            price_status=(
                "intraday_preview"
                if _is_preview_methodology(methodology)
                else "final_close"
            ),
            price_timestamp=None,
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
        .where(True if not selected_group else _group_filter(selected_group))
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
                institutional_foreign_net=prediction.institutional_foreign_net,
                institutional_trust_net=prediction.institutional_trust_net,
                institutional_dealer_net=prediction.institutional_dealer_net,
                institutional_total_net=prediction.institutional_total_net,
                institutional_intensity=prediction.institutional_intensity,
                institutional_tag=prediction.institutional_tag,
                institutional_reason=prediction.institutional_reason,
                is_preview=bool(prediction.is_preview),
                price_status=prediction.price_status or "final_close",
                price_timestamp=(
                    prediction.price_timestamp.isoformat()
                    if prediction.price_timestamp is not None
                    else None
                ),
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
        is_preview=bool(rows[0][0].is_preview),
        price_status=rows[0][0].price_status or "final_close",
        price_timestamp=(
            rows[0][0].price_timestamp.isoformat()
            if rows[0][0].price_timestamp is not None
            else None
        ),
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
