# 架構說明 — Taiwan Alpha Radar

## 定位

這是一個**每日選股決策平台**，不是看盤系統、不是下單系統。
系統每天分析台股，產出大盤、類股、個股評分與 AI 投資報告，協助使用者做選股決策。

## 系統分層

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 / TS / Tailwind / shadcn 風格 / Recharts) │
│  Dashboard · 大盤 · 族群 · 選股排行 · 個股分析                  │
└───────────────▲──────────────────────────────────────────────┘
                │  REST (JSON)  /api/*
┌───────────────┴──────────────────────────────────────────────┐
│  FastAPI                                                       │
│   api/         路由層 (dashboard / market / sectors / stocks)  │
│   services/    pipeline 編排 · queries 讀取 · cache (Redis)    │
│   alpha/       評分引擎 (Strategy Pattern, 5 維度)             │
│   ai/          報告引擎 (Provider Pattern: mock/openai/anthropic)│
│   collectors/  資料蒐集 (ABC + Mock Provider, 4 領域)          │
│   domain/      universe (台股清單) · simulator (確定性模擬)    │
│   models/      SQLAlchemy ORM (6 張表)                         │
│   scheduler/   APScheduler 每日排程                            │
└───────────────▲───────────────────────▲──────────────────────┘
                │                        │
         ┌──────┴─────┐           ┌──────┴─────┐
         │ PostgreSQL │           │   Redis    │
         └────────────┘           └────────────┘
```

## 資料流（每日 Pipeline）

`services/pipeline.py:run_daily_pipeline` 是唯一編排入口，排程與 seed 都呼叫它：

1. `sync_universe` — 確保 `stocks` 表含 universe 全部標的
2. **個股評分** — `StockScoreEngine` 對每檔股票：
   - `collectors` 取得價格 / 籌碼 / 基本面 / 新聞
   - 5 個 `DimensionScorer` 各自評分 → 加權合成 Alpha Score
3. **持久化** — 排名後寫入 `stock_scores`、近 60 日 `daily_prices`
4. **族群評分** — `aggregate_sectors` 依題材聚合 → `sector_scores`
5. **市場溫度** — `compute_market_score` 依市場廣度/指數強度/平均分 → `market_scores`
6. **AI 報告** — 前 10 名個股由 `ReportEngine` 生成 → `ai_reports`

整個 pipeline 對 `(實體, 日期)` 為 upsert，重跑同一天具冪等性。

## 關鍵設計決策

| 決策 | 理由 |
|------|------|
| **Strategy Pattern 評分維度** | 每個維度是獨立 class，新增維度（如 ESG、選擇權籌碼）只需加一個 class 並註冊，引擎與 API 不變。 |
| **Provider Pattern AI** | `AIProvider` 抽象，OpenAI / Anthropic / mock 可互換，由 `AI_PROVIDER` 環境變數切換；任何 LLM 失敗都會 fallback 到 mock，不中斷 pipeline。 |
| **Collector ABC + Registry** | 4 領域資料源各有抽象介面，目前是 Mock Provider；接真實資料（FinMind / TWSE OpenAPI）只需實作 ABC 並在 registry 分支。 |
| **確定性模擬器** | 以 `sha256(stock_id)` 為種子，重啟容器資料不變，方便展示與測試。 |
| **JSONB 存 breakdown** | 維度明細與指標以 JSONB 儲存，新增維度免 schema migration。 |
| **Redis graceful fallback** | Redis 不可用時快取自動降級為 no-op，不影響服務。 |
| **啟動自動 seed** | 後端啟動即建表 + 灌當日分析，`docker compose up` 一鍵即可展示。 |

## Alpha Score 組成

| 維度 | 權重 | 衡量 |
|------|------|------|
| 技術面 technical | 30% | 均線排列、動能、RSI、量價 |
| 籌碼面 institutional | 25% | 三大法人買賣超、外資持股、融資 |
| 基本面 fundamental | 20% | ROE、營收年增、本益比、毛利、殖利率 |
| 題材面 thematic | 15% | 題材熱度 + 新聞情緒 |
| 風險面 risk | 10% | 波動度、最大回檔、過熱（分數越高越安全） |

## 未來擴充

- **真實資料源**：實作 `collectors/*` 的 ABC（FinMind、TWSE OpenAPI、券商 API）。
- **更多維度**：在 `alpha/dimensions/` 新增 class 並加入 `ALL_DIMENSIONS`。
- **回測模組**：pipeline 已支援任意 `as_of` 日期，可擴充歷史回測。
- **使用者自選池 / 通知**：在 services 層加入 watchlist 與推播。
- **資料庫遷移**：導入 Alembic 取代 `create_all`。
