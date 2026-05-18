-- M-3: correlation_id 전파 — strategic_goals, goal_model_specs, goal_progress_snapshots
-- CLAUDE.md: "모든 action에 correlation_id를 포함한다"

ALTER TABLE strategic_goals
    ADD COLUMN IF NOT EXISTS correlation_id UUID DEFAULT gen_random_uuid();

ALTER TABLE goal_model_specs
    ADD COLUMN IF NOT EXISTS correlation_id UUID DEFAULT gen_random_uuid();

ALTER TABLE goal_progress_snapshots
    ADD COLUMN IF NOT EXISTS correlation_id UUID DEFAULT gen_random_uuid();

CREATE INDEX IF NOT EXISTS idx_strategic_goals_correlation_id ON strategic_goals (correlation_id);
CREATE INDEX IF NOT EXISTS idx_goal_model_specs_correlation_id ON goal_model_specs (correlation_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_snapshots_correlation_id ON goal_progress_snapshots (correlation_id);
