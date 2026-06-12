"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import type { DimensionDetail } from "@/lib/types";

export function DimensionRadar({ dimensions }: { dimensions: DimensionDetail[] }) {
  const data = dimensions.map((d) => ({ label: d.label, score: d.score }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="hsl(222 20% 20%)" />
        <PolarAngleAxis
          dataKey="label"
          tick={{ fill: "hsl(215 16% 65%)", fontSize: 12 }}
        />
        <Radar
          dataKey="score"
          stroke="hsl(199 89% 56%)"
          fill="hsl(199 89% 56%)"
          fillOpacity={0.4}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
