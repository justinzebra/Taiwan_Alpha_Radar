import type { DimensionDetail } from "@/lib/types";
import { cn, scoreColor } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

const ACCENT: Record<string, string> = {
  technical: "bg-primary",
  institutional: "bg-gold",
  fundamental: "bg-bear",
  thematic: "bg-accent",
  risk: "bg-bull",
};

export function DimensionCard({ d }: { d: DimensionDetail }) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/40 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-medium">{d.label}</span>
          <span className="rounded bg-muted/60 px-1.5 py-0.5 text-[10px] text-muted-foreground">
            權重 {(d.weight * 100).toFixed(0)}%
          </span>
        </div>
        <span className={cn("tnum text-xl font-semibold", scoreColor(d.score))}>
          {d.score.toFixed(0)}
        </span>
      </div>
      <Progress
        value={d.score}
        className="mt-2.5"
        indicatorClassName={ACCENT[d.key] ?? "bg-primary"}
      />
      <ul className="mt-3 space-y-1.5">
        {d.reasons.map((r, i) => (
          <li key={i} className="flex gap-2 text-xs text-muted-foreground">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />
            <span>{r}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
