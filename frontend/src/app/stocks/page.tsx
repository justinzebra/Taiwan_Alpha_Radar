"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ErrorPanel } from "@/components/common/States";
import { SkeletonRows } from "@/components/common/States";
import { LeaderboardTable } from "@/components/dashboard/LeaderboardTable";

const SORTS = [
  { key: "rank", label: "綜合排名" },
  { key: "score", label: "總分" },
  { key: "technical", label: "技術面" },
  { key: "institutional", label: "籌碼面" },
  { key: "fundamental", label: "基本面" },
];

const PAGE_SIZE = 15;

export default function StocksPage() {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("rank");
  const [page, setPage] = useState(1);

  const { data, loading, error } = useApi(
    () => api.stocks({ page, page_size: PAGE_SIZE, search: query, sort }),
    [page, query, sort],
  );

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-6 animate-fade-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">選股排行</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          依 Alpha Score 排序的每日選股清單 · 共 {data?.total ?? "-"} 檔
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setPage(1);
              setQuery(search);
            }}
            className="relative w-full sm:max-w-xs"
          >
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜尋股票名稱或代號…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </form>

          <div className="flex flex-wrap gap-1.5">
            {SORTS.map((s) => (
              <Button
                key={s.key}
                size="sm"
                variant={sort === s.key ? "default" : "outline"}
                onClick={() => {
                  setSort(s.key);
                  setPage(1);
                }}
              >
                {s.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5">
          {error ? (
            <ErrorPanel message={error} />
          ) : loading ? (
            <SkeletonRows rows={PAGE_SIZE} />
          ) : data && data.items.length > 0 ? (
            <LeaderboardTable items={data.items} />
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">
              查無符合條件的股票
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          第 {page} / {totalPages} 頁
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="h-4 w-4" /> 上一頁
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            下一頁 <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
