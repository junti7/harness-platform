-- Harness Platform DB Schema
-- Apply: psql harness_prod < infra/schema.sql

CREATE TABLE IF NOT EXISTS raw_signals (
    id           SERIAL PRIMARY KEY,
    source       VARCHAR(100) NOT NULL,
    ingested_at  TIMESTAMP DEFAULT NOW(),
    raw_data     JSONB NOT NULL,
    content_hash VARCHAR(64) UNIQUE,
    status       VARCHAR(20) DEFAULT 'pending',
    domain       VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_raw_signals_domain_status ON raw_signals(domain, status);

CREATE TABLE IF NOT EXISTS source_catalog (
    id                   SERIAL PRIMARY KEY,
    source_name          VARCHAR(100) UNIQUE NOT NULL,
    source_type          VARCHAR(50) NOT NULL,
    base_url             TEXT,
    reliability_score    DOUBLE PRECISION DEFAULT 0.5,
    expected_signal_type VARCHAR(50),
    collection_cost      VARCHAR(20) DEFAULT 'free',
    rate_limit_policy    JSONB DEFAULT '{}'::jsonb,
    enabled              BOOLEAN DEFAULT TRUE,
    failure_count        INTEGER DEFAULT 0,
    cooldown_until       TIMESTAMP,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
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
    created_at     TIMESTAMP DEFAULT NOW(),
    domain         VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_filtered_signals_domain_created_at ON filtered_signals(domain, created_at);

CREATE TABLE IF NOT EXISTS signals (
    id                         SERIAL PRIMARY KEY,
    raw_signal_id              INTEGER REFERENCES raw_signals(id),
    filtered_signal_id         INTEGER REFERENCES filtered_signals(id),
    source                     VARCHAR(100),
    signal_type                VARCHAR(50),
    signal_summary             TEXT NOT NULL,
    why_now                    TEXT,
    source_url                 TEXT,
    content_hash               VARCHAR(64) UNIQUE,
    novelty_score              DOUBLE PRECISION DEFAULT 0.0,
    relevance_score            DOUBLE PRECISION DEFAULT 0.0,
    source_confidence          DOUBLE PRECISION DEFAULT 0.0,
    monetization_potential     DOUBLE PRECISION DEFAULT 0.0,
    preliminary_score          DOUBLE PRECISION DEFAULT 0.0,
    status                     VARCHAR(30) DEFAULT 'candidate',
    created_at                 TIMESTAMP DEFAULT NOW(),
    updated_at                 TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entities (
    id             SERIAL PRIMARY KEY,
    entity_type    VARCHAR(50) NOT NULL,
    name           TEXT NOT NULL,
    canonical_name TEXT,
    metadata       JSONB DEFAULT '{}'::jsonb,
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (entity_type, name)
);

CREATE TABLE IF NOT EXISTS signal_entities (
    id          SERIAL PRIMARY KEY,
    signal_id   INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    entity_id   INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    relation    VARCHAR(50),
    confidence  DOUBLE PRECISION DEFAULT 0.0,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (signal_id, entity_id, relation)
);

CREATE TABLE IF NOT EXISTS refined_outputs (
    id                  SERIAL PRIMARY KEY,
    filtered_signal_id  INTEGER REFERENCES filtered_signals(id),
    final_title         TEXT,
    final_body          TEXT,
    tags                JSONB,
    tier3_model         VARCHAR(50),
    sensitivity_level   VARCHAR(20) DEFAULT 'low',
    requires_ceo_approval BOOLEAN DEFAULT FALSE,
    published           BOOLEAN DEFAULT FALSE,
    notion_page_id      TEXT,
    published_at        TIMESTAMP,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- 정제 backlog KPI(/api/pipeline/backlog) 의 LEFT JOIN/created_at FILTER 집계 가속.
CREATE INDEX IF NOT EXISTS idx_refined_outputs_filtered_signal_id
    ON refined_outputs(filtered_signal_id);
CREATE INDEX IF NOT EXISTS idx_refined_outputs_created_at
    ON refined_outputs(created_at DESC);

CREATE TABLE IF NOT EXISTS agent_reviews (
    id                   SERIAL PRIMARY KEY,
    signal_id            INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    refined_output_id    INTEGER REFERENCES refined_outputs(id) ON DELETE CASCADE,
    agent_name           VARCHAR(100) NOT NULL,
    agent_role           VARCHAR(100),
    model                VARCHAR(100),
    review_type          VARCHAR(50) NOT NULL,
    score                DOUBLE PRECISION,
    confidence           DOUBLE PRECISION,
    reasoning            TEXT,
    risks                JSONB DEFAULT '[]'::jsonb,
    recommendations      JSONB DEFAULT '[]'::jsonb,
    raw_output           JSONB DEFAULT '{}'::jsonb,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ceo_decisions (
    id             SERIAL PRIMARY KEY,
    target_type    VARCHAR(50) NOT NULL,
    target_id      INTEGER NOT NULL,
    decision       VARCHAR(30) NOT NULL,
    approval_type  VARCHAR(50),
    reason         TEXT,
    decided_by     VARCHAR(100) DEFAULT 'CEO',
    created_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (target_type, target_id, decision)
);

CREATE TABLE IF NOT EXISTS partner_feedback (
    id                         SERIAL PRIMARY KEY,
    partner_name               VARCHAR(100) DEFAULT 'Vice President',
    target_type                VARCHAR(50) NOT NULL,
    target_id                  INTEGER NOT NULL,
    market_read                VARCHAR(50) NOT NULL,
    trust_temperature          VARCHAR(30),
    relationship_leverage      VARCHAR(30),
    timing_read                VARCHAR(30),
    emotional_resonance        VARCHAR(30),
    buyer_hesitation           TEXT,
    analog_notes               TEXT,
    requested_action           VARCHAR(50),
    human_review_required      BOOLEAN DEFAULT FALSE,
    created_at                 TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS research_reports (
    id               SERIAL PRIMARY KEY,
    title            TEXT NOT NULL,
    report_type      VARCHAR(50) DEFAULT 'daily_brief',
    audience         VARCHAR(50) DEFAULT 'internal',
    body             TEXT,
    summary          TEXT,
    sensitivity_level VARCHAR(20) DEFAULT 'medium',
    requires_ceo_approval BOOLEAN DEFAULT FALSE,
    status           VARCHAR(30) DEFAULT 'draft',
    source_signal_ids JSONB DEFAULT '[]'::jsonb,
    cost_usd         DOUBLE PRECISION DEFAULT 0.0,
    published        BOOLEAN DEFAULT FALSE,
    notion_page_id   TEXT,
    published_at     TIMESTAMP,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS newsletter_issues (
    id                         SERIAL PRIMARY KEY,
    issue_date                 DATE,
    title                      TEXT NOT NULL,
    status                     VARCHAR(30) DEFAULT 'draft',
    free_body                  TEXT,
    paid_body                  TEXT,
    source_signal_ids          JSONB DEFAULT '[]'::jsonb,
    publishing_platform        VARCHAR(50),
    public_url                 TEXT,
    notion_page_id             TEXT,
    requires_president_approval BOOLEAN DEFAULT TRUE,
    published_at               TIMESTAMP,
    created_at                 TIMESTAMP DEFAULT NOW(),
    updated_at                 TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS content_reviews (
    id                  SERIAL PRIMARY KEY,
    newsletter_issue_id INTEGER REFERENCES newsletter_issues(id) ON DELETE CASCADE,
    reviewer_role       VARCHAR(100) DEFAULT 'Vice President',
    readability         VARCHAR(30),
    shareability        VARCHAR(30),
    jargon_notes        TEXT,
    paid_hesitation     TEXT,
    suggested_title     TEXT,
    recommendation      VARCHAR(30) DEFAULT 'revise',
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriber_snapshots (
    id                    SERIAL PRIMARY KEY,
    snapshot_date          DATE DEFAULT CURRENT_DATE,
    platform               VARCHAR(50),
    free_subscribers       INTEGER DEFAULT 0,
    paid_subscribers       INTEGER DEFAULT 0,
    paid_revenue_krw       INTEGER DEFAULT 0,
    opens                  INTEGER DEFAULT 0,
    clicks                 INTEGER DEFAULT 0,
    replies                INTEGER DEFAULT 0,
    shares                 INTEGER DEFAULT 0,
    unsubscribe_count      INTEGER DEFAULT 0,
    notes                  TEXT,
    created_at             TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_profiles (
    id                         SERIAL PRIMARY KEY,
    external_ref               TEXT UNIQUE,
    email_hash                 VARCHAR(64),
    tier                       VARCHAR(50) DEFAULT 'free',
    persona_type               VARCHAR(50) DEFAULT 'general',
    country                    VARCHAR(50),
    timezone                   VARCHAR(50),
    preferred_language         VARCHAR(10) DEFAULT 'ko',
    knowledge_level            VARCHAR(30) DEFAULT 'beginner',
    preferred_depth            VARCHAR(30) DEFAULT 'plain',
    consent_marketing          BOOLEAN DEFAULT FALSE,
    consent_personalization    BOOLEAN DEFAULT FALSE,
    created_at                 TIMESTAMP DEFAULT NOW(),
    updated_at                 TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_memory_events (
    id                   SERIAL PRIMARY KEY,
    customer_id          INTEGER REFERENCES customer_profiles(id) ON DELETE CASCADE,
    event_type           VARCHAR(50) NOT NULL,
    event_key            TEXT,
    event_value          JSONB DEFAULT '{}'::jsonb,
    source_channel       VARCHAR(50),
    source_artifact_type VARCHAR(50),
    source_artifact_id   INTEGER,
    confidence           DOUBLE PRECISION DEFAULT 0.0,
    sensitivity_level    VARCHAR(20) DEFAULT 'low',
    expires_at           TIMESTAMP,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_interest_tags (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customer_profiles(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL,
    weight      DOUBLE PRECISION DEFAULT 1.0,
    source      VARCHAR(50),
    updated_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (customer_id, tag)
);

CREATE TABLE IF NOT EXISTS customer_preference_overrides (
    id               SERIAL PRIMARY KEY,
    customer_id      INTEGER REFERENCES customer_profiles(id) ON DELETE CASCADE,
    preference_key   TEXT NOT NULL,
    preference_value JSONB DEFAULT '{}'::jsonb,
    scope            VARCHAR(30) DEFAULT 'brief',
    source           VARCHAR(50),
    confidence       DOUBLE PRECISION DEFAULT 0.0,
    priority         VARCHAR(30) DEFAULT 'medium',
    effective_from   TIMESTAMP DEFAULT NOW(),
    expires_at       TIMESTAMP,
    active           BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_watchlists (
    id             SERIAL PRIMARY KEY,
    customer_id    INTEGER REFERENCES customer_profiles(id) ON DELETE CASCADE,
    entity_type    VARCHAR(50) NOT NULL,
    entity_key     TEXT NOT NULL,
    priority       VARCHAR(30) DEFAULT 'medium',
    reason         TEXT,
    active         BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (customer_id, entity_type, entity_key)
);

CREATE TABLE IF NOT EXISTS customer_questions (
    id                     SERIAL PRIMARY KEY,
    customer_id            INTEGER REFERENCES customer_profiles(id) ON DELETE CASCADE,
    question               TEXT NOT NULL,
    status                 VARCHAR(30) DEFAULT 'open',
    priority               VARCHAR(30) DEFAULT 'medium',
    topic_tags             JSONB DEFAULT '[]'::jsonb,
    last_answered_issue_id INTEGER REFERENCES newsletter_issues(id),
    last_answered_artifact_type VARCHAR(50),
    last_answered_artifact_id   INTEGER,
    sensitivity_level      VARCHAR(20) DEFAULT 'low',
    due_at                 TIMESTAMP,
    created_at             TIMESTAMP DEFAULT NOW(),
    updated_at             TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_upgrade_events (
    id                   SERIAL PRIMARY KEY,
    product_name         TEXT NOT NULL,
    artifact_type        VARCHAR(50),
    artifact_id          INTEGER,
    source_event_ids     JSONB DEFAULT '[]'::jsonb,
    source_feedback_ids  JSONB DEFAULT '[]'::jsonb,
    upgrade_type         VARCHAR(50) NOT NULL,
    description          TEXT NOT NULL,
    applied_to_products  JSONB DEFAULT '[]'::jsonb,
    created_by           VARCHAR(100) DEFAULT 'Product Planning Agent',
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS artifact_memory_usage (
    id                   SERIAL PRIMARY KEY,
    artifact_type        VARCHAR(50) NOT NULL,
    artifact_id          INTEGER NOT NULL,
    customer_id          INTEGER REFERENCES customer_profiles(id) ON DELETE SET NULL,
    audience_scope       VARCHAR(30) DEFAULT 'segment',
    audience_key         TEXT,
    memory_event_ids     JSONB DEFAULT '[]'::jsonb,
    override_ids         JSONB DEFAULT '[]'::jsonb,
    watchlist_ids        JSONB DEFAULT '[]'::jsonb,
    question_ids         JSONB DEFAULT '[]'::jsonb,
    upgrade_event_ids    JSONB DEFAULT '[]'::jsonb,
    usage_summary        TEXT,
    qa_checked           BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMP DEFAULT NOW()
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

ALTER TABLE ceo_decisions
    ADD COLUMN IF NOT EXISTS approval_type VARCHAR(50);

ALTER TABLE partner_feedback
    ALTER COLUMN partner_name SET DEFAULT 'Vice President';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ceo_decisions_decision'
    ) THEN
        ALTER TABLE ceo_decisions
            ADD CONSTRAINT chk_ceo_decisions_decision
            CHECK (decision IN ('approved', 'hold', 'rejected', 'request_more_research'));
    END IF;
END $$;

ALTER TABLE ceo_decisions
    DROP CONSTRAINT IF EXISTS chk_ceo_decisions_approval_type;

ALTER TABLE ceo_decisions
    ADD CONSTRAINT chk_ceo_decisions_approval_type
    CHECK (
        approval_type IS NULL OR approval_type IN (
            'signal_approve',
            'opportunity_approve',
            'vice_president_review_request',
            'customer_test_approve',
            'monetization_experiment_approve',
            'report_publish_approve',
            'investment_thesis_approve',
            'capital_action_approve',
            'legal_review_approve',
            'red_team_clear',
            'pre_mortem_approve',
            'qa_clear'
        )
    );

ALTER TABLE refined_outputs
    ADD COLUMN IF NOT EXISTS sensitivity_level VARCHAR(20) DEFAULT 'low';

ALTER TABLE refined_outputs
    ADD COLUMN IF NOT EXISTS requires_ceo_approval BOOLEAN DEFAULT FALSE;

ALTER TABLE refined_outputs
    ADD COLUMN IF NOT EXISTS notion_page_id TEXT;

ALTER TABLE research_reports
    ADD COLUMN IF NOT EXISTS sensitivity_level VARCHAR(20) DEFAULT 'medium';

ALTER TABLE research_reports
    ADD COLUMN IF NOT EXISTS requires_ceo_approval BOOLEAN DEFAULT FALSE;

ALTER TABLE research_reports
    ADD COLUMN IF NOT EXISTS notion_page_id TEXT;

CREATE INDEX IF NOT EXISTS idx_raw_signals_status
    ON raw_signals(status);

CREATE INDEX IF NOT EXISTS idx_filtered_signals_score
    ON filtered_signals(score DESC);

CREATE INDEX IF NOT EXISTS idx_signals_status_score
    ON signals(status, preliminary_score DESC);

CREATE INDEX IF NOT EXISTS idx_signals_type
    ON signals(signal_type);

CREATE INDEX IF NOT EXISTS idx_agent_reviews_signal
    ON agent_reviews(signal_id);

CREATE INDEX IF NOT EXISTS idx_agent_reviews_refined_output
    ON agent_reviews(refined_output_id);

CREATE INDEX IF NOT EXISTS idx_ceo_decisions_target
    ON ceo_decisions(target_type, target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_partner_feedback_target
    ON partner_feedback(target_type, target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_partner_feedback_market_read
    ON partner_feedback(market_read, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_research_reports_status
    ON research_reports(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_newsletter_issues_status
    ON newsletter_issues(status, issue_date DESC);

CREATE INDEX IF NOT EXISTS idx_content_reviews_issue
    ON content_reviews(newsletter_issue_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_subscriber_snapshots_date
    ON subscriber_snapshots(snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_customer_profiles_tier
    ON customer_profiles(tier, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_profiles_persona
    ON customer_profiles(persona_type, tier, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_memory_events_customer
    ON customer_memory_events(customer_id, event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_interest_tags_customer
    ON customer_interest_tags(customer_id, weight DESC);

CREATE INDEX IF NOT EXISTS idx_customer_preference_overrides_customer
    ON customer_preference_overrides(customer_id, active, preference_key, expires_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_watchlists_customer
    ON customer_watchlists(customer_id, active, priority);

CREATE INDEX IF NOT EXISTS idx_customer_questions_customer
    ON customer_questions(customer_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_questions_due
    ON customer_questions(status, priority, due_at);

CREATE INDEX IF NOT EXISTS idx_product_upgrade_events_product
    ON product_upgrade_events(product_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_artifact_memory_usage_artifact
    ON artifact_memory_usage(artifact_type, artifact_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_artifact_memory_usage_customer
    ON artifact_memory_usage(customer_id, audience_scope, created_at DESC);
