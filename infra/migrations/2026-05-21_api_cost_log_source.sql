-- Add source column to api_cost_log to separate pipeline vs openclaw budgets
ALTER TABLE api_cost_log ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'pipeline';
