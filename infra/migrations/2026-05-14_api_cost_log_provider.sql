-- T-12: api_cost_log에 provider 컬럼 추가
-- providers: anthropic, google, openai, ollama, copilot

ALTER TABLE api_cost_log
    ADD COLUMN IF NOT EXISTS provider VARCHAR(20) DEFAULT 'anthropic';

CREATE INDEX IF NOT EXISTS idx_api_cost_log_provider
    ON api_cost_log(provider, created_at DESC);
