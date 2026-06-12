import { Badge } from "@/components/ui/badge";

/** Map a recommendation string to a colored badge. */
export function RecommendationBadge({ value }: { value: string }) {
  const variant =
    value === "強力推薦" || value === "推薦"
      ? "bull"
      : value === "區間偏多"
        ? "gold"
        : value === "偏空"
          ? "bear"
          : "outline";
  return <Badge variant={variant as never}>{value}</Badge>;
}
