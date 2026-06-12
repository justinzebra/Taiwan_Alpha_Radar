"""Unit tests for the AI report engine (mock provider)."""
from datetime import date

from app.ai import get_report_engine
from app.alpha import StockScoreEngine
from app.collectors import get_collectors
from app.domain.universe import get_stock


def test_mock_report_has_all_sections():
    engine = StockScoreEngine(get_collectors("mock"), history_days=120)
    score = engine.score(get_stock("2330"), date(2026, 6, 10))
    report = get_report_engine("mock").generate(score)

    assert report.provider == "mock"
    assert report.summary
    assert report.highlights
    assert report.risks
    assert report.short_term
    assert report.mid_term
