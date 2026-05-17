-- Goal Loop schema for Ralph-style closed-loop business execution
-- Status: draft migration

CREATE TABLE IF NOT EXISTS strategic_goals (
    id                      SERIAL PRIMARY KEY,
    title                   TEXT NOT NULL,
    objective               TEXT NOT NULL,
    goal_type               VARCHAR(50) DEFAULT 'growth',
    channel                 VARCHAR(50),
    target_metric           VARCHAR(100) NOT NULL,
    target_value            DOUBLE PRECISION NOT NULL,
    current_value           DOUBLE PRECISION DEFAULT 0.0,
    baseline_value          DOUBLE PRECISION DEFAULT 0.0,
    unit                    VARCHAR(30) DEFAULT 'count',
    deadline                TIMESTAMP NOT NULL,
    status                  VARCHAR(30) DEFAULT 'draft',
    urgency                 VARCHAR(30) DEFAULT 'medium',
    owner_team              VARCHAR(100) DEFAULT 'Business Operations Team',
    executive_escalation_required BOOLEAN DEFAULT FALSE,
    local_revision_count    INTEGER DEFAULT 0,
    success_definition      TEXT,
    failure_definition      TEXT,
    constraints_json        JSONB DEFAULT '{}'::jsonb,
    metadata                JSONB DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_strategy_reviews (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    review_round            INTEGER DEFAULT 1,
    review_type             VARCHAR(50) DEFAULT 'initial_strategy',
    hypothesis              TEXT NOT NULL,
    strategy_summary        TEXT NOT NULL,
    top_risks               JSONB DEFAULT '[]'::jsonb,
    anomaly_triggers        JSONB DEFAULT '[]'::jsonb,
    forecast_summary        TEXT,
    recommended_action      VARCHAR(50) DEFAULT 'proceed',
    red_team_required       BOOLEAN DEFAULT TRUE,
    executive_review_required BOOLEAN DEFAULT TRUE,
    created_by              VARCHAR(100) DEFAULT 'Chief of Staff',
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_action_items (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    strategy_review_id      INTEGER REFERENCES goal_strategy_reviews(id) ON DELETE SET NULL,
    team_name               VARCHAR(100) NOT NULL,
    owner_role              VARCHAR(100),
    action_type             VARCHAR(50) DEFAULT 'experiment',
    title                   TEXT NOT NULL,
    description             TEXT NOT NULL,
    success_metric          VARCHAR(100),
    target_delta            DOUBLE PRECISION,
    due_at                  TIMESTAMP,
    status                  VARCHAR(30) DEFAULT 'planned',
    priority                VARCHAR(30) DEFAULT 'medium',
    blocker                 TEXT,
    external_publish        BOOLEAN DEFAULT FALSE,
    requires_executive_approval BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_model_specs (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    version                 INTEGER DEFAULT 1,
    model_type              VARCHAR(50) NOT NULL,
    objective_metric        VARCHAR(100) NOT NULL,
    model_equation          TEXT NOT NULL,
    variable_definitions    JSONB DEFAULT '{}'::jsonb,
    parameter_estimates     JSONB DEFAULT '{}'::jsonb,
    sensitivity_rank        JSONB DEFAULT '[]'::jsonb,
    trigger_thresholds      JSONB DEFAULT '{}'::jsonb,
    scenario_assumptions    JSONB DEFAULT '{}'::jsonb,
    active                  BOOLEAN DEFAULT TRUE,
    created_by              VARCHAR(100) DEFAULT 'Business Operations Team',
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_progress_snapshots (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    model_spec_id           INTEGER REFERENCES goal_model_specs(id) ON DELETE SET NULL,
    snapshot_date           DATE DEFAULT CURRENT_DATE,
    actual_value            DOUBLE PRECISION DEFAULT 0.0,
    expected_value          DOUBLE PRECISION,
    forecast_probability    DOUBLE PRECISION,
    variance                DOUBLE PRECISION,
    health_status           VARCHAR(30) DEFAULT 'green',
    notes                   TEXT,
    source_metrics_json     JSONB DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_forecasts (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    model_spec_id           INTEGER REFERENCES goal_model_specs(id) ON DELETE SET NULL,
    forecast_date           DATE DEFAULT CURRENT_DATE,
    model_name              VARCHAR(100) DEFAULT 'Business Operations Team',
    expected_deadline_value DOUBLE PRECISION,
    probability_to_hit      DOUBLE PRECISION,
    confidence              DOUBLE PRECISION,
    narrative               TEXT,
    recommended_mode        VARCHAR(30) DEFAULT 'stay_course',
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_anomaly_events (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    model_spec_id           INTEGER REFERENCES goal_model_specs(id) ON DELETE SET NULL,
    snapshot_id             INTEGER REFERENCES goal_progress_snapshots(id) ON DELETE SET NULL,
    anomaly_type            VARCHAR(50) NOT NULL,
    severity                VARCHAR(30) DEFAULT 'medium',
    trigger_rule            TEXT NOT NULL,
    observed_value          TEXT,
    expected_value          TEXT,
    local_revision_recommended BOOLEAN DEFAULT TRUE,
    executive_escalation_required BOOLEAN DEFAULT FALSE,
    resolved                BOOLEAN DEFAULT FALSE,
    resolution_summary      TEXT,
    created_at              TIMESTAMP DEFAULT NOW(),
    resolved_at             TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goal_decision_cards (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    strategy_review_id      INTEGER REFERENCES goal_strategy_reviews(id) ON DELETE SET NULL,
    target_type             VARCHAR(50) DEFAULT 'strategic_goal',
    card_type               VARCHAR(50) DEFAULT 'goal_approval',
    summary                 TEXT NOT NULL,
    recommendation          TEXT,
    risks                   JSONB DEFAULT '[]'::jsonb,
    anomalies               JSONB DEFAULT '[]'::jsonb,
    payload_json            JSONB DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_metric_components (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    model_spec_id           INTEGER REFERENCES goal_model_specs(id) ON DELETE SET NULL,
    component_name          VARCHAR(100) NOT NULL,
    component_role          VARCHAR(50) DEFAULT 'driver',
    equation_term           TEXT,
    expected_value          DOUBLE PRECISION,
    actual_value            DOUBLE PRECISION,
    variance                DOUBLE PRECISION,
    unit                    VARCHAR(30),
    source_metric_key       VARCHAR(100),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_diagnostic_events (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    model_spec_id           INTEGER REFERENCES goal_model_specs(id) ON DELETE SET NULL,
    snapshot_id             INTEGER REFERENCES goal_progress_snapshots(id) ON DELETE SET NULL,
    primary_component_id    INTEGER REFERENCES goal_metric_components(id) ON DELETE SET NULL,
    diagnosis_type          VARCHAR(50) NOT NULL,
    root_cause_hypothesis   TEXT NOT NULL,
    evidence_json           JSONB DEFAULT '{}'::jsonb,
    confidence              DOUBLE PRECISION DEFAULT 0.0,
    executive_escalation_required BOOLEAN DEFAULT FALSE,
    created_by              VARCHAR(100) DEFAULT 'Business Operations Team',
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_feedback_signals (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    snapshot_id             INTEGER REFERENCES goal_progress_snapshots(id) ON DELETE SET NULL,
    source_type             VARCHAR(50) NOT NULL,
    source_ref              TEXT,
    signal_type             VARCHAR(50) NOT NULL,
    signal_text             TEXT NOT NULL,
    severity                VARCHAR(30) DEFAULT 'medium',
    structured_json         JSONB DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_revision_reasons (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    strategy_review_id      INTEGER REFERENCES goal_strategy_reviews(id) ON DELETE SET NULL,
    diagnostic_event_id     INTEGER REFERENCES goal_diagnostic_events(id) ON DELETE SET NULL,
    previous_model_spec_id  INTEGER REFERENCES goal_model_specs(id) ON DELETE SET NULL,
    new_model_spec_id       INTEGER REFERENCES goal_model_specs(id) ON DELETE SET NULL,
    revision_type           VARCHAR(50) NOT NULL,
    reason_summary          TEXT NOT NULL,
    action_change_summary   TEXT,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goal_review_artifacts (
    id                      SERIAL PRIMARY KEY,
    goal_id                 INTEGER REFERENCES strategic_goals(id) ON DELETE CASCADE,
    strategy_review_id      INTEGER REFERENCES goal_strategy_reviews(id) ON DELETE SET NULL,
    artifact_type           VARCHAR(50) NOT NULL,
    artifact_path           TEXT,
    provider_set            JSONB DEFAULT '[]'::jsonb,
    verdict                 VARCHAR(30),
    notes                   TEXT,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategic_goals_status
    ON strategic_goals(status, deadline);

CREATE INDEX IF NOT EXISTS idx_goal_action_items_goal
    ON goal_action_items(goal_id, status, due_at);

CREATE INDEX IF NOT EXISTS idx_goal_progress_snapshots_goal_date
    ON goal_progress_snapshots(goal_id, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_goal_forecasts_goal_date
    ON goal_forecasts(goal_id, forecast_date DESC);

CREATE INDEX IF NOT EXISTS idx_goal_model_specs_goal
    ON goal_model_specs(goal_id, active, version DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_goal_model_specs_active
    ON goal_model_specs(goal_id)
    WHERE active = TRUE;

CREATE INDEX IF NOT EXISTS idx_goal_metric_components_goal
    ON goal_metric_components(goal_id, model_spec_id, component_name);

CREATE INDEX IF NOT EXISTS idx_goal_diagnostic_events_goal
    ON goal_diagnostic_events(goal_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_goal_feedback_signals_goal
    ON goal_feedback_signals(goal_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_goal_revision_reasons_goal
    ON goal_revision_reasons(goal_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_goal_anomaly_events_goal
    ON goal_anomaly_events(goal_id, resolved, severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_goal_decision_cards_goal
    ON goal_decision_cards(goal_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_goal_review_artifacts_goal
    ON goal_review_artifacts(goal_id, created_at DESC);
