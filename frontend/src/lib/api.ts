import type {
  DashboardResponse,
  BacktestSummary,
  DailyPredictionResultResponse,
  MarketResponse,
  SectorListResponse,
  StockDetailResponse,
  StockListResponse,
  PredictionListResponse,
} from "./types";

// Browser-side base URL (the fetch runs in the user's browser, so it must point
// at the host-published backend port, not the internal docker hostname).
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    // Always fetch fresh analysis; the backend layer already caches via Redis.
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${detail || path}`);
  }
  return (await res.json()) as T;
}

export const api = {
  dashboard: () => getJSON<DashboardResponse>("/dashboard"),
  market: () => getJSON<MarketResponse>("/market"),
  sectors: () => getJSON<SectorListResponse>("/sectors"),
  stocks: (params: {
    page?: number;
    page_size?: number;
    search?: string;
    sort?: string;
    theme?: string;
  }) => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.page_size) q.set("page_size", String(params.page_size));
    if (params.search) q.set("search", params.search);
    if (params.sort) q.set("sort", params.sort);
    if (params.theme) q.set("theme", params.theme);
    return getJSON<StockListResponse>(`/stocks?${q.toString()}`);
  },
  stock: (id: string) => getJSON<StockDetailResponse>(`/stocks/${id}`),
  predictions: (limit = 10) =>
    getJSON<PredictionListResponse>(`/predictions?limit=${limit}`),
  predictionResults: (date?: string, limit = 10) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (date) q.set("date", date);
    return getJSON<DailyPredictionResultResponse>(
      `/prediction-results?${q.toString()}`,
    );
  },
  backtest: () => getJSON<BacktestSummary>("/backtest"),
  runPipeline: () =>
    getJSON<{ status: string }>("/admin/run-pipeline", { method: "POST" }),
};

export { API_BASE };
