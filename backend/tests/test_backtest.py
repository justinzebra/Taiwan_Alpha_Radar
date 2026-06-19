"""Walk-forward prediction and outcome tests using deterministic close prices."""
from datetime import date, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database import Base
from app.models import DailyPrediction, DailyPrice, PredictionOutcome, Stock
from app.services.backtest import (
    build_predictions,
    evaluate_predictions,
    get_backtest_summary,
    get_daily_prediction_results,
)


def _seed_prices(db: Session) -> None:
    for stock_id, drift, theme in (
        ("AAA", 1.02, "UP"),
        ("BBB", 0.99, "DOWN"),
    ):
        db.add(
            Stock(
                stock_id=stock_id,
                name=stock_id,
                name_en=stock_id,
                sector="TEST",
                theme=theme,
                market="TWSE",
                market_cap_billion=1,
            )
        )
        price = 100.0
        for offset in range(90):
            day = date(2026, 1, 1) + timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            previous = price
            price *= drift
            db.add(
                DailyPrice(
                    stock_id=stock_id,
                    trade_date=day,
                    open=previous,
                    high=max(previous, price),
                    low=min(previous, price),
                    close=price,
                    volume=1_000_000,
                    change_pct=(price / previous - 1) * 100,
                )
            )
    db.commit()


def test_walk_forward_predictions_do_not_use_future_prices():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_prices(db)
        build_predictions(db, lookback_days=30)

        predictions = db.execute(
            select(DailyPrediction).where(DailyPrediction.stock_id == "AAA")
        ).scalars().all()

        assert predictions
        assert all(p.methodology == "technical_eod_v1" for p in predictions)
        assert predictions[-1].direction == "偏多"
        assert predictions[-1].data_source == "twse_tpex_official"


def test_outcomes_cover_requested_horizons_and_compare_equal_weight_benchmark():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_prices(db)
        build_predictions(db, lookback_days=20)
        evaluate_predictions(db, horizons=(1, 3, 5, 10))

        horizons = set(
            db.execute(select(PredictionOutcome.horizon_days)).scalars().all()
        )
        summary = get_backtest_summary(db)

        assert horizons == {1, 3, 5, 10}
        assert summary.methodology == "technical_eod_v1"
        assert summary.horizons
        assert summary.horizons[0].evaluated_predictions > 0
        assert summary.horizons[0].top10_excess_return_pct != 0


def test_rebuilding_predictions_is_idempotent():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_prices(db)
        build_predictions(db, lookback_days=10)
        first = db.query(DailyPrediction).count()
        build_predictions(db, lookback_days=10)

        assert db.query(DailyPrediction).count() == first


def test_daily_prediction_results_show_next_session_scorecard():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_prices(db)
        build_predictions(db, lookback_days=20)
        evaluate_predictions(db, horizons=(1,))

        result = get_daily_prediction_results(db, limit=10)

        assert result.available_dates
        assert result.prediction_date
        assert result.result_date
        assert result.evaluated_predictions == 2
        assert len(result.items) == 2
        assert result.items[0].rank == 1
        assert result.items[0].result_open is not None
        assert result.items[0].open_to_close_pct is not None


def test_prediction_lists_can_filter_by_theme_with_local_rank():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_prices(db)
        build_predictions(db, lookback_days=20)
        evaluate_predictions(db, horizons=(1,))

        from app.services.backtest import get_latest_predictions

        predictions = get_latest_predictions(db, theme="DOWN")
        result = get_daily_prediction_results(db, theme="DOWN")

        assert [group.value for group in predictions.available_groups] == [
            "",
            "DOWN",
            "UP",
        ]
        assert predictions.selected_group == "DOWN"
        assert len(predictions.items) == 1
        assert predictions.items[0].rank == 1
        assert predictions.items[0].theme == "DOWN"
        assert result.selected_group == "DOWN"
        assert result.evaluated_predictions == 1
        assert result.items[0].rank == 1
        assert result.items[0].theme == "DOWN"
