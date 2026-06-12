"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, FlaskConical, Layers, LineChart, Radar } from "lucide-react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "儀表板", icon: Activity },
  { href: "/market", label: "大盤分析", icon: LineChart },
  { href: "/sectors", label: "熱門族群", icon: Layers },
  { href: "/stocks", label: "選股排行", icon: BarChart3 },
  { href: "/predictions", label: "預測驗證", icon: FlaskConical },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/70 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between gap-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/30">
            <Radar className="h-5 w-5 text-primary" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-sm font-semibold tracking-tight">
              Taiwan Alpha Radar
            </span>
            <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              每日選股決策平台
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
