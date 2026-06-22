# technical_eod_v2_candidate 並行觀察模型

`technical_eod_v2_candidate` 是 Taiwan Alpha Radar 的第二套盤後技術候選模型。

它不是正式升級版，也不會取代 `technical_eod_v1`。目前設計目標是：

- 保留 `technical_eod_v1` 作為 baseline。
- 在同一套 pipeline 中並行產生 v1 與 v2_candidate。
- 觀察「市場廣度」與「高品質訊號」是否能穩定改善未來 3 至 5 個交易日表現。
- 避免直接把歷史最佳條件硬套成正式模型，降低 overfitting 風險。

## 1. 和 v1 的關係

v2_candidate 的基礎分數仍使用 v1 的 `signal_score`。

v1 保持不動：

- 不修改 `technical_eod_v1` 公式。
- 不覆蓋 v1 的 `daily_predictions`。
- 不覆蓋 v1 的 `prediction_outcomes`。
- API 預設仍回傳 v1。

v2_candidate 另存：

```text
methodology = technical_eod_v2_candidate
```

因此可用以下 API 對照：

```bash
curl 'http://localhost:8000/api/predictions?methodology=technical_eod_v1'
curl 'http://localhost:8000/api/predictions?methodology=technical_eod_v2_candidate'

curl 'http://localhost:8000/api/backtest?methodology=technical_eod_v1'
curl 'http://localhost:8000/api/backtest?methodology=technical_eod_v2_candidate'
```

## 2. 新增市場廣度

市場廣度定義：

```text
market_breadth =
  當日股票池中 close > previous_close 的股票數
  / 當日可計算股票總數
```

市場狀態：

```text
if market_breadth >= 0.6:
    market_regime = "risk_on"
elif market_breadth >= 0.5:
    market_regime = "neutral_positive"
else:
    market_regime = "risk_off"
```

解讀：

| market_regime | 意義 |
|---|---|
| `risk_on` | 多數股票上漲，技術動能較有市場環境支持 |
| `neutral_positive` | 市場略偏正向，但強度未達全面 risk-on |
| `risk_off` | 多數股票未上漲，偏多訊號需要降級觀察 |

## 3. 品質標籤

v2_candidate 新增 `quality_tag` 與 `quality_reason`。

規則：

```text
if signal_score >= 60
and market_breadth >= 0.5
and 50 <= rsi_14 <= 70
and volume_confirm == true:
    quality_tag = "high_quality"
elif signal_score >= 60 and market_breadth >= 0.5:
    quality_tag = "market_supported"
elif signal_score >= 60 and market_breadth < 0.5:
    quality_tag = "watch_only"
else:
    quality_tag = "neutral"
```

標籤說明：

| quality_tag | 顯示 | 說明 |
|---|---|---|
| `high_quality` | 高品質 | 個股偏多、市場廣度支持、RSI 健康且有量價確認 |
| `market_supported` | 市場支持 | 個股偏多且市場廣度支持，但未完全符合高品質條件 |
| `watch_only` | 觀察 | 個股偏多，但市場廣度不足 50% |
| `neutral` | 中性 | 技術分數尚未達偏多門檻 |

## 4. 調整後分數與排名

v2_candidate 不只用 `signal_score` 排名，而是計算 `adjusted_score`：

```text
adjusted_score = signal_score

if market_breadth < 0.5:
    adjusted_score -= 8

if quality_tag == "high_quality":
    adjusted_score += 6
elif quality_tag == "market_supported":
    adjusted_score += 3
elif quality_tag == "watch_only":
    adjusted_score -= 5

adjusted_score = clamp(adjusted_score, 0, 100)
```

v2_candidate 的 `rank` 使用 `adjusted_score` 由高到低排序。

API 仍同時回傳：

- `signal_score`
- `adjusted_score`
- `rank`
- `market_breadth`
- `market_regime`
- `quality_tag`
- `quality_reason`

## 5. 主要觀察週期

v2_candidate 的產品定位不是「明日必漲」或「隔日精準預測」。

建議表述：

> 收盤後建立未來 3 至 5 個交易日觀察清單。

原因是初步分析顯示，v1 在近期樣本中的 3 至 5 日結果比隔日更穩定。
v2_candidate 也應優先觀察 3 至 5 個交易日，而不是只用隔日勝率定生死。

## 6. 避免 overfitting 的原則

v2_candidate 來自歷史資料中的共同條件，但不直接宣稱優於 v1。

目前採取的保守做法：

1. v1 保留為 baseline。
2. v2_candidate 並行產生、並行回測。
3. outcome 分 methodology 保存與查詢。
4. 至少累積 1 至 2 個月新資料後，再評估是否升級為正式 v2。
5. 每次正式改版應使用新 methodology 名稱，避免污染歷史比較。

## 7. 已知限制

- 價格尚未完整做除權息還原。
- 未納入交易成本、滑價與買賣價差。
- 目前仍是收盤後訊號，收盤到收盤驗證不等同可實際成交策略。
- 市場廣度以目前股票池計算，股票池本身可能有樣本選擇偏誤。
- `quality_tag` 是規則標籤，不是機率，也不是保證勝率。

