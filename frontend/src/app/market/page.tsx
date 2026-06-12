"use client";

import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { cn, dirColor, fmtNumber, fmtPct } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ErrorPanel, LoadingPanel } from "@/components/common/States";
import { MarketGauge } from "@/components/charts/MarketGauge";
import { StatTile } from "@/components/dashboard/StatTile";

export default function MarketPage() {
  const { data: market, loading, error } = useApi(() => api.market());

  if (loading) return <LoadingPanel />;
  if (error || !market) return <ErrorPanel message={error ?? "無資料"} />;

  const riskVariant =
    market.risk_level === "高" ? "bear" : market.risk_level === "低" ? "bull" : "gold";

  return (
    <div className="space-y-8 animate-fade-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">大盤分析</h1>
        <p className="mt-1 text-sm text-muted-foreground">分析基準日 {market.as_of}</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>市場溫度</CardTitle>
          </CardHeader>
          <CardContent>
            <MarketGauge score={market.temperature_score} sentiment={market.sentiment} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>市場研判</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed">{market.notes.comment}</p>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatTile label="上漲" value={market.advancers} valueClassName="text-bull" />
              <StatTile label="下跌" value={market.decliners} valueClassName="text-bear" />
              <StatTile
                label="市場風險"
                value={<Badge variant={riskVariant as never}>{market.risk_level}</Badge>}
              />
              <StatTile
                label="市場廣度"
                value={`${market.notes.breadth_pct ?? "-"}%`}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {market.indices.map((idx) => (
          <Card key={idx.index_id}>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>{idx.name}</CardTitle>
              <Badge variant={idx.trend === "上升" ? "bull" : "bear"}>{idx.trend}</Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-end justify-between">
                <span className="tnum text-3xl font-semibold">{fmtNumber(idx.value)}</span>
                <span className={cn("tnum text-lg", dirColor(idx.change_pct))}>
                  {fmtPct(idx.change_pct)}
                </span>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                  <span>趨勢強度</span>
                  <span className="tnum">{idx.strength.toFixed(0)} / 100</span>
                </div>
                <Progress value={idx.strength} />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>成交量</span>
                <span className="tnum">{fmtNumber(idx.volume_billion, 1)} 億</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
