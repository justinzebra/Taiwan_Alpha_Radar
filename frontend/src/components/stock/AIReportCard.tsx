import { AlertTriangle, Eye, Sparkles, TrendingUp } from "lucide-react";
import type { AIReportDetail } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function AIReportCard({ report }: { report: AIReportDetail }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-foreground">
          <Sparkles className="h-4 w-4 text-primary" /> AI 投資摘要
        </CardTitle>
        <Badge variant="outline">由 {report.provider} 生成</Badge>
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm leading-relaxed">
          {report.summary}
        </p>

        <div className="grid gap-5 sm:grid-cols-2">
          <Section
            icon={<TrendingUp className="h-4 w-4 text-bull" />}
            title="投資亮點"
            items={report.highlights}
          />
          <Section
            icon={<AlertTriangle className="h-4 w-4 text-gold" />}
            title="風險提醒"
            items={report.risks}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Observation icon={<Eye className="h-4 w-4 text-primary" />} label="短期觀察" text={report.short_term} />
          <Observation icon={<Eye className="h-4 w-4 text-accent" />} label="中期觀察" text={report.mid_term} />
        </div>
      </CardContent>
    </Card>
  );
}

function Section({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        {icon} {title}
      </div>
      <ul className="space-y-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex gap-2 text-sm text-muted-foreground">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Observation({
  icon,
  label,
  text,
}: {
  icon: React.ReactNode;
  label: string;
  text: string;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/40 p-3">
      <div className="mb-1 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        {icon} {label}
      </div>
      <p className="text-sm leading-relaxed">{text}</p>
    </div>
  );
}
