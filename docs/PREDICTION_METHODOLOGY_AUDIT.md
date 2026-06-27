# technical_eod_v1 預測方法論審核文件

本文提供 Taiwan Alpha Radar 目前每日預測模型 `technical_eod_v1` 的完整方法說明，目標是讓其他 AI 或工程審核者可以獨立檢查：

- 模型使用哪些資料。
- 每個分數如何計算。
- 排名與方向如何產生。
- 回測與每日對答案如何定義。
- 目前有哪些偏差與限制。

> 本文件描述的是「預測驗證」頁使用的 `technical_eod_v1`，不是完整 Alpha Score。完整 Alpha Score
> 已接入部分真實盤後籌碼資料，但財報、新聞與部分籌碼細節仍包含 mock，不應拿來單獨驗證真實預測能力。

## 1. 核心結論

`technical_eod_v1` 是一個**盤後技術動能排序模型**。

它只使用每檔股票截至預測日收盤為止的 OHLCV：

- open
- high
- low
- close
- volume
- change_pct

模型不使用：

- 即時行情。
- 盤中成交。
- 籌碼資料。
- 財報資料。
- 新聞資料。
- 未來價格。
- LLM 或 AI 生成判斷。

因此它適合回答：

> 某個交易日收盤後，在目前追蹤股票池中，哪些股票的技術狀態相對較強？

它不適合回答：

> 明天開盤能不能買、盤中會不會漲、精準目標價是多少。

## 2. 主要實作位置

| 功能 | 檔案 |
|---|---|
| 技術分數公式 | `backend/app/alpha/dimensions/technical.py` |
| 產生每日預測 | `backend/app/services/backtest.py` 的 `build_predictions` |
| 預測方向 | `backend/app/services/backtest.py` 的 `_direction` |
| 評估預測結果 | `backend/app/services/backtest.py` 的 `evaluate_predictions` |
| 最新預測 API | `backend/app/services/backtest.py` 的 `get_latest_predictions` |
| 每日對答案 API | `backend/app/services/backtest.py` 的 `get_daily_prediction_results` |
| API schema | `backend/app/schemas/backtest.py` |
| API route | `backend/app/api/routes/backtest.py` |
| 前端頁面 | `frontend/src/app/predictions/page.tsx` |

## 3. 資料來源

目前本機與 Docker pipeline 會使用 TWSE／TPEx 官方盤後收盤資料。

系統標記：

```text
methodology = technical_eod_v1
data_source = twse_tpex_official
```

資料表：

| 表 | 說明 |
|---|---|
| `daily_prices` | 每檔股票每日 OHLCV |
| `daily_predictions` | 每檔股票每日預測分數、方向、排名 |
| `prediction_outcomes` | 每筆預測在未來 1/3/5/10 個交易日後的結果 |
| `stocks` | 股票基本資料，包含 `theme` 族群 |

## 4. 預測產生流程

`build_predictions` 對每一檔股票、每一個可預測交易日執行以下流程：

```text
for stock in stocks:
    prices = stock 的歷史 daily_prices，依 trade_date 遞增
    if len(prices) < 25:
        skip

    start = max(24, len(prices) - prediction_lookback_days)

    for index in range(start, len(prices)):
        window = prices[0:index+1]
        score = TechnicalDimension.score(window)
        direction = _direction(score)
        confidence = min(100, abs(score - 50) * 2)
        entry_close = prices[index].close
        save DailyPrediction

for each prediction_date:
    sort predictions by signal_score desc
    assign rank = 1, 2, 3...
```

重要特性：

- 每個預測日只使用當日與過去資料。
- 排名是同一日期內的相對排名。
- 綜合 tab 是全股票池排名。
- 族群 tab 是查詢時依 `stocks.theme` 篩選後重新編號，資料表內仍只保存綜合排名。

## 5. 技術分數公式

技術分數從 50 分開始，最後 clamp 到 0 至 100。

```text
score = 50
```

若收盤價資料少於 25 筆：

```text
score = 50
reason = 資料不足，給予中性分數
```

### 5.1 均線趨勢

計算：

```text
MA5  = 最近 5 筆 close 平均
MA20 = 最近 20 筆 close 平均
MA60 = 最近 60 筆 close 平均；若資料不足 60 筆，改用可用資料長度 - 1
last = 預測日 close
```

加減分：

| 條件 | 分數 |
|---|---:|
| `last > MA5 > MA20 > MA60` | `+18` |
| `last < MA5 < MA20 < MA60` | `-18` |
| 其他狀況且 `last > MA20` | `+6` |
| 其他狀況且 `last <= MA20` | `-6` |

### 5.2 20 日動能

計算 20 日漲跌幅：

```text
momentum_20d_pct = (last_close / close_20_days_ago - 1) * 100
```

