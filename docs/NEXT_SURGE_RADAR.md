# 下一版：飆股雷達預測

本文是給下一個 session 的交接文件。  
目前已完成：

- `technical_eod_v1`
- `technical_eod_v2_candidate`
- 盤中未收盤暫估 `technical_intraday_preview_*`
- 預測頁熱門題材 tab：
  - 記憶體
  - 低軌衛星
  - 被動元件
  - PCB高階材料
  - 玻纖布

下一版目標是新增「飆股雷達」，用來辨識市場口中的強勢飆股候選。

## 1. 產品定位

飆股雷達不是保證股票會上漲，也不是喊單工具。

它要回答的是：

> 在目前股票池裡，哪些股票出現「強勢發動、主升段、或過熱」特徵？

建議頁面名稱：

```text
飆股雷達
```

或先做在預測頁的新 tab：

```text
飆股候選
```

## 2. 與現有模型的關係

現有模型：

- v1：收盤技術排序 baseline。
- v2_candidate：v1 + 市場廣度 + 品質標籤。
- intraday_preview：收盤前暫估。

飆股雷達應該是新 methodology 或新 service，不要直接覆蓋 v1/v2：

```text
surge_radar_v1
```

它可以引用 v2 的資訊，例如：

- `signal_score`
- `adjusted_score`
- `market_breadth`
- `quality_tag`
- 熱門題材 tag

但它的 ranking 目標不同：  
v1/v2 是「相對穩健的觀察清單」，飆股雷達是「高動能 / 高波動候選」。

## 3. 第一版資料來源

第一版先做純價量，不要急著接新聞或社群。

使用資料：

- 官方盤後 OHLCV
- 盤中 preview OHLCV 若可用
- universe 的 `tags`

先不要依賴：

- 社群文章
- YouTube 標題
- 新聞爬蟲
- LLM 判斷

這樣可回測，也比較不會有資料授權問題。

## 4. 建議特徵

每檔股票計算：

```text
return_1d_pct
return_5d_pct
return_20d_pct
volume_ratio_5d
volume_ratio_20d
rsi_14
ma_state
gap_from_ma20_pct
limit_up_like
hot_topic_bonus
```

可沿用：

```text
backend/app/alpha/features/technical_features.py
```

若特徵變多，建議新增：

```text
backend/app/alpha/features/surge_features.py
```

## 5. surge_score 候選公式

第一版可以先用規則式分數：

```text
surge_score = 50

if return_5d_pct > 8:
    surge_score += 12
elif return_5d_pct > 4:
    surge_score += 6

if return_20d_pct > 20:
    surge_score += 14
elif return_20d_pct > 10:
    surge_score += 8

if volume_ratio_20d >= 2:
    surge_score += 12
elif volume_ratio_20d >= 1.5:
    surge_score += 6

if ma_state == "bull_stack":
    surge_score += 10

if quality_tag == "high_quality":
    surge_score += 6
elif quality_tag == "market_supported":
    surge_score += 3

if stock has hot topic tag:
    surge_score += 5

if rsi_14 > 85:
    surge_score -= 10
elif rsi_14 > 78:
    surge_score -= 5

surge_score = clamp(0, 100)
```

## 6. 狀態分類

不要只給分數，還要給人類可讀狀態：

```text
剛發動
主升段
過熱警示
觀察
```

建議規則：

```text
if surge_score >= 75 and rsi_14 <= 78 and volume_ratio_20d >= 1.5:
    surge_state = "主升段"
elif return_5d_pct >= 4 and volume_ratio_20d >= 1.5 and rsi_14 <= 75:
    surge_state = "剛發動"
elif rsi_14 > 78 or return_5d_pct > 18:
    surge_state = "過熱警示"
else:
    surge_state = "觀察"
```

## 7. API 建議

新增 endpoint：

```text
GET /api/surge-radar
```

Query params：

```text
limit=20
theme=
topic=
mode=eod | intraday_preview
```

Response item：

```json
{
  "rank": 1,
  "stock_id": "2337",
  "name": "旺宏",
  "theme": "半導體",
  "tags": ["記憶體"],
  "surge_score": 88.4,
  "surge_state": "主升段",
  "return_5d_pct": 12.3,
  "return_20d_pct": 35.8,
  "volume_ratio_20d": 2.4,
  "rsi_14": 71.2,
  "quality_tag": "high_quality",
  "reason": "20日動能強、量能放大、均線多頭且屬記憶體熱門題材。"
}
```

## 8. 前端建議

新增頁面：

```text
frontend/src/app/surge-radar/page.tsx
```

或先掛在 predictions 頁：

```text
每日預測與回測驗證
├─ v1/v2 模型
├─ 盤中暫估
└─ 飆股雷達
```

表格欄位：

- 排名
- 股票
- 題材 tag
- 飆股分數
- 狀態
- 5日漲幅
- 20日漲幅
- 量能倍數
- RSI
- 理由

## 9. 回測驗證

需要驗證：

```text
被標為剛發動 / 主升段 / 過熱警示後
未來 1 / 3 / 5 / 10 日報酬如何
```

特別要比較：

- `surge_radar_v1 Top10`
- `technical_eod_v2_candidate Top10`
- 同題材等權平均
- 股票池等權平均

## 10. 注意事項

- 飆股雷達會偏向高波動股票，風險高於 v1/v2。
- 不要把 `surge_score` 寫成勝率。
- `過熱警示` 不是做空訊號，只是提醒追高風險。
- 若要接新聞/社群，請另開資料來源設計，不要先混進第一版。

