-- Harness Platform DB Schema
-- Apply: psql harness_prod < infra/schema.sql

CREATE TABLE IF NOT EXISTS raw_signals (
    id           SERIAL PRIMARY KEY,
    source       VARCHAR(100) NOT NULL,
    ingested_at  TIMESTAMP DEFAULT NOW(),
    raw_data     JSONB NOT NULL,
    content_hash VARCHAR(64) UNIQUE,
    status       VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS filtered_signals (
    id             SERIAL PRIMARY KEY,
    raw_signal_id  INTEGER REFERENCES raw_signals(id),
    source         VARCHAR(100),
    title          TEXT,
    summary        TEXT,
    score          DOUBLE PRECISION,
    category       VARCHAR(50),
    content_hash   VARCHAR(64) UNIQUE,
    tier2_model    VARCHAR(50),
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refined_outputs (
    id                  SERIAL PRIMARY KEY,
    filtered_signal_id  INTEGER REFERENCES filtered_signals(id),
    final_title         TEXT,
    final_body          TEXT,
    tags                JSONB,
    tier3_model         VARCHAR(50),
    published           BOOLEAN DEFAULT FALSE,
    published_at        TIMESTAMP,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_cost_log (
    id            SERIAL PRIMARY KEY,
    model         VARCHAR(50),
    input_tokens  INTEGER,
    output_tokens INTEGER,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id             SERIAL PRIMARY KEY,
    tier           INTEGER NOT NULL,
    item_id        INTEGER,
    item_type      VARCHAR(100),
    error_message  TEXT,
    raw_data       JSONB,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              SERIAL PRIMARY KEY,
    correlation_id  VARCHAR(8) NOT NULL,
    started_at      TIMESTAMP DEFAULT NOW(),
    finished_at     TIMESTAMP,
    tier1_count     INTEGER,
    tier2_count     INTEGER,
    tier3_count     INTEGER,
    tier4_count     INTEGER,
    status          VARCHAR(20) DEFAULT 'running',
    error           TEXT
);
