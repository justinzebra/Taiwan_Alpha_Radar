# Taiwan Alpha Radar 🛰️

> 台股 AI 選股分析平台 — **每日選股決策平台**

每天自動分析台灣股市，產出 **大盤溫度、類股強弱、個股 Alpha Score 與 AI 投資報告**，
幫你回答一個問題：**今天，該關注哪些股票？**

這不是看盤系統，也不是下單系統，而是一個聚焦「選股決策」的分析平台。

---

## ✨ 功能 (MVP)

- **市場儀表板** — 0~100 市場溫度儀表（極度看空 → 極度看多）、上漲/下跌家數、市場風險、Top 10 排行、熱門族群、評分分布圖
- **大盤分析** — 加權指數 / 櫃買指數的趨勢、強度、成交量、市場研判
- **熱門族群** — AI、機器人、光通訊、散熱、半導體… 族群強度排行與領漲股
- **選股排行** — 支援搜尋、排序（總分/技術/籌碼/基本）、分頁
- **個股分析** — 總分 + 五力評分（技術/籌碼/基本/題材/風險）、評分理由、股價走勢、雷達圖、**AI 投資摘要**（亮點/風險/短中期觀察）

---

## 🏗️ 技術棧

| 層 | 技術 |
|----|------|
| Frontend | Next.js 13 · TypeScript · TailwindCSS · shadcn 風格元件 · Recharts |
| Backend | Python · FastAPI · SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Scheduler | APScheduler |
| AI | OpenAI / Anthropic（Provider Pattern，預設 mock 可離線運作） |
| Deploy | Docker · Docker Compose |

---

## 🚀 快速啟動

### 🖱️ Windows 一鍵啟動（雙擊 .bat）

專案根目錄已附啟動／停止腳本，直接雙擊即可：

| 檔案 | 用途 | 需求 |
|------|------|------|
| `start.bat` | 啟動前後端（Docker，Windows） | 已安裝 Docker Desktop |
| `stop.bat` | 停止前後端（Docker，Windows） | — |
| `logs.bat` | 查看後端即時日誌（Docker，Windows） | — |
| `start-local.bat` | 啟動前後端（免 Docker，Windows） | Python 3.11+ 與 Node 18+ |
| `stop-local.bat` | 停止前後端（免 Docker，Windows） | — |
| `mac/start.sh` | 啟動前後端（Docker，macOS） | 已安裝 Docker Desktop |
| `mac/stop.sh` | 停止前後端（Docker，macOS） | — |
| `mac/start-local.sh` | 啟動前後端（免 Docker，macOS） | Python 3.11+ 與 Node 18+ |
| `mac/stop-local.sh` | 停止前後端（免 Docker，macOS） | — |
| `mac/start-local.command` | Finder 雙擊啟動（免 Docker，macOS） | Python 3.11+ 與 Node 18+ |
| `mac/stop-local.command` | Finder 雙擊停止（免 Docker，macOS） | — |

- **Windows + Docker** → 雙擊 `start.bat`（最乾淨，含 Postgres/Redis）。停止用 `stop.bat`。
- **Windows 本機開發** → 雙擊 `start-local.bat`：後端使用 **SQLite + TWSE/TPEx 官方盤後價格**，前端用 `npm run dev`。停止用 `stop-local.bat`。
- **macOS + Docker** → 於 Terminal 執行 `./mac/start.sh`。停止用 `./mac/stop.sh`。
- **macOS 本機開發** → 於 Terminal 執行 `./mac/start-local.sh`：後端使用 **SQLite + TWSE/TPEx 官方盤後價格**，前端用 `npm run dev`。停止用 `./mac/stop-local.sh`。
  - 要從 Finder 啟動，請雙擊 `mac/start-local.command`；停止時雙擊 `mac/stop-local.command`。
  - 前端需要 **Node 18 以上**；腳本會自動檢查並提示。

> 兩種方式都會在後端就緒後自動開啟瀏覽器到 http://localhost:3000。

### 方式一：Docker Compose（推薦，一鍵啟動）

```bash
docker compose up --build
```

啟動後：

- 前端 → http://localhost:3000
- 後端 API 文件 (Swagger) → http://localhost:8000/docs

後端首次啟動會自動下載約 180 個交易日的 **TWSE／TPEx 官方盤後 OHLCV**，
建立每日技術預測與 1／3／5／10 日 walk-forward 回測。首次下載可能需要數分鐘，無需 API key。
第一次 `up` 後請等待 backend 日誌出現 `Pipeline complete` 再開啟前端。

