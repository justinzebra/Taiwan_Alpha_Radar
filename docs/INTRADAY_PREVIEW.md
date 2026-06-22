# 盤中暫估預測

盤中暫估預測用於解決「等正式收盤訊號出來，隔天可能已經跳空或漲停」的實務問題。

它不是正式 EOD 模型，也不會覆蓋正式收盤預測。

## 1. Methodology

目前新增兩個 preview methodology：

```text
technical_intraday_preview_v1
technical_intraday_preview_v2_candidate
```

它們和正式模型的關係：

| 正式模型 | 盤中暫估 |
|---|---|
| `technical_eod_v1` | `technical_intraday_preview_v1` |
| `technical_eod_v2_candidate` | `technical_intraday_preview_v2_candidate` |

preview 只改資料來源，不改 scoring 公式：

```text
歷史官方 daily_prices
+ 今日盤中 snapshot 組成的暫時 OHLCV
→ 產生未收盤暫估排名
```

## 2. 手動刷新行為

儀表板按下「手動刷新」後會做兩件事：

1. 照舊重跑正式 EOD pipeline。
2. 嘗試抓 TWSE MIS 盤中 snapshot，建立 preview predictions。

如果盤中 quote 抓不到，或交易所回傳的 quote 日期不是今天，系統會回傳：

```text
盤中行情暫時無法取得，未建立未收盤暫估。
```

這是刻意設計，避免把昨天最後一筆報價誤標成今天的未收盤預測。

## 3. 標記方式

preview rows 會寫入 `daily_predictions`，但會標記：

```text
is_preview = true
price_status = intraday_preview
price_timestamp = quote 建立時間
```

正式收盤模型則是：

```text
is_preview = false
price_status = final_close
```

## 4. 不納入正式回測

preview 不會產生正式 `prediction_outcomes`。

原因：

- preview 使用未收盤資料。
- 收盤前價格、成交量、排名都可能改變。
- 盤中 snapshot 的可交易性和正式收盤資料不同。

因此 preview 頁面會提示：

```text
未收盤暫估不納入正式 walk-forward 回測。
```

正式勝率與超額報酬仍以：

```text
technical_eod_v1
technical_eod_v2_candidate
```

為準。

## 5. 資料源限制

目前第一版使用 TWSE MIS endpoint 做 best-effort snapshot。這不是完整授權即時行情 feed。

若要做更穩定的盤中預測，建議後續改接：

- 券商行情 API。
- Fugle / 富邦類型 intraday quote API。
- 正式授權行情 feed。

正式交易決策前，仍應確認資料延遲、授權條款、流動性與交易成本。

