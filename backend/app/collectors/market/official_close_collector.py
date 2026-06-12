"""Official TWSE/TPEx end-of-day OHLCV collector."""
from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from urllib.parse import urlencode

import httpx

from app.collectors.base import PriceCollector
from app.domain.simulator import Candle
from app.domain.universe import UNIVERSE, get_stock

JsonFetcher = Callable[[str], dict]


def _number(value: str) -> float:
    cleaned = value.replace(",", "").replace("+", "").strip()
    if cleaned in {"", "--", "---", "除權", "除息"}:
        return 0.0
    return float(cleaned)


def _roc_date(value: str) -> date:
    year, month, day = (int(part) for part in value.strip().split("/"))
    return date(year + 1911, month, day)


def _previous_month(day: date) -> date:
    if day.month == 1:
        return date(day.year - 1, 12, 1)
    return date(day.year, day.month - 1, 1)


class OfficialClosePriceCollector(PriceCollector):
    """Fetches monthly close data from exchange-operated HTTP endpoints."""

    def __init__(self, fetch_json: JsonFetcher | None = None):
        self._fetch_json = fetch_json or self._http_get_json
        self._cache: dict[str, dict] = {}

    @staticmethod
    def _http_get_json(url: str) -> dict:
        last_error: Exception | None = None
        headers = {"User-Agent": "TaiwanAlphaRadar/0.1 research-project"}
        for attempt in range(3):
            try:
                response = httpx.get(url, headers=headers, timeout=20.0)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"Official market-data request failed: {url}") from last_error

    def _get(self, url: str) -> dict:
        if url not in self._cache:
            self._cache[url] = self._fetch_json(url)
        return self._cache[url]

    def fetch_history(self, stock_id: str, end: date, days: int) -> list[Candle]:
        meta = get_stock(stock_id)
        if meta is None:
            return []

        rows: dict[date, tuple[float, float, float, float, int]] = {}
        cursor = end.replace(day=1)
        for _ in range(24):
            if meta.market == "TPEx":
                payload = self._get(self._tpex_url(stock_id, cursor))
                monthly = self._parse_tpex(payload)
            else:
                payload = self._get(self._twse_url(stock_id, cursor))
                monthly = self._parse_twse(payload)
            for trade_date, values in monthly.items():
                if trade_date <= end:
                    rows[trade_date] = values
            if len(rows) >= days:
                break
            cursor = _previous_month(cursor)

        return self._to_candles(rows)[-days:]

    def fetch_index(self, index_id: str, end: date, days: int) -> list[Candle]:
        if index_id == "TAIEX":
            rows: dict[date, tuple[float, float, float, float, int]] = {}
            cursor = end.replace(day=1)
            for _ in range(12):
                payload = self._get(self._taiex_url(cursor))
                for row in payload.get("data", []):
                    trade_date = _roc_date(row[0])
                    if trade_date > end:
                        continue
                    close = _number(row[4])
                    volume = int(_number(row[2]))
                    rows[trade_date] = (close, close, close, close, volume)
                if len(rows) >= days:
                    break
                cursor = _previous_month(cursor)
            return self._to_candles(rows)[-days:]

        # TPEx does not expose the same convenient monthly index endpoint.
        # Build a transparent equal-weight proxy from official TPEx closes.
        members = [stock for stock in UNIVERSE if stock.market == "TPEx"]
        histories = [self.fetch_history(stock.stock_id, end, days) for stock in members]
        by_date: dict[date, list[float]] = {}
        for history in histories:
            for previous, current in zip(history, history[1:]):
                if previous.close:
                    by_date.setdefault(current.trade_date, []).append(
                        current.close / previous.close - 1
                    )
        level = 245.0
        proxy: list[Candle] = []
        for trade_date in sorted(by_date):
            returns = by_date[trade_date]
            if not returns:
                continue
            previous = level
            level *= 1 + sum(returns) / len(returns)
            proxy.append(
                Candle(
                    trade_date=trade_date,
                    open=round(previous, 2),
                    high=round(max(previous, level), 2),
                    low=round(min(previous, level), 2),
                    close=round(level, 2),
                    volume=0,
                    change_pct=round((level / previous - 1) * 100, 2),
                )
            )
        return proxy[-days:]

    @staticmethod
    def _twse_url(stock_id: str, month: date) -> str:
        query = urlencode(
            {"response": "json", "date": month.strftime("%Y%m01"), "stockNo": stock_id}
        )
        return f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?{query}"

    @staticmethod
    def _tpex_url(stock_id: str, month: date) -> str:
        query = urlencode(
            {
                "code": stock_id,
                "date": month.strftime("%Y/%m/01"),
                "id": "",
                "response": "json",
            }
        )
        return f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?{query}"

    @staticmethod
    def _taiex_url(month: date) -> str:
        query = urlencode({"response": "json", "date": month.strftime("%Y%m01")})
        return f"https://www.twse.com.tw/exchangeReport/FMTQIK?{query}"

    @staticmethod
    def _parse_twse(payload: dict) -> dict[date, tuple[float, float, float, float, int]]:
        parsed = {}
        for row in payload.get("data", []):
            close = _number(row[6])
            if close <= 0:
                continue
            open_ = _number(row[3]) or close
            high = _number(row[4]) or close
            low = _number(row[5]) or close
            parsed[_roc_date(row[0])] = (
                open_,
                high,
                low,
                close,
                int(_number(row[1])),
            )
        return parsed

    @staticmethod
    def _parse_tpex(payload: dict) -> dict[date, tuple[float, float, float, float, int]]:
        tables = payload.get("tables", [])
        rows = tables[0].get("data", []) if tables else []
        parsed = {}
        for row in rows:
            close = _number(row[6])
            if close <= 0:
                continue
            open_ = _number(row[3]) or close
            high = _number(row[4]) or close
            low = _number(row[5]) or close
            parsed[_roc_date(row[0])] = (
                open_,
                high,
                low,
                close,
                int(_number(row[1]) * 1000),
            )
        return parsed

    @staticmethod
    def _to_candles(
        rows: dict[date, tuple[float, float, float, float, int]]
    ) -> list[Candle]:
        candles: list[Candle] = []
        previous_close: float | None = None
        for trade_date in sorted(rows):
            open_, high, low, close, volume = rows[trade_date]
            change_pct = (
                round((close / previous_close - 1) * 100, 2)
                if previous_close
                else 0.0
            )
            candles.append(
                Candle(trade_date, open_, high, low, close, volume, change_pct)
            )
            previous_close = close
        return candles
