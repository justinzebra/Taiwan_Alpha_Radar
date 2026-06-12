import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/layout/Nav";

export const metadata: Metadata = {
  title: "Taiwan Alpha Radar — 台股 AI 選股分析平台",
  description:
    "每日自動分析台股大盤、類股與個股，產生 Alpha Score 評分與 AI 投資報告的選股決策平台。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-Hant" className="dark">
      <body>
        <div className="app-backdrop" aria-hidden />
        <Nav />
        <main className="container py-8">{children}</main>
        <footer className="border-t border-border/60 py-6">
          <div className="container flex flex-col items-center justify-between gap-2 text-xs text-muted-foreground sm:flex-row">
            <span>Taiwan Alpha Radar · 每日選股決策平台 (MVP)</span>
            <span>
              本平台僅供研究分析，所有資料為模擬產生，不構成投資建議。
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