> 目前只有價格資料為官方真實資料；籌碼、財報、新聞與 AI 報告仍使用 mock。
> 「預測驗證」頁的 `technical_eod_v1` 僅使用真實收盤 OHLCV，與混合資料的完整 Alpha Score 分開呈現。

> 想用真實 LLM 產生報告？複製 `.env.example` 為 `.env`，設定
> `AI_PROVIDER=openai` 與 `OPENAI_API_KEY=...`（或 `anthropic`）即可。

### 方式二：本機開發

**後端**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 需要本機的 PostgreSQL 與 Redis，或調整 .env 的連線字串
cp .env.example .env
uvicorn app.main:app --reload
```

**前端**

```bash
cd frontend
npm install --legacy-peer-deps
cp .env.example .env.local
npm run dev
```

---

## 📁 專案結構

```
taiwan-alpha-radar/
├── backend/
│   └── app/
│       ├── domain/        # universe(台股清單) + simulator(確定性模擬)
│       ├── collectors/    # TWSE/TPEx 官方收盤價 + 其他維度 Mock Provider
│       ├── alpha/         # 評分引擎 (Strategy Pattern)
│       │   └── dimensions/  # technical/institutional/fundamental/thematic/risk
│       ├── ai/            # AI 報告引擎 (Provider Pattern)
│       ├── models/        # SQLAlchemy ORM (6 張表)
│       ├── schemas/       # Pydantic 回應模型
│       ├── services/      # pipeline 編排 · queries 讀取 · cache
│       ├── api/routes/    # FastAPI 路由
│       ├── scheduler/     # APScheduler 每日排程
│       ├── seed.py        # 建表 + 首次灌資料
│       └── main.py        # 應用進入點
├── frontend/
│   └── src/
│       ├── app/           # App Router 頁面 (dashboard/market/sectors/stocks/[id])
│       ├── components/    # ui / charts / dashboard / stock / layout
│       └── lib/           # api client · types · hooks · utils
├── docs/
│   ├── ARCHITECTURE.md    # 架構與設計決策
│   └── schema.sql         # PostgreSQL schema 參考
├── docker-compose.yml
└── README.md
```

---

## 🔌 API

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/dashboard` | 儀表板彙整（市場/Top10/族群/分布） |
| GET | `/api/market` | 大盤分析 |
| GET | `/api/sectors` | 族群強度排行 |
| GET | `/api/stocks` | 個股排行（`page`,`page_size`,`search`,`sort`,`theme`） |
| GET | `/api/stocks/{stock_id}` | 個股完整分析 + AI 報告 |
| GET | `/api/predictions` | 最新收盤後技術預測排行 |
| GET | `/api/backtest` | 1／3／5／10 日 walk-forward 回測 |
| POST | `/api/admin/run-pipeline` | 手動重跑當日分析（展示用） |
| GET | `/health` | 健康檢查 |

---

## 🧮 Alpha Score 評分系統

總分 100 分，由五個**可獨立擴充**的維度（Strategy Pattern）加權組成：

```
技術面 30% + 籌碼面 25% + 基本面 20% + 題材面 15% + 風險面 10%
```

新增維度只需在 `backend/app/alpha/dimensions/` 新增一個 `DimensionScorer`
並加入 `ALL_DIMENSIONS`，引擎與 API 完全不需修改。

---

## 🧪 測試

```bash
cd backend
pip install -r requirements.txt
pytest                      # 核心引擎測試（indicators / alpha / ai）
```

---

## 🛣️ 開發流程與未來擴充

1. **真實籌碼資料** — 接入 TWSE／TPEx 三大法人與融資融券盤後資料。
2. **真實基本面** — 接入公開資訊觀測站財報與月營收。
3. **合法新聞來源** — 取代題材面的 mock 新聞。
4. **模型驗證深化** — 納入交易成本、最大回撤與不同市場狀態切片。
5. **資料庫遷移** — 導入 Alembic 取代啟動時 `create_all`。

策略使用方式與計分細節請見 [`docs/RECOMMENDATION_STRATEGY.md`](docs/RECOMMENDATION_STRATEGY.md)。
系統架構與設計決策請見 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

---

## ⚠️ 免責聲明

價格與技術預測使用 TWSE／TPEx 官方盤後資料；籌碼、財報、新聞及完整 Alpha Score
目前仍包含模擬資料。所有評分與回測僅供研究，**不構成任何投資建議**。
