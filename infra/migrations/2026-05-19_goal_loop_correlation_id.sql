-- Add correlation IDs to Ralph-loop goal tables for auditability.

ALTER TABLE strategic_goals
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

ALTER TABLE goal_model_specs
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

ALTER TABLE goal_progress_snapshots
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

ALTER TABLE goal_forecasts
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

ALTER TABLE goal_anomaly_events
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

ALTER TABLE goal_diagnostic_events
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

CREATE INDEX IF NOT EXISTS idx_strategic_goals_correlation_id
    ON strategic_goals(correlation_id);

CREATE INDEX IF NOT EXISTS idx_goal_progress_snapshots_correlation_id
    ON goal_progress_snapshots(correlation_id);

CREATE INDEX IF NOT EXISTS idx_goal_diagnostic_events_correlation_id
    ON goal_diagnostic_events(correlation_id);
