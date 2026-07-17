-- Track non-LLM production artifacts (image generation, rendering, QA) separately
-- from api_cost_log so estimated provider charges and internal production effort
-- can be reconciled without falsifying token usage.
CREATE TABLE IF NOT EXISTS artifact_cost_log (
    id BIGSERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    units NUMERIC(14,4) NOT NULL DEFAULT 1,
    unit_name TEXT NOT NULL DEFAULT 'call',
    unit_price_usd NUMERIC(14,8),
    estimated_cost_usd NUMERIC(14,8) NOT NULL DEFAULT 0,
    actual_cost_usd NUMERIC(14,8),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_artifact_cost_log_job ON artifact_cost_log(job_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifact_cost_log_created ON artifact_cost_log(created_at DESC);
