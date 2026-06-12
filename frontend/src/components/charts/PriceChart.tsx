"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "@/lib/types";

export function PriceChart({ data }: { data: PricePoint[] }) {
  const points = data.map((p) => ({
    date: p.trade_date.slice(5), // MM-DD
    close: p.close,
  }));
  const up =
    data.length >= 2 && data[data.length - 1].close >= data[0].close;
  const stroke = up ? "hsl(0 84% 62%)" : "hsl(152 62% 45%)";

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={points} margin={{ top: 10, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity={0.35} />
            <stop offset="100%" stopColor={stroke} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fill: "hsl(215 16% 60%)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          minTickGap={28}
        />
        <YAxis
          domain={["auto", "auto"]}
          tick={{ fill: "hsl(215 16% 60%)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip
          contentStyle={{
            background: "hsl(222 28% 9%)",
            border: "1px solid hsl(222 20% 16%)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "hsl(210 20% 92%)" }}
          formatter={(v: number) => [v.toFixed(2), "收盤"]}
        />
        <Area
          type="monotone"
          dataKey="close"
          stroke={stroke}
          strokeWidth={2}
          fill="url(#priceFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
