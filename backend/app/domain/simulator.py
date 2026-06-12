"""Deterministic market data simulator.

Generates reproducible OHLCV history, institutional flows, fundamentals and
news catalysts from a stock id + date. Reproducibility matters: restarting the
container must not reshuffle the dataset, so every series is seeded from a hash
of (stock_id), not from wall-clock randomness.

This lives in the domain layer because both the collectors (mock data source)
and tests depend on it. Replacing the mock collectors with a real feed does not
touch this module.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.universe import StockMeta


def _seed(*parts: str) -> int:
    raw = "::".join(parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _rng(*parts: str) -> random.Random:
    return random.Random(_seed(*parts))


@dataclass(frozen=True)
class Candle:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: float


def trading_days(end: date, count: int) -> list[date]:
    """Return ``count`` weekday dates ending on/just before ``end`` (no holidays)."""
    days: list[date] = []
    cursor = end
    while len(days) < count:
        if cursor.weekday() < 5:  # Mon-Fri
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


def simulate_prices(meta: StockMeta, end: date, days: int) -> list[Candle]:
    """Build a deterministic OHLCV random walk for one stock.

    Each stock gets its own drift and volatility derived from its seed so the
    universe shows a realistic spread of trends rather than identical noise.
    """
    rng = _rng("price", meta.stock_id)
    # Per-stock character.
    drift = (rng.random() - 0.45) * 0.0025          # slight long bias spread
    volatility = 0.012 + rng.random() * 0.028        # 1.2% - 4.0% daily sigma
    price = meta.base_price * (0.85 + rng.random() * 0.1)

    candles: list[Candle] = []
    for d in trading_days(end, days):
        # Daily return: drift + gaussian shock, clamped to TWSE +-10% limit.
        shock = rng.gauss(0, volatility)
        ret = max(-0.099, min(0.099, drift + shock))
        prev_close = price
        close = round(prev_close * (1 + ret), 2)
        open_ = round(prev_close * (1 + rng.gauss(0, volatility * 0.4)), 2)
        high = round(max(open_, close) * (1 + abs(rng.gauss(0, volatility * 0.3))), 2)
        low = round(min(open_, close) * (1 - abs(rng.gauss(0, volatility * 0.3))), 2)
        base_vol = meta.market_cap_billion * 1_000  # rough liquidity proxy
        volume = int(base_vol * (0.5 + rng.random() * 1.5))
        change_pct = round((close / prev_close - 1) * 100, 2)
        candles.append(
            Candle(d, open_, high, low, close, volume, change_pct)
        )
        price = close
    return candles


@dataclass(frozen=True)
class InstitutionalFlow:
    """Three-major-institutions net buy/sell, in thousands of shares."""

    foreign_net: int
    trust_net: int
    dealer_net: int
    foreign_hold_pct: float
    margin_balance_change_pct: float


def simulate_institutional(meta: StockMeta, day: date) -> InstitutionalFlow:
    rng = _rng("inst", meta.stock_id, day.isoformat())
    scale = max(1.0, math.log10(meta.market_cap_billion + 10)) * 1500
    return InstitutionalFlow(
        foreign_net=int(rng.gauss(0, 1) * scale),
        trust_net=int(rng.gauss(0, 0.4) * scale),
        dealer_net=int(rng.gauss(0, 0.2) * scale),
        foreign_hold_pct=round(15 + rng.random() * 60, 1),
        margin_balance_change_pct=round(rng.gauss(0, 3), 2),
    )


@dataclass(frozen=True)
class Fundamentals:
    eps_ttm: float
    pe_ratio: float
    pb_ratio: float
    roe_pct: float
    yield_pct: float
    revenue_yoy_pct: float
    gross_margin_pct: float


def simulate_fundamentals(meta: StockMeta, ref_price: float) -> Fundamentals:
    rng = _rng("fund", meta.stock_id)
    # Growth themes get richer multiples / margins.
    growth = meta.theme in {"AI", "光通訊", "散熱", "機器人", "半導體"}
    eps = round(max(0.5, ref_price / (rng.uniform(12, 35) if growth else rng.uniform(8, 18))), 2)
    pe = round(ref_price / eps, 1)
    return Fundamentals(
        eps_ttm=eps,
        pe_ratio=pe,
        pb_ratio=round(rng.uniform(1.0, 6.0) if growth else rng.uniform(0.6, 2.5), 2),
        roe_pct=round(rng.uniform(12, 35) if growth else rng.uniform(5, 18), 1),
        yield_pct=round(rng.uniform(0.0, 2.5) if growth else rng.uniform(2.0, 6.5), 2),
        revenue_yoy_pct=round(rng.gauss(25 if growth else 3, 18), 1),
        gross_margin_pct=round(rng.uniform(25, 60) if growth else rng.uniform(8, 25), 1),
    )


_HEADLINE_BANK = {
    "AI": ["AI 伺服器訂單能見度看到明年", "雲端客戶加大 AI 資本支出", "輝達供應鏈拉貨動能強勁"],
    "光通訊": ["矽光子題材發酵", "800G 光模組需求放量", "CPO 進度優於預期"],
    "散熱": ["液冷散熱滲透率提升", "AI 機櫃散熱規格升級", "水冷板出貨遞增"],
    "機器人": ["人形機器人供應鏈卡位", "減速機需求回溫", "工業自動化訂單回升"],
    "半導體": ["先進製程產能滿載", "成熟製程庫存去化完成", "封測稼動率回升"],
    "電動車": ["車用電子認證通過", "充電樁布建加速", "重電訂單看到 2027"],
    "金融": ["升息環境利差擴大", "壽險投資收益回穩", "金控獲利改寫新高"],
    "傳產": ["航運運價反彈", "原物料報價走揚", "庫存回補需求顯現"],
}


@dataclass(frozen=True)
class NewsItem:
    title: str
    sentiment: float  # -1 .. 1
    source: str


def simulate_news(meta: StockMeta, day: date, n: int = 3) -> list[NewsItem]:
    rng = _rng("news", meta.stock_id, day.isoformat())
    bank = _HEADLINE_BANK.get(meta.theme, ["營運展望穩健", "法人調整評等", "近期股價波動加大"])
    items: list[NewsItem] = []
    for i in range(n):
        title = rng.choice(bank)
        items.append(
            NewsItem(
                title=f"{meta.name}（{meta.stock_id}）{title}",
                sentiment=round(rng.uniform(-0.3, 0.9), 2),
                source=rng.choice(["經濟日報", "工商時報", "鉅亨網", "MoneyDJ"]),
            )
        )
    return items
