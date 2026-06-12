"""End-to-end integration test.

Runs the full daily pipeline against a real (SQLite) database, then verifies the
read-side query service and the FastAPI endpoints return coherent data. This
exercises: collectors -> alpha engine -> persistence -> queries -> API.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - register tables on Base.metadata
from app.database import Base, get_db
from app.main import app
from app.services import queries
from app.services.pipeline import run_daily_pipeline

AS_OF = date(2026, 6, 10)


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
