"""Official TWSE/TPEx end-of-day institutional flow collector."""
from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from typing import Any
from urllib.parse import urlencode

import httpx

from app.collectors.base import InstitutionalCollector
from app.domain.simulator import InstitutionalFlow
from app.domain.universe import get_stock

JsonFetcher = Callable[[str], dict[str, Any]]


def _number(value: Any) -> int:
    cleaned = str(value or "").replace(",", "").replace("+", "").strip()
    if cleaned in {"", "-", "--", "---"}:
        return 0
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


class OfficialInstitutionalCollector(InstitutionalCollector):
    """Fetches daily three-major-institution net flow from official endpoints."""

    source = "twse_tpex_official_institutional"

    def __init__(self, fetch_json: JsonFetcher | None = None):
        self._fetch_json = fetch_json or self._http_get_json
        self._cache: dict[str, dict[str, InstitutionalFlow]] = {}

    @staticmethod
    def _http_get_json(url: str) -> dict[str, Any]:
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
        raise RuntimeError(f"Official institutional request failed: {url}") from last_error

    def fetch_flow(self, stock_id: str, day: date) -> InstitutionalFlow:
        meta = get_stock(stock_id)
        if meta is None:
            return InstitutionalFlow(0, 0, 0, 0.0, 0.0)
        key = f"{meta.market}:{day.isoformat()}"
        if key not in self._cache:
            payload = self._fetch_json(
                self._tpex_url(day) if meta.market == "TPEx" else self._twse_url(day)
            )
            self._cache[key] = (
                self._parse_tpex(payload)
                if meta.market == "TPEx"
                else self._parse_twse(payload)
            )
        return self._cache[key].get(stock_id, InstitutionalFlow(0, 0, 0, 0.0, 0.0))

    @staticmethod
    def _twse_url(day: date) -> str:
        query = urlencode(
            {
                "date": day.strftime("%Y%m%d"),
                "selectType": "ALLBUT0999",
                "response": "json",
            }
        )
        return f"https://www.twse.com.tw/rwd/zh/fund/T86?{query}"

    @staticmethod
    def _tpex_url(day: date) -> str:
        query = urlencode(
            {
                "date": day.strftime("%Y/%m/%d"),
                "type": "Daily",
                "response": "json",
            }
        )
        return f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?{query}"

    @staticmethod
    def _parse_twse(payload: dict[str, Any]) -> dict[str, InstitutionalFlow]:
        if payload.get("stat") not in {"OK", "很抱歉，沒有符合條件的資料!"}:
            return {}
        parsed = {}
        for row in payload.get("data", []):
            if len(row) <= 18:
                continue
            stock_id = str(row[0]).strip()
            foreign_net = _number(row[4]) // 1000
            trust_net = _number(row[10]) // 1000
            dealer_net = _number(row[11]) // 1000
            total_net = _number(row[18]) // 1000
            parsed[stock_id] = InstitutionalFlow(
                foreign_net=foreign_net,
                trust_net=trust_net,
                dealer_net=dealer_net,
                foreign_hold_pct=0.0,
                margin_balance_change_pct=0.0,
            )
            if total_net and foreign_net + trust_net + dealer_net != total_net:
                parsed[stock_id] = InstitutionalFlow(
                    foreign_net=foreign_net,
                    trust_net=trust_net,
                    dealer_net=total_net - foreign_net - trust_net,
                    foreign_hold_pct=0.0,
                    margin_balance_change_pct=0.0,
                )
        return parsed

    @staticmethod
    def _parse_tpex(payload: dict[str, Any]) -> dict[str, InstitutionalFlow]:
        tables = payload.get("tables") or []
        if not tables:
            return {}
        parsed = {}
        for row in tables[0].get("data", []):
            if len(row) <= 23:
                continue
            stock_id = str(row[0]).strip()
            foreign_net = _number(row[10]) // 1000
            trust_net = _number(row[13]) // 1000
            dealer_net = _number(row[22]) // 1000
            total_net = _number(row[23]) // 1000
            if total_net and foreign_net + trust_net + dealer_net != total_net:
                dealer_net = total_net - foreign_net - trust_net
            parsed[stock_id] = InstitutionalFlow(
                foreign_net=foreign_net,
                trust_net=trust_net,
                dealer_net=dealer_net,
                foreign_hold_pct=0.0,
                margin_balance_change_pct=0.0,
            )
        return parsed
