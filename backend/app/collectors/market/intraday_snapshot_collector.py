"""Best-effort intraday quote snapshots for pre-close preview signals."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx

from app.domain.simulator import Candle
from app.domain.universe import StockMeta

JsonFetcher = Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class IntradaySnapshot:
    stock_id: str
    candle: Candle
    timestamp: datetime
    source: str


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    cleaned = str(value).replace(",", "").replace("+", "").strip()
    if cleaned in {"", "-", "--", "---"}:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class TwseMisIntradaySnapshotCollector:
    """Fetches delayed/current intraday quote snapshots from TWSE MIS endpoints."""

    source = "twse_mis_intraday_preview"

    def __init__(self, fetch_json: JsonFetcher | None = None):
        self._fetch_json = fetch_json or self._http_get_json

    @staticmethod
    def _http_get_json(url: str) -> dict[str, Any]:
        headers = {
            "User-Agent": "TaiwanAlphaRadar/0.1 research-project",
            "Referer": "https://mis.twse.com.tw/stock/index.jsp",
        }
        with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True) as client:
            # The quote endpoint is more reliable after opening the MIS landing page.
            client.get("https://mis.twse.com.tw/stock/index.jsp")
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def fetch_snapshot(self, meta: StockMeta, at: datetime) -> IntradaySnapshot | None:
        exchange = "otc" if meta.market == "TPEx" else "tse"
        channel = f"{exchange}_{meta.stock_id}.tw"
        url = (
            "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
            f"?ex_ch={channel}&json=1&delay=0&_={int(time.time() * 1000)}"
        )
        payload = self._fetch_json(url)
        rows = payload.get("msgArray") or []
        if not rows:
            return None
        row = rows[0]
        current = _number(row.get("z")) or _number(row.get("y"))
        previous_close = _number(row.get("y"))
        if current <= 0 or previous_close <= 0:
            return None

        open_ = _number(row.get("o")) or previous_close
        high = _number(row.get("h")) or max(open_, current)
        low = _number(row.get("l")) or min(open_, current)
        volume_lots = _number(row.get("v")) or _number(row.get("tv"))
        volume = int(volume_lots * 1000)
        trade_date = at.date()
        raw_date = str(row.get("d") or "")
        raw_time = str(row.get("t") or "")
        timestamp = at
        if len(raw_date) == 8 and raw_time:
            try:
                trade_date = date(
                    int(raw_date[0:4]),
                    int(raw_date[4:6]),
                    int(raw_date[6:8]),
                )
                timestamp = datetime.strptime(
                    f"{raw_date} {raw_time}", "%Y%m%d %H:%M:%S"
                )
            except ValueError:
                timestamp = at
        change_pct = (current / previous_close - 1) * 100
        return IntradaySnapshot(
            stock_id=meta.stock_id,
            candle=Candle(
                trade_date=trade_date,
                open=round(open_, 2),
                high=round(max(high, open_, current), 2),
                low=round(min(low, open_, current), 2),
                close=round(current, 2),
                volume=volume,
                change_pct=round(change_pct, 2),
            ),
            timestamp=timestamp,
            source=self.source,
        )
