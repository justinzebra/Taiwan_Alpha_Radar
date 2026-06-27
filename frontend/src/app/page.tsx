"use client";

import { useState } from "react";
import { Activity, Database, Flame, Gauge, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { cn, dirColor, fmtNumber, fmtPct } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SectionTitle } from "@/components/common/SectionTitle";
import { ErrorPanel, LoadingPanel } from "@/components/common/States";
import { MarketGauge } from "@/components/charts/MarketGauge";
import { ScoreDistribution } from "@/components/charts/ScoreDistribution";
import { StatTile } from "@/components/dashboard/StatTile";
import { LeaderboardTable } from "@/components/dashboard/LeaderboardTable";
import { HotSectors } from "@/components/dashboard/HotSectors";

export default function DashboardPage() {
  const { data, loading, error, reload } = useApi(() => api.dashboard());
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  async function handleManualRefresh() {
    setRefreshing(true);
    setRefreshMessage(null);
    try {
      const result = await api.runPipeline();
      const asOf = result.summary?.as_of ? `，最新交易日 ${result.summary.as_of}` : "";
      const preview =
        result.preview?.status === "ok"
          ? `；${result.preview.message}（${result.preview.quote_count} 檔）`
          : result.preview?.message
            ? `；${result.preview.message}`
            : "";
      setRefreshMessage(`刷新完成${asOf}${preview}`);
      reload();
    } catch (err) {
      setRefreshMessage(
        err instanceof Error ? `刷新失敗：${err.message}` : "刷新失敗",
      );
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) return <LoadingPanel />;
  if (error || !data) return <ErrorPanel message={error ?? "無資料"} />;

  const { market, top_stocks, hot_sectors, score_distribution } = data;
  const riskVariant =
    market.risk_level === "高" ? "bear" : market.risk_level === "低" ? "bull" : "gold";

  return (
    <div className="space-y-8 animate-fade-up">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-bear" />
          每日選股決策 · 分析基準日 {data.as_of}
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">市場儀表板</h1>
      </div>

      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-col gap-4 pt-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <Database className="mt-0.5 h-4 w-4 text-primary" />
            <div>
              <div className="text-sm font-medium">
                價格資料：
                {data.data_status.price_data_is_real ? "TWSE／TPEx 官方盤後資料" : "模擬資料"}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                技術預測使用收盤 OHLCV，v3 使用盤後三大法人資料；財報與新聞目前仍為 mock，
                完整 Alpha Score 尚不可視為全真實資料模型。
              </p>
              {refreshMessage ? (
                <p
                  className={cn(
                    "mt-2 text-xs",
                    refreshMessage.startsWith("刷新失敗") ? "text-bear" : "text-bull",
                  )}
                >
                  {refreshMessage}
                </p>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <Button
              type="button"
              size="sm"
              onClick={handleManualRefresh}
              disabled={refreshing}
              aria-label="手動刷新收盤資料與勝率"
            >
              <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
              {refreshing ? "刷新中" : "手動刷新"}
            </Button>
            <a href="/predictions" className="text-xs text-primary hover:underline">
              查看每日預測與回測 →
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Top row: gauge + key stats */}
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-4 w-4" /> 市場溫度
            </CardTitle>
          </CardHeader>
          <CardContent>
            <MarketGauge score={market.temperature_score} sentiment={market.sentiment} />
            <p className="mt-3 text-center text-xs leading-relaxed text-muted-foreground">
              {market.notes.comment}
            </p>
          </CardContent>
        </Card>

        <div className="grid grid-cols-2 gap-5 lg:col-span-2">
          <StatTile
            label="上漲家數"
            value={market.advancers}
            valueClassName="text-bull"
            hint="今日收紅檔數"
            icon={<TrendingUp className="h-4 w-4 text-bull" />}
          />
          <StatTile
            label="下跌家數"
            value={market.decliners}
            valueClassName="text-bear"
            hint="今日收綠檔數"
            icon={<TrendingDown className="h-4 w-4 text-bear" />}
          />
          <StatTile
            label="市場風險"
            value={<Badge variant={riskVariant as never}>{market.risk_level}</Badge>}
            hint={`市場廣度 ${market.notes.breadth_pct ?? "-"}%`}
            icon={<Activity className="h-4 w-4 text-muted-foreground" />}
          />
          <StatTile
            label="平均 Alpha Score"
            value={(market.notes.avg_alpha ?? 0).toFixed(1)}
            hint="全市場個股平均評分"
            icon={<Flame className="h-4 w-4 text-gold" />}
          />
          {market.indices.map((idx) => (
            <StatTile
              key={idx.index_id}
              label={idx.name}
              value={fmtNumber(idx.value)}
              valueClassName={dirColor(idx.change_pct)}
              hint={
                <span className={cn("tnum", dirColor(idx.change_pct))}>
                  {fmtPct(idx.change_pct)} · {idx.trend} · 強度 {idx.strength.toFixed(0)}
                </span>
              }
            />
          ))}
        </div>
      </div>

      {/* Middle row: leaderboard + sectors */}
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Top 10 選股排行</CardTitle>
            <a href="/stocks" className="text-xs text-primary hover:underline">
              查看完整排行 →
            </a>
          </CardHeader>
          <CardContent>
            <LeaderboardTable items={top_stocks} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-gold" /> 今日熱門族群
            </CardTitle>
            <a href="/sectors" className="text-xs text-primary hover:underline">
              更多 →
            </a>
          </CardHeader>
          <CardContent>
            <HotSectors sectors={hot_sectors} />
          </CardContent>
        </Card>
      </div>

      {/* Bottom row: score distribution */}
      <div>
        <SectionTitle
          title="個股評分分布"
          subtitle="全市場 Alpha Score 分布，快速掌握強弱結構"
        />
        <Card>
          <CardContent className="pt-5">
            <ScoreDistribution data={score_distribution} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
