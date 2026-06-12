import type { SectorItem } from "@/lib/types";
import { cn, dirColor, fmtPct } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

const MEDALS = ["🥇", "🥈", "🥉"];

export function HotSectors({ sectors }: { sectors: SectorItem[] }) {
  return (
    <div className="space-y-3">
      {sectors.map((s, i) => (
        <div key={s.theme} className="rounded-lg border border-border/50 bg-background/40 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-5 text-center text-sm">{MEDALS[i] ?? `${i + 1}`}</span>
              <span className="font-medium">{s.theme}</span>
              <span className="text-xs text-muted-foreground">
                {s.constituent_count} 檔
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className={cn("tnum text-xs", dirColor(s.avg_change_pct))}>
                {fmtPct(s.avg_change_pct)}
              </span>
              <span className="tnum text-sm font-semibold text-primary">
                {s.strength_score.toFixed(0)}
              </span>
            </div>
          </div>
          <Progress value={s.strength_score} className="mt-2" />
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {s.leaders.map((l) => (
              <span key={l.stock_id}>
                {l.name}
                <span className={cn("ml-1 tnum", dirColor(l.change_pct))}>
                  {fmtPct(l.change_pct)}
                </span>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
