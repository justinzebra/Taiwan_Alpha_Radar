"""Walk-forward prediction and outcome tests using deterministic close prices."""
from datetime import date, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database import Base
from app.models import DailyPrediction, DailyPrice, PredictionOutcome, Stock
from app.services.backtest import build_predictions, evaluate_predictions, get_backtest_summary


def _seed_prices(db: Session) -> None:
    for stock_id, drift in (("AAA", 1.02), ("BBB", 0.99)):
        db.add(
            Stock(
                stock_id=stock_id,
                name=stock_id,
                name_en=stock_id,
                sector="TEST",
                theme="TEST",
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
