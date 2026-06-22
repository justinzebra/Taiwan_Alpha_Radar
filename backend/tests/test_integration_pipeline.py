"""End-to-end integration test.

Runs the full daily pipeline against a real (SQLite) database, then verifies the
read-side query service and the FastAPI endpoints return coherent data. This
exercises: collectors -> alpha engine -> persistence -> queries -> API.
"""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - register tables on Base.metadata
from app.database import Base, get_db
from app.domain.simulator import Candle
from app.main import app
from app.models import DailyPrice, Stock
from app.services import queries
from app.services.pipeline import (
    run_daily_pipeline,
    run_intraday_preview_pipeline,
    sync_universe,
)

AS_OF = date(2026, 6, 10)


class FakeIntradayCollector:
    source = "test_intraday_preview"

    def fetch_snapshot(self, meta, at):
        return type(
            "Snapshot",
            (),
            {
                "stock_id": meta.stock_id,
                "timestamp": datetime(2026, 6, 11, 10, 30),
                "source": self.source,
                "candle": Candle(
                    trade_date=date(2026, 6, 11),
                    open=meta.base_price,
                    high=round(meta.base_price * 1.02, 2),
                    low=round(meta.base_price * 0.99, 2),
                    close=round(meta.base_price * 1.01, 2),
                    volume=1_000_000,
                    change_pct=1.0,
                ),
            },
        )()


@pytest.fixture(scope="module")
def db_session(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("data") / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    session = TestingSession()
    run_daily_pipeline(session, AS_OF)  # populate once for the whole module
    # Ensure no stale cache from a previous run / live Redis affects assertions.
    from app.services.cache import cache_clear

    cache_clear()
    yield TestingSession
    session.close()


@pytest.fixture(scope="module")
def client(db_session):
    def _override():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_pipeline_populates_all_tables(db_session):
    db = db_session()
    try:
        market = queries.get_market(db)
        assert market is not None
        assert 0 <= market.temperature_score <= 100
        assert len(market.indices) == 2

        stocks = queries.list_stocks(db, page=1, page_size=100)
        assert stocks.total >= 30
        # Ranks are unique and start at 1.
        ranks = sorted(s.rank for s in stocks.items)
        assert ranks[0] == 1

        sectors = queries.get_sectors(db)
        assert len(sectors.sectors) >= 4

        dashboard = queries.get_dashboard(db)
        assert dashboard is not None
        assert len(dashboard.top_stocks) == 10
        assert sum(b.count for b in dashboard.score_distribution) == stocks.total
    finally:
        db.close()


def test_api_dashboard_endpoint(client):
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert "market" in body
    assert len(body["top_stocks"]) == 10
    assert body["data_status"]["price_source"] == "mock"
    assert body["data_status"]["prediction_methodology"] == "technical_eod_v1"


def test_api_backtest_endpoint(client):
    res = client.get("/api/backtest")
    assert res.status_code == 200
    body = res.json()
    assert body["methodology"] == "technical_eod_v1"
    assert {item["horizon_days"] for item in body["horizons"]} == {1, 3, 5, 10}

    v2 = client.get(
        "/api/backtest",
        params={"methodology": "technical_eod_v2_candidate"},
    )
    assert v2.status_code == 200
    v2_body = v2.json()
    assert v2_body["methodology"] == "technical_eod_v2_candidate"
    assert {item["horizon_days"] for item in v2_body["horizons"]} == {1, 3, 5, 10}


def test_api_predictions_returns_latest_ranked_signals(client):
    res = client.get("/api/predictions", params={"limit": 10})
    assert res.status_code == 200
    body = res.json()
    assert body["methodology"] == "technical_eod_v1"
    assert len(body["items"]) == 10
    assert [item["rank"] for item in body["items"]] == list(range(1, 11))
    assert all(item["direction"] in {"偏多", "中性", "偏空"} for item in body["items"])

    v2 = client.get(
        "/api/predictions",
        params={"limit": 10, "methodology": "technical_eod_v2_candidate"},
    )
    assert v2.status_code == 200
    v2_body = v2.json()
    assert v2_body["methodology"] == "technical_eod_v2_candidate"
    assert len(v2_body["items"]) == 10
    assert all("adjusted_score" in item for item in v2_body["items"])
    assert all(item["quality_tag"] for item in v2_body["items"])


def test_api_prediction_results_returns_daily_scorecard(client):
    res = client.get("/api/prediction-results", params={"limit": 10})
    assert res.status_code == 200
    body = res.json()
    assert body["methodology"] == "technical_eod_v1"
    assert body["available_dates"]
    assert body["prediction_date"]
    assert body["result_date"]
    assert len(body["items"]) == 10
    assert all("direction_correct" in item for item in body["items"])

    v2 = client.get(
        "/api/prediction-results",
        params={"limit": 10, "methodology": "technical_eod_v2_candidate"},
    )
    assert v2.status_code == 200
    v2_body = v2.json()
    assert v2_body["methodology"] == "technical_eod_v2_candidate"
    assert len(v2_body["items"]) == 10
    assert all("market_breadth" in item for item in v2_body["items"])


def test_api_stocks_search_and_sort(client):
    res = client.get("/api/stocks", params={"search": "2330", "sort": "score"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(i["stock_id"] == "2330" for i in items)


def test_api_stock_detail_has_dimensions(client):
    res = client.get("/api/stocks/2330")
    assert res.status_code == 200
    body = res.json()
    assert body["stock_id"] == "2330"
    assert len(body["dimensions"]) == 5
    assert len(body["price_history"]) > 0


def test_top_ranked_stock_has_ai_report(client):
    # The #1 ranked stock is always within the AI-report top-N set.
    top = client.get("/api/stocks", params={"sort": "rank", "page_size": 1}).json()
    top_id = top["items"][0]["stock_id"]

    res = client.get(f"/api/stocks/{top_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["ai_report"] is not None
    assert body["ai_report"]["summary"]
    assert body["ai_report"]["highlights"]


def test_api_unknown_stock_returns_404(client):
    res = client.get("/api/stocks/9999")
    assert res.status_code == 404


def test_pipeline_keeps_price_history_across_analysis_dates(db_session):
    db = db_session()
    try:
        before = db.query(DailyPrice).count()
        run_daily_pipeline(db, date(2026, 6, 11))
        after = db.query(DailyPrice).count()
        assert after > before
    finally:
        db.close()


def test_intraday_preview_predictions_are_marked_and_not_backtested(db_session, client):
    db = db_session()
    try:
        summary = run_intraday_preview_pipeline(
            db,
            date(2026, 6, 11),
            quote_collector=FakeIntradayCollector(),
        )
        assert summary["status"] == "ok"
        assert summary["quote_count"] >= 30
        assert summary["predictions"] > 0
    finally:
        db.close()

    res = client.get(
        "/api/predictions",
        params={"methodology": "technical_intraday_preview_v2_candidate"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["is_preview"] is True
    assert body["price_status"] == "intraday_preview"
    assert body["price_timestamp"]
    assert len(body["items"]) == 10
    assert all(item["is_preview"] for item in body["items"])

    backtest = client.get(
        "/api/backtest",
        params={"methodology": "technical_intraday_preview_v2_candidate"},
    )
    assert backtest.status_code == 200
    assert backtest.json()["horizons"] == []


def test_sync_universe_updates_existing_market_metadata(db_session):
    db = db_session()
    try:
        stock = db.get(Stock, "3324")
        stock.market = "TWSE"
        db.commit()

        sync_universe(db)

        assert db.get(Stock, "3324").market == "TPEx"
    finally:
        db.close()
