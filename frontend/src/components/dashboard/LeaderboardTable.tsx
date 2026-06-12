import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { StockListItem } from "@/lib/types";
import { cn, dirColor, fmtNumber, fmtPct, scoreColor } from "@/lib/utils";
import { RecommendationBadge } from "@/components/common/ScoreBadge";

/** Compact ranking table reused by the dashboard and stocks page. */
export function LeaderboardTable({
  items,
  showRecommendation = true,
}: {
  items: StockListItem[];
  showRecommendation?: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wider text-muted-foreground">
            <th className="px-3 py-2 font-medium">#</th>
            <th className="px-3 py-2 font-medium">股票</th>
            <th className="px-3 py-2 font-medium">代號</th>
            <th className="px-3 py-2 text-right font-medium">收盤</th>
            <th className="px-3 py-2 text-right font-medium">漲跌幅</th>
            <th className="px-3 py-2 text-right font-medium">Score</th>
            {showRecommendation && (
              <th className="px-3 py-2 text-right font-medium">建議</th>
            )}
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {items.map((s) => (
            <tr
              key={s.stock_id}
              className="group border-t border-border/50 transition-colors hover:bg-muted/40"
            >
              <td className="px-3 py-2.5 tnum text-muted-foreground">{s.rank}</td>
              <td className="px-3 py-2.5">
                <Link
                  href={`/stocks/${s.stock_id}`}
                  className="font-medium hover:text-primary"
                >
                  {s.name}
                </Link>
                <span className="ml-2 text-xs text-muted-foreground">{s.theme}</span>
              </td>
              <td className="px-3 py-2.5 tnum text-muted-foreground">{s.stock_id}</td>
              <td className="px-3 py-2.5 text-right tnum">{fmtNumber(s.last_close)}</td>
              <td className={cn("px-3 py-2.5 text-right tnum", dirColor(s.change_pct))}>
                {fmtPct(s.change_pct)}
              </td>
              <td className={cn("px-3 py-2.5 text-right tnum font-semibold", scoreColor(s.total_score))}>
                {s.total_score.toFixed(1)}
              </td>
              {showRecommendation && (
                <td className="px-3 py-2.5 text-right">
                  <RecommendationBadge value={s.recommendation} />
                </td>
              )}
              <td className="px-3 py-2.5 text-right">
                <Link
                  href={`/stocks/${s.stock_id}`}
                  className="inline-flex text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                  aria-label={`查看 ${s.name} 個股分析`}
                >
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