動能貢獻：

```text
score += clamp(momentum_20d_pct * 0.6, -15, +15)
```

解讀：

- 20 日漲幅越大，分數越高。
- 單靠動能最多加 15 分。
- 單靠動能最多扣 15 分。

### 5.3 RSI(14)

使用 14 日 RSI。

| RSI 條件 | 分數 | 解讀 |
|---|---:|---|
| `50 <= RSI <= 70` | `+8` | 強勢但未過熱 |
| `RSI > 80` | `-6` | 過熱 |
| `RSI < 30` | `-4` | 弱勢 |
| 其他 | `0` | 中性 |

### 5.4 成交量確認

計算前 20 日平均量，不含預測日：

```text
volume_avg_20 = average(volume[-21:-1])
```

若符合：

```text
today_volume > volume_avg_20 * 1.3
and today_close > yesterday_close
```

則：

```text
score += 6
```

### 5.5 最終分數

最後透過 `DimensionScorer._result` 限制在 0 至 100：

```text
score = min(100, max(0, score))
```

## 6. 方向與信心度

方向由技術分數直接轉換：

| 分數 | 方向 |
|---:|---|
| `score >= 60` | 偏多 |
| `score <= 40` | 偏空 |
| 其他 | 中性 |

信心度不是勝率，而是分數偏離中性 50 的程度：

```text
confidence = min(100, abs(score - 50) * 2)
```

例子：

| 技術分數 | 信心度 |
|---:|---:|
| 50 | 0 |
| 60 | 20 |
| 70 | 40 |
| 90 | 80 |

## 7. 排名邏輯

### 7.1 綜合排名

同一個 `prediction_date` 內，所有股票依 `signal_score` 由高到低排序。

```text
rank 1 = 當日技術分數最高
```

### 7.2 族群排名

族群 tab 不額外產生新預測，而是在 API 查詢時做篩選：

```text
WHERE stocks.theme = selected_theme
ORDER BY daily_predictions.rank
LIMIT 10
```

前端顯示時重新編號：

```text
族群內 rank = 1, 2, 3...
```

因此：

- 綜合 `#1` 是全股票池最強。
- AI `#1` 是 AI 族群中最強。
- 半導體 `#1` 是半導體族群中最強。

## 8. 每日對答案

每日對答案使用 `prediction_outcomes` 中 `horizon_days = 1` 的結果。

### 8.1 收盤到收盤報酬

目前主要驗證報酬：

```text
return_pct = (result_close / prediction_close - 1) * 100
```

其中：

- `prediction_close` = 預測日收盤價。
- `result_close` = 下一個可交易日收盤價。

這適合驗證方向，但不完全等於可成交策略，因為訊號是收盤後才產生。

### 8.2 開盤到收盤報酬

每日對答案頁也顯示：

```text
open_to_close_pct = (result_close / result_open - 1) * 100
```

這較接近「隔日開盤後才知道訊號並交易」的單日結果，但目前仍未扣交易成本。

### 8.3 命中判定

```text
if direction == 偏多:
    direction_correct = return_pct > 0
elif direction == 偏空:
    direction_correct = return_pct < 0
else:
    direction_correct = abs(return_pct) < 1
```

中性方向以絕對漲跌小於 1% 視為命中。

## 9. 回測摘要

`evaluate_predictions` 預設計算以下 horizon：

```text
1, 3, 5, 10 個交易日
```

每個 horizon 的報酬：

```text
return_pct = (exit_close / entry_close - 1) * 100
```

等權基準：

```text
benchmark_return_pct =
    同一 prediction_date、同一 horizon、所有可計算股票 return_pct 的平均
```

超額報酬：

```text
excess_return_pct = return_pct - benchmark_return_pct
```

回測摘要目前使用每日 Top group：

```text
top_count = min(10, max(1, ceil(stock_count * 0.25)))
```

目前股票池 40 檔，所以：

```text
top_count = 10
```

摘要指標：

| 指標 | 定義 |
|---|---|
| `top10_average_return_pct` | Top 10 平均報酬 |
| `benchmark_return_pct` | 股票池等權平均報酬 |
| `top10_excess_return_pct` | Top 10 報酬 - 等權基準 |
| `top10_win_rate_pct` | Top 10 中報酬大於 0 的比例 |
| `direction_accuracy_pct` | Top 10 中方向命中的比例 |

## 10. API 重現方式

### 10.1 最新綜合預測

```bash
curl 'http://localhost:8000/api/predictions?limit=10'
```

### 10.2 最新族群預測

```bash
curl 'http://localhost:8000/api/predictions?theme=AI&limit=10'
curl 'http://localhost:8000/api/predictions?theme=半導體&limit=10'
```

### 10.3 最新每日對答案

```bash
curl 'http://localhost:8000/api/prediction-results?limit=10'
```

