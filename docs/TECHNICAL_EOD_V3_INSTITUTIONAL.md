# technical_eod_v3_institutional 盤後法人籌碼模型

`technical_eod_v3_institutional` 是 Taiwan Alpha Radar 的第三套盤後候選模型。

它的目的不是取代 v1/v2，而是並行驗證：

> 加入三大法人盤後買賣超後，是否能改善每日觀察清單的 1 / 3 / 5 / 10 日表現？

## 1. 模型定位

| 模型 | 資料 | 用途 |
|---|---|---|
| `technical_eod_v1` | 官方收盤 OHLCV | 技術 baseline |
| `technical_eod_v2_candidate` | v1 + 市場廣度 + 品質標籤 | 技術品質候選 |
| `technical_eod_v3_institutional` | v2 + 三大法人盤後買賣超 | 法人籌碼候選 |

V3 使用的是**盤後正式資料**，不是盤中法人估算。

## 2. 三大法人資料

資料來源：

- TWSE 三大法人買賣超日報。
- TPEx 三大法人買賣明細資訊。

系統會持久化到：

```text
daily_institutional_flows
```

欄位：

```text
stock_id
trade_date
data_source
foreign_net
trust_net
dealer_net
total_net
```

單位：

```text
千股
```

## 3. V3 分數邏輯

V3 先沿用 v2 的技術與市場狀態邏輯：

```text
base_score = technical_eod_v2_candidate.adjusted_score
```

再加入法人調整：

```text
institutional_intensity =
  三大法人合計買賣超千股 / 最近 5 日平均成交量千股
```

```text
institutional_adjustment =
  clamp(institutional_intensity * 10, -12, +12)
```

若外資與投信同步買超：

```text
institutional_adjustment += 5
institutional_tag = institutional_accumulation
```

若外資與投信同步賣超：

```text
institutional_adjustment -= 5
institutional_tag = institutional_distribution
```

最終：

```text
adjusted_score = clamp(base_score + institutional_adjustment, 0, 100)
```

## 4. API 欄位

`GET /api/predictions?methodology=technical_eod_v3_institutional`

每筆 item 會額外包含：

```text
institutional_foreign_net
institutional_trust_net
institutional_dealer_net
institutional_total_net
institutional_intensity
institutional_tag
institutional_reason
```

## 5. 盤中暫估限制

盤中不能精準取得今日三大法人買賣超，因為三大法人資料是盤後彙整。

因此目前沒有實作：

```text
technical_intraday_preview_v3
```

若未來要做，只能先使用：

```text
盤中價格 snapshot + 上一交易日法人資料
```

並且必須明確標示：

```text
法人資料尚未收盤更新
```

## 6. 驗證重點

V3 應該和 v1/v2 並行觀察：

- Top 10 平均報酬。
- 超額報酬。
- 勝率。
- 方向命中率。
- 法人買盤標籤是否優於法人賣壓標籤。

不能只看單日命中，至少要比較 1 / 3 / 5 / 10 日。

