-- AlphaStream Intelligence Terminal - Database Schema
-- SQLite database for caching S&P 500 stock data

DROP TABLE IF EXISTS stocks;
DROP TABLE IF EXISTS market_indices;
DROP TABLE IF EXISTS macro_indicators;
DROP TABLE IF EXISTS treasury_history;
DROP TABLE IF EXISTS cpi_history;
DROP TABLE IF EXISTS vix_history;
DROP TABLE IF EXISTS refresh_log;
DROP TABLE IF EXISTS alternative_assets;

-- Main stocks table
CREATE TABLE stocks (
    -- Identifiers
    ticker TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    
    -- Price & Performance
    price REAL NOT NULL,
    change_1d REAL DEFAULT 0.0,
    change_1w REAL DEFAULT 0.0,
    change_1m REAL DEFAULT 0.0,
    change_1y REAL DEFAULT 0.0,
    change_5y REAL DEFAULT 0.0,
    change_ytd REAL DEFAULT 0.0,
    
    -- Volume
    volume INTEGER DEFAULT 0,
    
    -- High/Low ranges
    high_1d REAL,
    low_1d REAL,
    high_1m REAL,
    low_1m REAL,
    high_1y REAL,
    low_1y REAL,
    high_5y REAL,
    low_5y REAL,
    
    -- Valuation Metrics
    pe_ratio REAL,
    eps REAL,
    dividend_yield REAL DEFAULT 0.0,
    market_cap REAL,
    shares_outstanding REAL,
    
    -- Profitability Metrics (TTM)
    net_profit_margin REAL DEFAULT 0.0,
    gross_margin REAL DEFAULT 0.0,
    roe REAL DEFAULT 0.0,
    revenue_ttm REAL,
    
    -- Risk & Ownership
    beta REAL DEFAULT 1.0,
    institutional_ownership REAL DEFAULT 0.0,
    debt_to_equity REAL,
    
    -- Company Information
    year_founded INTEGER,
    website TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    weight REAL DEFAULT 0.0,
    
    -- Metadata
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_source TEXT DEFAULT 'sp500live',
    is_sp500 BOOLEAN DEFAULT 1
);

-- Indexes for performance
CREATE INDEX idx_sector ON stocks(sector);
CREATE INDEX idx_last_updated ON stocks(last_updated);
CREATE INDEX idx_market_cap ON stocks(market_cap DESC);
CREATE INDEX idx_change_1d ON stocks(change_1d DESC);

-- ============================================================================
-- Market indices (current)
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_indices (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    change REAL NOT NULL,
    change_pct REAL NOT NULL,
    last_updated TEXT NOT NULL
);

-- ============================================================================
-- Macro indicators (current)
-- ============================================================================
CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    change REAL,
    unit TEXT,
    last_updated TEXT NOT NULL
);

-- ============================================================================
-- Treasury history (365 days)
-- ============================================================================
CREATE TABLE IF NOT EXISTS treasury_history (
    date TEXT PRIMARY KEY,
    yield_10y REAL NOT NULL,
    yield_2y REAL,
    last_updated TEXT NOT NULL
);

-- ============================================================================
-- CPI history (12 months)
-- ============================================================================
CREATE TABLE IF NOT EXISTS cpi_history (
    date TEXT PRIMARY KEY,
    cpi_value REAL NOT NULL,
    mom_change REAL,
    yoy_change REAL,
    last_updated TEXT NOT NULL
);

-- ============================================================================
-- VIX history (365 days)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vix_history (
    date TEXT PRIMARY KEY,
    vix_close REAL NOT NULL,
    vix_high REAL,
    vix_low REAL,
    last_updated TEXT NOT NULL
);

-- Refresh log table
CREATE TABLE refresh_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    refresh_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stocks_updated INTEGER NOT NULL,
    data_source TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    duration_seconds REAL
);

CREATE INDEX idx_refresh_time ON refresh_log(refresh_time DESC);

-- ============================================================================
-- Alternative assets (crypto, commodities, currencies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS alternative_assets (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    value REAL,
    change REAL,
    change_percent REAL,
    last_updated TEXT NOT NULL,
    fetch_error TEXT
);