### 10.4 指定日期對答案

```bash
curl 'http://localhost:8000/api/prediction-results?date=2026-06-12&limit=10'
```

### 10.5 指定日期 + 族群對答案

```bash
curl 'http://localhost:8000/api/prediction-results?date=2026-06-12&theme=AI&limit=10'
```

### 10.6 回測摘要

```bash
curl 'http://localhost:8000/api/backtest'
```

## 11. 可用 SQL 檢查

以下以 SQLite 本機資料庫為例。

### 11.1 查看最新預測日

```sql
SELECT MAX(prediction_date)
FROM daily_predictions
WHERE methodology = 'technical_eod_v1';
```

### 11.2 查看某日 Top 10

```sql
SELECT
  p.rank,
  p.stock_id,
  s.name,
  s.theme,
  p.signal_score,
  p.direction,
  p.confidence,
  p.entry_close
FROM daily_predictions p
JOIN stocks s ON s.stock_id = p.stock_id
WHERE p.methodology = 'technical_eod_v1'
  AND p.prediction_date = '2026-06-12'
ORDER BY p.rank
LIMIT 10;
```

### 11.3 查看某日 AI 族群排名

```sql
SELECT
  ROW_NUMBER() OVER (ORDER BY p.rank) AS local_rank,
  p.rank AS overall_rank,
  p.stock_id,
  s.name,
  s.theme,
  p.signal_score,
  p.direction
FROM daily_predictions p
JOIN stocks s ON s.stock_id = p.stock_id
WHERE p.methodology = 'technical_eod_v1'
  AND p.prediction_date = '2026-06-12'
  AND s.theme = 'AI'
ORDER BY p.rank;
```

### 11.4 查看某日隔日結果

```sql
SELECT
  p.rank,
  p.stock_id,
  s.name,
  p.direction,
  o.return_pct,
  o.benchmark_return_pct,
  o.excess_return_pct,
  o.direction_correct
FROM daily_predictions p
JOIN stocks s ON s.stock_id = p.stock_id
JOIN prediction_outcomes o
  ON o.prediction_id = p.id
 AND o.horizon_days = 1
WHERE p.methodology = 'technical_eod_v1'
  AND p.prediction_date = '2026-06-12'
ORDER BY p.rank
LIMIT 10;
```

## 12. 外部 AI 審核清單

建議外部 AI 或 reviewer 依序檢查：

1. `TechnicalDimension.score` 是否只依賴 OHLCV。
2. `build_predictions` 是否只使用 `prices[:index+1]`，沒有使用未來資料。
3. `prediction_date` 是否等於預測訊號產生當日。
4. `entry_close` 是否等於預測日收盤價。
5. `evaluate_predictions` 是否使用未來第 N 個交易日收盤價計算 outcome。
6. `benchmark_return_pct` 是否為同日同 horizon 股票池等權平均。
7. `direction_correct` 的中性判定是否合理。
8. 族群 tab 是否只是查詢篩選，不是另一套模型。
9. 前端顯示的族群 rank 是否為重新編號後的 local rank。
10. 是否存在除權息、交易成本、滑價或開盤跳空造成的回測偏差。

## 13. 已知限制

目前版本有以下限制，審核時應明確納入：

- 價格尚未完整做除權息還原。
- 回測未扣手續費、交易稅、滑價與買賣價差。
- 收盤到收盤驗證會高估可交易性，因為訊號在收盤後才知道。
- 股票池固定，可能有樣本選擇偏誤。
- 沒有處理流動性門檻。
- 沒有停損、停利、部位大小與資金曲線。
- 沒有針對多頭、空頭、震盪市場分 regime。
- 目前技術公式是規則式模型，未做參數最佳化或樣本外訓練。
- `confidence` 不是機率，也不是歷史勝率。
- 族群 tab 的「相對同族群」比較只在該族群內計算，不能直接和綜合 tab 的超額報酬等同解讀。

## 14. 審核者可提出的改進方向

若要讓模型更接近可交易策略，建議優先審核或擴充：

1. 改用隔日開盤買進作為主要績效。
2. 加入交易成本與滑價。
3. 做除權息還原價格。
4. 增加成交量或成交金額門檻。
5. 將市場狀態分為多頭、空頭、震盪後分別回測。
6. 比較 `technical_eod_v1` 與簡單基準模型，例如隨機選股、前日漲幅排行、均線單因子。
7. 做 rolling window walk-forward，而不是只看累積總表。
8. 將每次公式改版命名為新 methodology，例如 `technical_eod_v2`，保留舊模型對照。

## 15. 免責聲明

`technical_eod_v1` 是研究用途的盤後技術排序模型，不構成任何投資建議。任何真實交易前，必須另行評估交易成本、流動性、風險承受能力與法規限制。
