"use client";

import { RadialBar, RadialBarChart, PolarAngleAxis, ResponsiveContainer } from "recharts";

/**
 * Semicircular market-temperature gauge (0-100).
 * Color shifts from green (bearish) through blue to red (bullish) by score band.
 */
function gaugeColor(score: number): string {
  if (score >= 80) return "hsl(0 84% 62%)";
  if (score >= 60) return "hsl(20 85% 58%)";
  if (score >= 40) return "hsl(199 89% 56%)";
  if (score >= 20) return "hsl(152 50% 50%)";
  return "hsl(152 62% 45%)";
}

export function MarketGauge({
  score,
  sentiment,
}: {
  score: number;
  sentiment: string;
}) {
  const color = gaugeColor(score);
  const data = [{ name: "temp", value: score, fill: color }];

  return (
    <div className="relative mx-auto aspect-[2/1.15] w-full max-w-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          innerRadius="78%"
          outerRadius="100%"
          data={data}
          startAngle={210}
          endAngle={-30}
          barSize={18}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            background={{ fill: "hsl(222 20% 16%)" }}
            dataKey="value"
            cornerRadius={12}
            angleAxisId={0}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-x-0 bottom-2 flex flex-col items-center">
        <span
          className="tnum text-5xl font-semibold leading-none"
          style={{ color }}
        >
          {score.toFixed(0)}
        </span>
        <span className="mt-1 text-xs text-muted-foreground">市場溫度 / 100</span>
        <span
          className="mt-2 rounded-full px-3 py-1 text-sm font-medium"
          style={{ color, backgroundColor: `${color}22` }}
        >
          {sentiment}
        </span>
      </div>
    </div>
  );
}
