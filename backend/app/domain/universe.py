"""Taiwan stock universe — the single source of truth for the mock dataset.

This module defines a realistic slice of TWSE/TPEx listed companies grouped by
theme/sector. Everything downstream (collectors, alpha engine, seeding) derives
from this list, so swapping in a real data feed later only means replacing the
collector layer — the universe contract stays the same.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockMeta:
    """Static metadata for a single listed company."""

    stock_id: str          # e.g. "2330"
    name: str              # e.g. "台積電"
    name_en: str
    sector: str            # high-level industry
    theme: str             # hot-money theme bucket used by sector analysis
    market: str            # "TWSE" | "TPEx"
    base_price: float      # anchor price for the deterministic price simulator
    market_cap_billion: float


# Theme buckets shown on the dashboard "今日熱門族群".
THEMES: list[str] = [
    "AI",
    "機器人",
    "光通訊",
    "散熱",
    "半導體",
    "金融",
    "傳產",
    "電動車",
]

# A curated ~40-stock universe. Prices are anchors only; the simulator builds
# deterministic OHLCV history from them.
UNIVERSE: list[StockMeta] = [
    # --- 半導體 / AI 龍頭 ---
    StockMeta("2330", "台積電", "TSMC", "半導體", "半導體", "TWSE", 1010.0, 26200.0),
    StockMeta("2454", "聯發科", "MediaTek", "半導體", "AI", "TWSE", 1300.0, 2080.0),
    StockMeta("2303", "聯電", "UMC", "半導體", "半導體", "TWSE", 52.0, 650.0),
    StockMeta("3711", "日月光投控", "ASE", "半導體", "半導體", "TWSE", 165.0, 720.0),
    StockMeta("2308", "台達電", "Delta", "電子零組件", "電動車", "TWSE", 420.0, 1090.0),
    # --- AI 伺服器 / 機器人 ---
    StockMeta("2317", "鴻海", "Foxconn", "電子組裝", "AI", "TWSE", 205.0, 2840.0),
    StockMeta("2382", "廣達", "Quanta", "電子組裝", "AI", "TWSE", 290.0, 1120.0),
    StockMeta("3231", "緯創", "Wistron", "電子組裝", "AI", "TWSE", 118.0, 340.0),
    StockMeta("2376", "技嘉", "Gigabyte", "電腦及週邊", "AI", "TWSE", 310.0, 200.0),
    StockMeta("4938", "和碩", "Pegatron", "電子組裝", "機器人", "TWSE", 88.0, 235.0),
    StockMeta("2049", "上銀", "Hiwin", "機械", "機器人", "TWSE", 215.0, 220.0),
    StockMeta("1590", "亞德客-KY", "Airtac", "機械", "機器人", "TWSE", 820.0, 165.0),
    # --- 光通訊 ---
    StockMeta("3019", "亞光", "AOE", "光電", "光通訊", "TWSE", 95.0, 60.0),
    StockMeta("4979", "華星光", "Luxnet", "光電", "光通訊", "TPEx", 180.0, 35.0),
    StockMeta("3450", "聯鈞", "Browave", "光電", "光通訊", "TPEx", 210.0, 40.0),
    StockMeta("4977", "眾達-KY", "Eoptolink", "光電", "光通訊", "TPEx", 290.0, 45.0),
    # --- 散熱 ---
    StockMeta("3017", "奇鋐", "AVC", "電子零組件", "散熱", "TWSE", 720.0, 220.0),
    StockMeta("3324", "雙鴻", "Auras", "電子零組件", "散熱", "TWSE", 560.0, 90.0),
    StockMeta("2421", "建準", "Sunon", "電子零組件", "散熱", "TWSE", 78.0, 60.0),
    # --- 金融 ---
    StockMeta("2881", "富邦金", "Fubon", "金融", "金融", "TWSE", 92.0, 1230.0),
    StockMeta("2882", "國泰金", "Cathay", "金融", "金融", "TWSE", 65.0, 970.0),
    StockMeta("2891", "中信金", "CTBC", "金融", "金融", "TWSE", 40.0, 800.0),
    StockMeta("2886", "兆豐金", "Mega", "金融", "金融", "TWSE", 42.0, 580.0),
    StockMeta("2884", "玉山金", "E.Sun", "金融", "金融", "TWSE", 28.0, 450.0),
    # --- 傳產 / 航運 ---
    StockMeta("2603", "長榮", "Evergreen", "航運", "傳產", "TWSE", 210.0, 440.0),
    StockMeta("2609", "陽明", "Yang Ming", "航運", "傳產", "TWSE", 75.0, 260.0),
    StockMeta("1301", "台塑", "FPC", "塑膠", "傳產", "TWSE", 48.0, 300.0),
    StockMeta("1303", "南亞", "Nan Ya", "塑膠", "傳產", "TWSE", 45.0, 350.0),
    StockMeta("2002", "中鋼", "CSC", "鋼鐵", "傳產", "TWSE", 23.0, 360.0),
    StockMeta("1101", "台泥", "TCC", "水泥", "傳產", "TWSE", 33.0, 230.0),
    # --- 電動車 / 綠能 ---
    StockMeta("6531", "愛普", "Aprosys", "半導體", "電動車", "TPEx", 480.0, 30.0),
    StockMeta("1519", "華城", "Hwa Chuang", "電機機械", "電動車", "TWSE", 420.0, 150.0),
    StockMeta("1513", "中興電", "CHEM", "電機機械", "電動車", "TWSE", 220.0, 110.0),
    # --- 其他電子 / 網通 ---
    StockMeta("2412", "中華電", "CHT", "電信", "傳產", "TWSE", 125.0, 970.0),
    StockMeta("2357", "華碩", "ASUS", "電腦及週邊", "AI", "TWSE", 560.0, 420.0),
    StockMeta("2345", "智邦", "Accton", "通信網路", "AI", "TWSE", 640.0, 360.0),
    StockMeta("3661", "世芯-KY", "Alchip", "半導體", "AI", "TWSE", 2800.0, 215.0),
    StockMeta("3035", "智原", "Faraday", "半導體", "AI", "TWSE", 380.0, 95.0),
    StockMeta("6415", "矽力-KY", "Silergy", "半導體", "半導體", "TWSE", 410.0, 90.0),
    StockMeta("2379", "瑞昱", "Realtek", "半導體", "半導體", "TWSE", 560.0, 290.0),
]

# Indices tracked by market analysis.
INDICES: list[dict] = [
    {"index_id": "TAIEX", "name": "加權指數", "base_value": 22800.0},
    {"index_id": "TPEX", "name": "櫃買指數", "base_value": 245.0},
]

_BY_ID: dict[str, StockMeta] = {s.stock_id: s for s in UNIVERSE}


def get_stock(stock_id: str) -> StockMeta | None:
    return _BY_ID.get(stock_id)


def all_themes() -> list[str]:
    """Themes that actually have at least one stock in the universe."""
    present = {s.theme for s in UNIVERSE}
    return [t for t in THEMES if t in present]
