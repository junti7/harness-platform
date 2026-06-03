CREATE TABLE IF NOT EXISTS edu_customers (
    id BIGSERIAL PRIMARY KEY,
    segment TEXT NOT NULL DEFAULT 'parent',
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    preferred_salutation TEXT NOT NULL DEFAULT 'neutral',
    locale TEXT NOT NULL DEFAULT 'ko-KR',
    preferred_llm TEXT NOT NULL DEFAULT 'auto',
    login_channel TEXT NOT NULL DEFAULT 'magic_link',
    consent_version TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE edu_customers ADD COLUMN IF NOT EXISTS preferred_salutation TEXT NOT NULL DEFAULT 'neutral';
ALTER TABLE edu_customers ADD COLUMN IF NOT EXISTS locale TEXT NOT NULL DEFAULT 'ko-KR';
ALTER TABLE edu_customers ADD COLUMN IF NOT EXISTS preferred_llm TEXT NOT NULL DEFAULT 'auto';

CREATE INDEX IF NOT EXISTS idx_edu_customers_email ON edu_customers (email);
CREATE INDEX IF NOT EXISTS idx_edu_customers_phone ON edu_customers (phone);

CREATE TABLE IF NOT EXISTS edu_cases (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES edu_customers(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'intake',
    child_grade TEXT NOT NULL DEFAULT '',
    primary_concern TEXT NOT NULL DEFAULT '',
    ai_usage_context TEXT NOT NULL DEFAULT '',
    current_phase TEXT NOT NULL DEFAULT 'opening',
    current_tone_level INTEGER NOT NULL DEFAULT 0,
    last_turn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edu_cases_customer_id ON edu_cases (customer_id);
CREATE INDEX IF NOT EXISTS idx_edu_cases_status ON edu_cases (status);

CREATE TABLE IF NOT EXISTS edu_case_turns (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES edu_cases(id) ON DELETE CASCADE,
    turn_no INTEGER NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT '',
    tone_level INTEGER NOT NULL DEFAULT 0,
    quick_replies_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    show_offer BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edu_case_turns_case_id ON edu_case_turns (case_id);
CREATE INDEX IF NOT EXISTS idx_edu_case_turns_case_turn ON edu_case_turns (case_id, turn_no);

CREATE TABLE IF NOT EXISTS edu_case_snapshots (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES edu_cases(id) ON DELETE CASCADE,
    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    detected_patterns_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommended_next_questions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    offer_readiness_score NUMERIC(5,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edu_case_snapshots_case_id ON edu_case_snapshots (case_id);

CREATE TABLE IF NOT EXISTS edu_case_offers (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES edu_cases(id) ON DELETE CASCADE,
    offer_type TEXT NOT NULL,
    shown_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    declined_at TIMESTAMPTZ,
    offer_context_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_edu_case_offers_case_id ON edu_case_offers (case_id);

CREATE TABLE IF NOT EXISTS edu_magic_links (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES edu_customers(id) ON DELETE CASCADE,
    case_id BIGINT REFERENCES edu_cases(id) ON DELETE SET NULL,
    email TEXT NOT NULL DEFAULT '',
    token_hash TEXT NOT NULL UNIQUE,
    segment TEXT NOT NULL DEFAULT 'parent',
    name TEXT NOT NULL DEFAULT '',
    preferred_salutation TEXT NOT NULL DEFAULT 'neutral',
    locale TEXT NOT NULL DEFAULT 'ko-KR',
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE edu_magic_links ADD COLUMN IF NOT EXISTS preferred_salutation TEXT NOT NULL DEFAULT 'neutral';
ALTER TABLE edu_magic_links ADD COLUMN IF NOT EXISTS locale TEXT NOT NULL DEFAULT 'ko-KR';
ALTER TABLE edu_magic_links ADD COLUMN IF NOT EXISTS case_id BIGINT REFERENCES edu_cases(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_edu_magic_links_email ON edu_magic_links (email);
CREATE INDEX IF NOT EXISTS idx_edu_magic_links_expires_at ON edu_magic_links (expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_edu_magic_links_case_id ON edu_magic_links (case_id);
