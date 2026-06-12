"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { cn, dirColor, fmtPct } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ErrorPanel, LoadingPanel } from "@/components/common/States";

export default function SectorsPage() {
  const { data, loading, error } = useApi(() => api.sectors());

  if (loading) return <LoadingPanel />;
  if (error || !data) return <ErrorPanel message={error ?? "無資料"} />;

  return (
    <div className="space-y-6 animate-fade-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">熱門族群分析</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          依族群強度排序 · 分析基準日 {data.as_of}
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {data.sectors.map((s) => (
          <Card key={s.theme}>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base text-foreground">
                <span className="tnum text-muted-foreground">#{s.rank}</span>
                {s.theme}
                <Badge variant="outline">{s.constituent_count} 檔</Badge>
              </CardTitle>
              <div className="text-right">
                <div className="tnum text-2xl font-semibold text-primary">
                  {s.strength_score.toFixed(0)}
                </div>
                <div className={cn("tnum text-xs", dirColor(s.avg_change_pct))}>
                  {fmtPct(s.avg_change_pct)}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <Progress value={s.strength_score} />
              <div className="space-y-1.5">
                {s.leaders.map((l) => (
                  <Link
                    key={l.stock_id}
                    href={`/stocks/${l.stock_id}`}
                    className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted/50"
                  >
                    <span>
                      {l.name}
                      <span className="ml-2 text-xs text-muted-foreground">
                        {l.stock_id}
                      </span>
                    </span>
                    <span className="flex items-center gap-3">
                      <span className={cn("tnum text-xs", dirColor(l.change_pct))}>
                        {fmtPct(l.change_pct)}
                      </span>
                      <span className="tnum font-medium text-primary">
                        {l.total_score.toFixed(0)}
                      </span>
                    </span>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
