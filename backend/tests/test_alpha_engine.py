"""Unit tests for the alpha scoring engine."""
from datetime import date

import pytest

from app.alpha import StockScoreEngine, aggregate_sectors, compute_market_score
from app.alpha.dimensions import ALL_DIMENSIONS
from app.collectors import get_collectors
from app.domain.universe import UNIVERSE, get_stock

AS_OF = date(2026, 6, 10)


@pytest.fixture(scope="module")
def engine() -> StockScoreEngine:
    return StockScoreEngine(get_collectors("mock"), history_days=120)


def test_dimension_weights_sum_to_one():
    total = sum(d.weight for d in ALL_DIMENSIONS)
    assert abs(total - 1.0) < 1e-9


def test_score_is_between_0_and_100(engine):
    meta = get_stock("2330")
    result = engine.score(meta, AS_OF)
    assert result is not None
    assert 0 <= result.total_score <= 100
    assert len(result.dimensions) == 5


def test_scoring_is_deterministic(engine):
    meta = get_stock("2330")
    first = engine.score(meta, AS_OF)
    second = engine.score(meta, AS_OF)
    assert first.total_score == second.total_score


def test_recommendation_label_assigned(engine):
    meta = get_stock("2454")
    result = engine.score(meta, AS_OF)
    assert result.recommendation in {
        "強力推薦",
        "推薦",
        "區間偏多",
        "觀望",
        "偏空",
    }


def test_sector_aggregation_ranks_themes(engine):
    scores = [engine.score(m, AS_OF) for m in UNIVERSE]
    scores = [s for s in scores if s]
    sectors = aggregate_sectors(scores)
    assert sectors
    # Ranks are contiguous starting at 1 and sorted by strength desc.
    assert [s.rank for s in sectors] == list(range(1, len(sectors) + 1))
    assert sectors[0].strength_score >= sectors[-1].strength_score


def test_market_temperature_in_range(engine):
    scores = [s for m in UNIVERSE if (s := engine.score(m, AS_OF))]
    market = compute_market_score(engine.collectors, scores, AS_OF)
    assert 0 <= market.temperature_score <= 100
    assert market.sentiment in {"極度看多", "偏多", "中性", "偏空", "極度看空"}
    assert len(market.indices) == 2
