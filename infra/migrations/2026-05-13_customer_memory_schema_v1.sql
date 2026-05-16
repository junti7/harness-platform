ALTER TABLE customer_profiles
    ADD COLUMN IF NOT EXISTS persona_type VARCHAR(50) DEFAULT 'general';

ALTER TABLE customer_questions
    ADD COLUMN IF NOT EXISTS priority VARCHAR(30) DEFAULT 'medium',
    ADD COLUMN IF NOT EXISTS last_answered_artifact_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS last_answered_artifact_id INTEGER,
    ADD COLUMN IF NOT EXISTS due_at TIMESTAMP;

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

ALTER TABLE artifact_memory_usage
    ADD COLUMN IF NOT EXISTS customer_id INTEGER REFERENCES customer_profiles(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS audience_scope VARCHAR(30) DEFAULT 'segment',
    ADD COLUMN IF NOT EXISTS audience_key TEXT,
    ADD COLUMN IF NOT EXISTS override_ids JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_customer_profiles_persona
    ON customer_profiles(persona_type, tier, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_questions_due
    ON customer_questions(status, priority, due_at);

CREATE INDEX IF NOT EXISTS idx_customer_preference_overrides_customer
    ON customer_preference_overrides(customer_id, active, preference_key, expires_at DESC);

CREATE INDEX IF NOT EXISTS idx_artifact_memory_usage_customer
    ON artifact_memory_usage(customer_id, audience_scope, created_at DESC);
