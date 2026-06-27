"""Contract tests for official institutional-flow normalization."""
from datetime import date

from app.collectors.institutional.official_institutional_collector import (
    OfficialInstitutionalCollector,
)


def test_twse_institutional_flow_normalizes_to_thousand_shares():
    def fake_fetch(url: str) -> dict:
        return {
            "stat": "OK",
            "data": [
                [
                    "2330",
                    "台積電",
                    "10,000",
                    "3,000",
                    "7,000",
                    "0",
                    "0",
                    "0",
                    "5,000",
                    "1,000",
                    "4,000",
                    "-2,000",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "9,000",
                ]
            ],
        }

    flow = OfficialInstitutionalCollector(fake_fetch).fetch_flow(
        "2330", date(2026, 6, 26)
    )

    assert flow.foreign_net == 7
    assert flow.trust_net == 4
    assert flow.dealer_net == -2


def test_tpex_institutional_flow_uses_total_foreign_and_dealer_columns():
    def fake_fetch(url: str) -> dict:
        return {
            "tables": [
                {
                    "data": [
                        [
                            "4979",
                            "華星光",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "20,000",
                            "4,000",
                            "16,000",
                            "5,000",
                            "1,000",
                            "4,000",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "8,000",
                            "3,000",
                            "5,000",
                            "25,000",
                        ]
                    ]
                }
            ]
        }

    flow = OfficialInstitutionalCollector(fake_fetch).fetch_flow(
        "4979", date(2026, 6, 26)
    )

    assert flow.foreign_net == 16
    assert flow.trust_net == 4
    assert flow.dealer_net == 5
