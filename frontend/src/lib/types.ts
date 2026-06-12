// Response types mirroring the FastAPI backend schemas.

export interface IndexItem {
  index_id: string;
  name: string;
  value: number;
  change_pct: number;
  trend: string;
  strength: number;
  volume_billion: number;
}

export interface MarketResponse {
  as_of: string;
  temperature_score: number;
  sentiment: string;
  risk_level: string;
  advancers: number;
  decliners: number;
  total_volume_billion: number;
  indices: IndexItem[];
  notes: {
    breadth_pct?: number;
    avg_alpha?: number;
    index_strength?: number;
    comment?: string;
  };
}

export interface SectorLeader {
  stock_id: string;
  name: string;
  change_pct: number;
  total_score: number;
}

export interface SectorItem {
  theme: string;
  rank: number;
  strength_score: number;
  avg_change_pct: number;
  constituent_count: number;
  leaders: SectorLeader[];
}

export interface SectorListResponse {
  as_of: string;
  sectors: SectorItem[];
}

export interface StockListItem {
  rank: number;
  stock_id: string;
  name: string;
  sector: string;
  theme: string;
  total_score: number;
  change_pct: number;
  last_close: number;
  recommendation: string;
}

export interface StockListResponse {
  as_of: string;
  total: number;
  page: number;
  page_size: number;
  items: StockListItem[];
}

export interface ScoreBucket {
  label: string;
  count: number;
}

export interface DashboardResponse {
  as_of: string;
  market: MarketResponse;
  top_stocks: StockListItem[];
  hot_sectors: SectorItem[];
  score_distribution: ScoreBucket[];
  data_status: {
    price_source: string;
    other_sources: string;
    prediction_methodology: string;
    price_data_is_real: boolean;
    full_alpha_is_real: boolean;
  };
}

export interface PredictionItem {
  rank: number;
  stock_id: string;
  name: string;
  signal_score: number;
  direction: string;
  confidence: number;
  entry_close: number;
}

export interface PredictionListResponse {
  as_of: string;
  methodology: string;
  data_source: string;
  items: PredictionItem[];
}

export interface BacktestHorizon {
  horizon_days: number;
  evaluated_predictions: number;
  top10_average_return_pct: number;
  benchmark_return_pct: number;
  top10_excess_return_pct: number;
  top10_win_rate_pct: number;
  direction_accuracy_pct: number;
}

export interface BacktestSummary {
  methodology: string;
  data_source: string;
  prediction_start: string;
  prediction_end: string;
  horizons: BacktestHorizon[];
}

export interface DimensionDetail {
  key: string;
  label: string;
  score: number;
  weight: number;
  weighted: number;
  reasons: string[];
  metrics: Record<string, unknown>;
}

export interface AIReportDetail {
  provider: string;
  summary: string;
  highlights: string[];
  risks: string[];
  short_term: string;
  mid_term: string;
}

export interface PricePoint {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change_pct: number;
}

export interface StockDetailResponse {
  as_of: string;
  stock_id: string;
  name: string;
  name_en: string;
  sector: string;
  theme: string;
  market: string;
  total_score: number;
  rank: number;
  recommendation: string;
  last_close: number;
  change_pct: number;
  dimensions: DimensionDetail[];
  ai_report: AIReportDetail | null;
  price_history: PricePoint[];
}
