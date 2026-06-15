"use client";

import Link from "next/link";
import { useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Database,
  FlaskConical,
  Target,
} from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { cn, dirColor, fmtNumber, fmtPct, scoreColor } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorPanel, LoadingPanel } from "@/components/common/States";

function DailyScorecard() {
  const [selectedDate, setSelectedDate] = useState("");
  const results = useApi(
    () => api.predictionResults(selectedDate || undefined, 10),
    [selectedDate],
  );

  if (results.loading) return <LoadingPanel label="載入每日對答案…" />;
  if (results.error || !results.data) {
    return <ErrorPanel message={results.error ?? "無每日驗證資料"} />;
  }

  const data = results.data;
  if (!data.prediction_date || data.items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>每日對答案</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          尚無已完成隔日驗證的預測。
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-4 w-4" /> 每日對答案
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              {data.prediction_date} 收盤預測 → {data.result_date} 收盤結果
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            <CalendarDays className="h-4 w-4" />
            預測日期
            <select
              value={data.prediction_date}
              onChange={(event) => setSelectedDate(event.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
            >
              {data.available_dates.map((date) => (
                <option key={date} value={date}>
                  {date}
                </option>
              ))}
            </select>
          </label>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <div className="text-xs text-muted-foreground">方向命中</div>
            <div className="mt-1 tnum text-xl font-semibold">
              {data.direction_accuracy_pct.toFixed(1)}%
            </div>
          </div>
          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <div className="text-xs text-muted-foreground">上漲檔數</div>
            <div className="mt-1 tnum text-xl font-semibold">
              {data.positive_count}/{data.evaluated_predictions}
            </div>
            <div className="text-xs text-muted-foreground">
              勝率 {data.win_rate_pct.toFixed(1)}%
            </div>
          </div>
          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <div className="text-xs text-muted-foreground">Top 10 平均</div>
            <div className={cn("mt-1 tnum text-xl font-semibold", dirColor(data.average_return_pct))}>
              {fmtPct(data.average_return_pct)}
            </div>
          </div>
          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <div className="text-xs text-muted-foreground">相對股票池</div>
            <div className={cn("mt-1 tnum text-xl font-semibold", dirColor(data.excess_return_pct))}>
              {fmtPct(data.excess_return_pct)}
            </div>
            <div className="text-xs text-muted-foreground">
              基準 {fmtPct(data.benchmark_return_pct)}
            </div>
          </div>
          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <div className="text-xs text-muted-foreground">隔日開盤後平均</div>
            <div
              className={cn(
                "mt-1 tnum text-xl font-semibold",
                dirColor(data.average_open_to_close_pct ?? 0),
              )}
            >
              {data.average_open_to_close_pct === null
                ? "-"
                : fmtPct(data.average_open_to_close_pct)}
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">股票</th>
                <th className="px-3 py-2 text-right">訊號</th>
                <th className="px-3 py-2 text-right">方向</th>
                <th className="px-3 py-2 text-right">預測日收盤</th>
                <th className="px-3 py-2 text-right">結果日開盤</th>
                <th className="px-3 py-2 text-right">結果日收盤</th>
                <th className="px-3 py-2 text-right">收盤→收盤</th>
                <th className="px-3 py-2 text-right">開盤→收盤</th>
                <th className="px-3 py-2 text-right">判定</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.stock_id} className="border-t border-border/50">
                  <td className="px-3 py-3 tnum text-muted-foreground">{item.rank}</td>
                  <td className="px-3 py-3">
                    <Link href={`/stocks/${item.stock_id}`} className="font-medium hover:text-primary">
                      {item.name}
                    </Link>
                    <span className="ml-2 tnum text-xs text-muted-foreground">
                      {item.stock_id}
                    </span>
                  </td>
                  <td className={cn("px-3 py-3 text-right tnum font-semibold", scoreColor(item.signal_score))}>
                    {item.signal_score.toFixed(1)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <Badge variant={item.direction === "偏多" ? "bull" : item.direction === "偏空" ? "bear" : "outline"}>
                      {item.direction}
                    </Badge>
                  </td>
                  <td className="px-3 py-3 text-right tnum">{fmtNumber(item.prediction_close)}</td>
                  <td className="px-3 py-3 text-right tnum">
                    {item.result_open === null ? "-" : fmtNumber(item.result_open)}
                  </td>
                  <td className="px-3 py-3 text-right tnum">{fmtNumber(item.result_close)}</td>
                  <td className={cn("px-3 py-3 text-right tnum font-medium", dirColor(item.return_pct))}>
                    {fmtPct(item.return_pct)}
                  </td>
                  <td className={cn("px-3 py-3 text-right tnum", dirColor(item.open_to_close_pct ?? 0))}>
                    {item.open_to_close_pct === null ? "-" : fmtPct(item.open_to_close_pct)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <Badge variant={item.direction_correct ? "bull" : "bear"}>
                      {item.direction_correct ? "命中" : "未命中"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-xs leading-relaxed text-muted-foreground">
          收盤→收盤用於驗證週期方向；開盤→收盤較接近訊號公布後可執行的單日結果。
          目前價格尚未完整還原除權息，公司行動日請另外核對。
        </p>
      </CardContent>
    </Card>
  );
}

export default function PredictionsPage() {
  const predictions = useApi(() => api.predictions(10));
  const backtest = useApi(() => api.backtest());

  if (predictions.loading || backtest.loading) return <LoadingPanel />;
  if (predictions.error || backtest.error || !predictions.data || !backtest.data) {
    return <ErrorPanel message={predictions.error ?? backtest.error ?? "無資料"} />;
  }

  return (
    <div className="space-y-8 animate-fade-up">
      <div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <FlaskConical className="h-3.5 w-3.5" />
          收盤後產生 · 預測基準日 {predictions.data.as_of}
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">每日預測與回測驗證</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          technical_eod_v1 僅使用當日及過去的官方收盤 OHLCV，
          評估未來 1、3、5、10 個交易日，不使用未來資料。
        </p>
      </div>

      <Card className="border-gold/30 bg-gold/5">
        <CardContent className="flex items-start gap-3 pt-5">
          <Database className="mt-0.5 h-4 w-4 text-gold" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            此頁的預測與回測使用官方價格資料。主儀表板的籌碼、基本面與題材資料目前仍是
            mock，因此兩者必須分開解讀；回測結果不代表未來績效。
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>下一交易日觀察名單</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">股票</th>
                  <th className="px-3 py-2 text-right">收盤</th>
                  <th className="px-3 py-2 text-right">技術訊號</th>
                  <th className="px-3 py-2 text-right">方向</th>
                  <th className="px-3 py-2 text-right">信心度</th>
                </tr>
              </thead>
              <tbody>
                {predictions.data.items.map((item) => (
                  <tr key={item.stock_id} className="border-t border-border/50">
                    <td className="px-3 py-3 tnum text-muted-foreground">{item.rank}</td>
                    <td className="px-3 py-3">
                      <Link href={`/stocks/${item.stock_id}`} className="font-medium hover:text-primary">
                        {item.name}
                      </Link>
                      <span className="ml-2 tnum text-xs text-muted-foreground">{item.stock_id}</span>
                    </td>
                    <td className="px-3 py-3 text-right tnum">{fmtNumber(item.entry_close)}</td>
                    <td className={cn("px-3 py-3 text-right tnum font-semibold", scoreColor(item.signal_score))}>
                      {item.signal_score.toFixed(1)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <Badge variant={item.direction === "偏多" ? "bull" : item.direction === "偏空" ? "bear" : "outline"}>
                        {item.direction}
                      </Badge>
                    </td>
                    <td className="px-3 py-3 text-right tnum">{item.confidence.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <DailyScorecard />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" /> Walk-forward 回測
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 text-xs text-muted-foreground">
            期間 {backtest.data.prediction_start || "-"} 至 {backtest.data.prediction_end || "-"}；
            基準為股票池等權報酬。
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {backtest.data.horizons.map((item) => (
              <div key={item.horizon_days} className="rounded-lg border border-border/60 bg-background/40 p-4">
                <div className="text-xs text-muted-foreground">未來 {item.horizon_days} 個交易日</div>
                <div className={cn("mt-2 tnum text-2xl font-semibold", dirColor(item.top10_excess_return_pct))}>
                  {fmtPct(item.top10_excess_return_pct)}
                </div>
                <div className="text-xs text-muted-foreground">Top 10 超額報酬</div>
                <div className="mt-3 space-y-1 text-xs">
                  <div className="flex justify-between"><span>Top 10 平均</span><span className={dirColor(item.top10_average_return_pct)}>{fmtPct(item.top10_average_return_pct)}</span></div>
                  <div className="flex justify-between"><span>等權基準</span><span>{fmtPct(item.benchmark_return_pct)}</span></div>
                  <div className="flex justify-between"><span>勝率</span><span>{item.top10_win_rate_pct.toFixed(1)}%</span></div>
                  <div className="flex justify-between"><span>方向命中</span><span>{item.direction_accuracy_pct.toFixed(1)}%</span></div>
                  <div className="flex justify-between"><span>樣本</span><span>{item.evaluated_predictions}</span></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
