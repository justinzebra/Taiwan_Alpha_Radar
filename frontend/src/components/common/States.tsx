import { AlertTriangle, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";

export function LoadingPanel({ label = "載入分析資料中…" }: { label?: string }) {
  return (
    <Card className="flex items-center justify-center gap-3 p-12 text-muted-foreground">
      <Loader2 className="h-5 w-5 animate-spin text-primary" />
      <span className="text-sm">{label}</span>
    </Card>
  );
}

export function ErrorPanel({ message }: { message: string }) {
  return (
    <Card className="flex flex-col items-center justify-center gap-3 p-12 text-center">
      <AlertTriangle className="h-8 w-8 text-gold" />
      <p className="text-sm font-medium">無法載入資料</p>
      <p className="max-w-md text-xs text-muted-foreground">{message}</p>
      <p className="text-xs text-muted-foreground">
        後端可能仍在產生今日分析，請稍候重新整理。
      </p>
    </Card>
  );
}

export function SkeletonRows({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-10 w-full animate-pulse rounded-md bg-muted/40"
        />
      ))}
    </div>
  );
}
