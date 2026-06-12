"""Contract tests for TWSE/TPEx official close-price normalization."""
from datetime import date

from app.collectors.market.official_close_collector import OfficialClosePriceCollector


def test_twse_monthly_rows_are_normalized_to_candles():
    payload = {
        "stat": "OK",
        "data": [
            ["115/05/04", "44,458,732", "99,944,198,300", "2,200.00",
             "2,285.00", "2,195.00", "2,275.00", "+140.00", "129,173", ""],
            ["115/05/05", "26,644,983", "60,009,590,420", "2,250.00",
             "2,270.00", "2,240.00", "2,250.00", "-25.00", "153,870", ""],
        ],
    }
    collector = OfficialClosePriceCollector(fetch_json=lambda _: payload)

    candles = collector.fetch_history("2330", date(2026, 5, 31), 2)

    assert [c.trade_date for c in candles] == [date(2026, 5, 4), date(2026, 5, 5)]
    assert candles[0].volume == 44_458_732
    assert candles[1].close == 2250.0
    assert candles[1].change_pct == -1.1


def test_tpex_monthly_volume_is_converted_from_thousand_shares():
    payload = {
        "tables": [{
            "data": [
                ["115/05/04", "1,811", "1,198,723", "664.00", "669.00",
                 "646.00", "669.00", "60.00", "3,551"],
                ["115/05/05", "1,656", "1,157,523", "676.00", "718.00",
                 "676.00", "718.00", "49.00", "4,124"],
            ],
        }],
    }
    collector = OfficialClosePriceCollector(fetch_json=lambda _: payload)

    candles = collector.fetch_history("4979", date(2026, 5, 31), 2)

    assert candles[0].volume == 1_811_000
    assert candles[1].change_pct == 7.32
    assert candles[1].high == 718.0


def test_history_excludes_rows_after_requested_end_date():
    payload = {
        "stat": "OK",
        "data": [
            ["115/05/04", "1,000", "1,000", "100", "101", "99", "100", "0", "1", ""],
            ["115/05/05", "1,000", "1,000", "100", "102", "99", "101", "1", "1", ""],
        ],
    }
    collector = OfficialClosePriceCollector(fetch_json=lambda _: payload)

    candles = collector.fetch_history("2330", date(2026, 5, 4), 20)

    assert len(candles) == 1
    assert candles[0].trade_date == date(2026, 5, 4)


def test_rows_without_a_valid_close_are_skipped():
    payload = {
        "stat": "OK",
        "data": [
            ["115/05/04", "0", "0", "--", "--", "--", "--", "0", "0", ""],
            ["115/05/05", "1,000", "100,000", "100", "101", "99", "100", "0", "1", ""],
        ],
    }
    collector = OfficialClosePriceCollector(fetch_json=lambda _: payload)

    candles = collector.fetch_history("2330", date(2026, 5, 31), 2)

    assert len(candles) == 1
    assert candles[0].trade_date == date(2026, 5, 5)
