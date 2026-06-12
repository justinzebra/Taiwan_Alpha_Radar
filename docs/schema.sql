-- Taiwan Alpha Radar — PostgreSQL schema (reference).
--
-- The application creates these tables automatically via SQLAlchemy
-- (Base.metadata.create_all) on startup. This file documents the canonical
-- schema and can be used to provision a database by hand or review the design.

-- =========================================================================
-- stocks — listed company master data
-- =========================================================================
CREATE TABLE IF NOT EXISTS stocks (
    stock_id            VARCHAR(10) PRIMARY KEY,
    name                VARCHAR(64) NOT NULL,
    name_en             VARCHAR(64) DEFAULT '',
    sector              VARCHAR(32),
    theme               VARCHAR(32),
    market              VARCHAR(8)  DEFAULT 'TWSE',
    market_cap_billion  DOUBLE PRECISION DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stocks_sector ON stocks (sector);
CREATE INDEX IF NOT EXISTS ix_stocks_theme  ON stocks (theme);

-- =========================================================================
-- daily_prices — OHLCV per stock per trading day
-- =========================================================================
CREATE TABLE IF NOT EXISTS daily_prices (
    id          BIGSERIAL PRIMARY KEY,
    stock_id    VARCHAR(10) NOT NULL REFERENCES stocks(stock_id) ON DELETE CASCADE,
    trade_date  DATE NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      BIGINT,
    change_pct  DOUBLE PRECISION DEFAULT 0,
    CONSTRAINT uq_price_stock_date UNIQUE (stock_id, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_prices_stock ON daily_prices (stock_id);
CREATE INDEX IF NOT EXISTS ix_prices_date  ON daily_prices (trade_date);

-- =========================================================================
-- stock_scores — composite Alpha Score + 5 dimensions per stock per date
-- =========================================================================
CREATE TABLE IF NOT EXISTS stock_scores (
    id                  BIGSERIAL PRIMARY KEY,
    stock_id            VARCHAR(10) NOT NULL REFERENCES stocks(stock_id) ON DELETE CASCADE,
    score_date          DATE NOT NULL,
    total_score         DOUBLE PRECISION NOT NULL,
    technical_score     DOUBLE PRECISION DEFAULT 0,
    institutional_score DOUBLE PRECISION DEFAULT 0,
    fundamental_score   DOUBLE PRECISION DEFAULT 0,
    thematic_score      DOUBLE PRECISION DEFAULT 0,
    risk_score          DOUBLE PRECISION DEFAULT 0,
    breakdown           JSONB DEFAULT '{}'::jsonb,   -- full per-dimension detail
    rank                INTEGER DEFAULT 0,
    recommendation      VARCHAR(16) DEFAULT '觀望',
    created_at          TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_score_stock_date UNIQUE (stock_id, score_date)
);
CREATE INDEX IF NOT EXISTS ix_scores_date  ON stock_scores (score_date);
CREATE INDEX IF NOT EXISTS ix_scores_total ON stock_scores (total_score);
CREATE INDEX IF NOT EXISTS ix_scores_rank  ON stock_scores (rank);

-- =========================================================================
-- sector_scores — per theme/sector strength per date (今日熱門族群)
-- =========================================================================
CREATE TABLE IF NOT EXISTS sector_scores (
    id                BIGSERIAL PRIMARY KEY,
    theme             VARCHAR(32) NOT NULL,
    score_date        DATE NOT NULL,
    strength_score    DOUBLE PRECISION NOT NULL,
    avg_change_pct    DOUBLE PRECISION DEFAULT 0,
    constituent_count INTEGER DEFAULT 0,
    rank              INTEGER DEFAULT 0,
    leaders           JSONB DEFAULT '[]'::jsonb,    -- top constituents
    created_at        TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_sector_theme_date UNIQUE (theme, score_date)
);
CREATE INDEX IF NOT EXISTS ix_sector_date ON sector_scores (score_date);
CREATE INDEX IF NOT EXISTS ix_sector_rank ON sector_scores (rank);

-- =========================================================================
-- market_scores — overall market temperature per date
-- =========================================================================
CREATE TABLE IF NOT EXISTS market_scores (
    id                   BIGSERIAL PRIMARY KEY,
    score_date           DATE NOT NULL UNIQUE,
    temperature_score    DOUBLE PRECISION NOT NULL,   -- 0-100
    sentiment_label      VARCHAR(16) NOT NULL,        -- 極度看空 ... 極度看多
    advancers            INTEGER DEFAULT 0,
    decliners            INTEGER DEFAULT 0,
    total_volume_billion DOUBLE PRECISION DEFAULT 0,
    risk_level           VARCHAR(16) DEFAULT '中',
    indices              JSONB DEFAULT '[]'::jsonb,    -- per-index snapshots
    notes                JSONB DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ DEFAULT now()
);

-- =========================================================================
-- ai_reports — LLM-generated investment summary per stock per date
-- =========================================================================
CREATE TABLE IF NOT EXISTS ai_reports (
    id           BIGSERIAL PRIMARY KEY,
    stock_id     VARCHAR(10) NOT NULL REFERENCES stocks(stock_id) ON DELETE CASCADE,
    report_date  DATE NOT NULL,
    provider     VARCHAR(16) DEFAULT 'mock',
    summary      TEXT DEFAULT '',
    sections     JSONB DEFAULT '{}'::jsonb,   -- highlights / risks / short_term / mid_term
    created_at   TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_report_stock_date UNIQUE (stock_id, report_date)
);
CREATE INDEX IF NOT EXISTS ix_reports_date ON ai_reports (report_date);
