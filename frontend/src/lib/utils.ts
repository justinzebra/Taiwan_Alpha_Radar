import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a percentage with sign, e.g. +1.23%. */
export function fmtPct(value: number, digits = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

/** Tailwind text color class for a directional value (TW: red up / green down). */
export function dirColor(value: number): string {
  if (value > 0) return "text-bull";
  if (value < 0) return "text-bear";
  return "text-muted-foreground";
}

/** Color class for a 0-100 score. */
export function scoreColor(score: number): string {
  if (score >= 80) return "text-bull";
  if (score >= 65) return "text-gold";
  if (score >= 50) return "text-primary";
  return "text-muted-foreground";
}

export function fmtNumber(value: number, digits = 2): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
