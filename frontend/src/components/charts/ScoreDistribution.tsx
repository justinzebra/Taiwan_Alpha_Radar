"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScoreBucket } from "@/lib/types";

const COLORS: Record<string, string> = {
  "80-100": "hsl(0 84% 62%)",
  "60-79": "hsl(41 88% 60%)",
  "40-59": "hsl(199 89% 56%)",
  "0-39": "hsl(152 62% 45%)",
};

export function ScoreDistribution({ data }: { data: ScoreBucket[] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
        <XAxis
          dataKey="label"
          tick={{ fill: "hsl(215 16% 60%)", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fill: "hsl(215 16% 60%)", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "hsl(222 20% 16% / 0.5)" }}
          contentStyle={{
            background: "hsl(222 28% 9%)",
            border: "1px solid hsl(222 20% 16%)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "hsl(210 20% 92%)" }}
          formatter={(v: number) => [`${v} 檔`, "數量"]}
        />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.label} fill={COLORS[d.label] ?? "hsl(199 89% 56%)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
