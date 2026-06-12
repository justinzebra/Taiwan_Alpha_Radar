"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { cn, dirColor, fmtNumber, fmtPct, scoreColor } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorPanel, LoadingPanel } from "@/components/common/States";
import { RecommendationBadge } from "@/components/common/ScoreBadge";
import { PriceChart } from "@/components/charts/PriceChart";
import { DimensionRadar } from "@/components/charts/DimensionRadar";
import { DimensionCard } from "@/components/stock/DimensionCard";
import { AIReportCard } from "@/components/stock/AIReportCard";

export default function StockDetailPage({
  params,
}: {
  params: { stockId: string };
}) {
  const { stockId } = params;
  const { data, loading, error } = useApi(() => api.stock(stockId), [stockId]);

  if (loading) return <LoadingPanel />;
  if (error || !data) return <ErrorPanel message={error ?? "無資料"} />;

  return (
    <div className="space-y-6 animate-fade-up">
      <Link
        href="/stocks"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> 返回排行
      </Link>

      {/* Header */}
      <Card>
        <CardContent className="flex flex-col gap-6 p-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex flex-col">
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-semibold tracking-tight">{data.name}</h1>
                <span className="tnum text-lg text-muted-foreground">{data.stock_id}</span>
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <Badge variant="outline">{data.sector}</Badge>
                <Badge variant="default">{data.theme}</Badge>
                <span>{data.market}</span>
                <span>排名 #{data.rank}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="tnum text-2xl font-semibold">{fmtNumber(data.last_close)}</div>
              <div className={cn("tnum text-sm", dirColor(data.change_pct))}>
                {fmtPct(data.change_pct)}
              </div>
            </div>
            <div className="h-12 w-px bg-border" />
            <div className="text-right">
              <div className="text-xs text-muted-foreground">Alpha Score</div>
              <div className={cn("tnum text-4xl font-bold", scoreColor(data.total_score))}>
                {data.total_score.toFixed(0)}
              </div>
              <div className="mt-1">
                <RecommendationBadge value={data.recommendation} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Price + Radar */}
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>近 60 日股價走勢</CardTitle>
          </CardHeader>
          <CardContent>
            <PriceChart data={data.price_history} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>五力評分雷達</CardTitle>
          </CardHeader>
          <CardContent>
            <DimensionRadar dimensions={data.dimensions} />
          </CardContent>
        </Card>
      </div>

      {/* Dimension breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>評分維度拆解</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.dimensions.map((d) => (
            <DimensionCard key={d.key} d={d} />
          ))}
        </CardContent>
      </Card>

      {/* AI report */}
      {data.ai_report ? (
        <AIReportCard report={data.ai_report} />
      ) : (
        <Card>
          <CardContent className="p-6 text-center text-sm text-muted-foreground">
            此股票今日尚未產生 AI 投資摘要（僅前段排名個股會即時生成）。
          </CardContent>
        </Card>
      )}
    </div>
  );
}
