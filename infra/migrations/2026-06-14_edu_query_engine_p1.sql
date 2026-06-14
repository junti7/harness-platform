CREATE EXTENSION IF NOT EXISTS pg_trgm;

ALTER TABLE pipeline_runs
    ALTER COLUMN correlation_id TYPE TEXT;

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS pipeline_name TEXT;

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS input_count INTEGER;

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS success_count INTEGER;

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS skipped_count INTEGER;

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS dlq_count INTEGER;

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS adapter_failures INTEGER;

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_corr
    ON pipeline_runs(correlation_id);

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS pipeline_name TEXT;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS reason_code TEXT;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS correlation_id TEXT;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS source_name TEXT;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS external_key TEXT;

UPDATE dead_letter_queue
   SET resolved = FALSE
 WHERE resolved IS NULL;

ALTER TABLE dead_letter_queue
    ALTER COLUMN resolved SET DEFAULT FALSE;

ALTER TABLE dead_letter_queue
    ALTER COLUMN resolved SET NOT NULL;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS first_seen_correlation_id TEXT;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS last_seen_correlation_id TEXT;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS occurrence_count INTEGER NOT NULL DEFAULT 1;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP DEFAULT NOW();

UPDATE dead_letter_queue
   SET pipeline_name = COALESCE(pipeline_name, 'legacy'),
       reason_code = COALESCE(reason_code, 'legacy_unknown'),
       external_key = COALESCE(
           external_key,
           NULLIF(raw_data->>'natural_key', ''),
           NULLIF(raw_data->>'source_id', ''),
           NULLIF(raw_data->>'source_url', ''),
           NULLIF(raw_data->>'path', ''),
           md5(COALESCE(raw_data::text, 'legacy-null-raw-data'))
       ),
       first_seen_correlation_id = COALESCE(first_seen_correlation_id, correlation_id),
       last_seen_correlation_id = COALESCE(last_seen_correlation_id, correlation_id),
       occurrence_count = COALESCE(occurrence_count, 1),
       last_seen_at = COALESCE(last_seen_at, created_at, NOW())
 WHERE pipeline_name IS NULL
    OR reason_code IS NULL
    OR external_key IS NULL
    OR first_seen_correlation_id IS NULL
    OR last_seen_correlation_id IS NULL
    OR occurrence_count IS NULL
    OR last_seen_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_dlq_corr
    ON dead_letter_queue(correlation_id, resolved, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dlq_external_key
    ON dead_letter_queue(external_key);

WITH ranked AS (
    SELECT
        id,
        pipeline_name,
        tier,
        external_key,
        reason_code,
        item_type,
        resolved,
        created_at,
        occurrence_count,
        first_seen_correlation_id,
        last_seen_correlation_id,
        last_seen_at,
        ROW_NUMBER() OVER (
            PARTITION BY pipeline_name, tier, external_key, reason_code, item_type, resolved
            ORDER BY created_at ASC, id ASC
        ) AS rn,
        SUM(COALESCE(occurrence_count, 1)) OVER (
            PARTITION BY pipeline_name, tier, external_key, reason_code, item_type, resolved
        ) AS merged_occurrence_count,
        MAX(COALESCE(last_seen_at, created_at, NOW())) OVER (
            PARTITION BY pipeline_name, tier, external_key, reason_code, item_type, resolved
        ) AS merged_last_seen_at,
        FIRST_VALUE(COALESCE(first_seen_correlation_id, correlation_id)) OVER (
            PARTITION BY pipeline_name, tier, external_key, reason_code, item_type, resolved
            ORDER BY created_at ASC, id ASC
        ) AS merged_first_seen_correlation_id,
        FIRST_VALUE(COALESCE(last_seen_correlation_id, correlation_id)) OVER (
            PARTITION BY pipeline_name, tier, external_key, reason_code, item_type, resolved
            ORDER BY COALESCE(last_seen_at, created_at, NOW()) DESC, id DESC
        ) AS merged_last_seen_correlation_id
    FROM dead_letter_queue
    WHERE resolved = FALSE
),
keeper_update AS (
    UPDATE dead_letter_queue d
       SET occurrence_count = r.merged_occurrence_count,
           first_seen_correlation_id = r.merged_first_seen_correlation_id,
           last_seen_correlation_id = r.merged_last_seen_correlation_id,
           correlation_id = r.merged_last_seen_correlation_id,
           last_seen_at = r.merged_last_seen_at
      FROM ranked r
     WHERE d.id = r.id
       AND r.rn = 1
    RETURNING d.id
)
UPDATE dead_letter_queue d
   SET resolved = TRUE,
       last_retry_at = COALESCE(d.last_retry_at, NOW()),
       error_message = CONCAT(COALESCE(d.error_message, ''), ' [deduped-before-idx]')
  FROM ranked r
 WHERE d.id = r.id
   AND r.rn > 1;

DROP INDEX IF EXISTS idx_dlq_unresolved_reuse;

CREATE UNIQUE INDEX IF NOT EXISTS idx_dlq_unresolved_reuse
    ON dead_letter_queue(pipeline_name, tier, external_key, reason_code, item_type)
    WHERE resolved = FALSE;

ALTER TABLE api_cost_log
    ADD COLUMN IF NOT EXISTS tier TEXT;

ALTER TABLE api_cost_log
    ADD COLUMN IF NOT EXISTS correlation_id TEXT;

ALTER TABLE api_cost_log
    ADD COLUMN IF NOT EXISTS est_tokens INTEGER;

ALTER TABLE api_cost_log
    ADD COLUMN IF NOT EXISTS actual_tokens INTEGER;

CREATE INDEX IF NOT EXISTS idx_api_cost_log_corr
    ON api_cost_log(correlation_id);

CREATE TABLE IF NOT EXISTS edu_knowledge_items (
    id BIGSERIAL PRIMARY KEY,
    source_ref TEXT,
    natural_key TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    source_id TEXT,
    source_url TEXT,
    source_kind TEXT NOT NULL DEFAULT 'general_reference'
        CHECK (source_kind IN ('community_voice', 'research_policy', 'media_case', 'general_reference')),
    provenance TEXT NOT NULL DEFAULT 'collected'
        CHECK (provenance IN ('collected', 'curated', 'generated')),
    rights_class TEXT NOT NULL DEFAULT 'unknown'
        CHECK (rights_class IN ('public', 'fair_excerpt', 'internal_only', 'unknown')),
    reuse_scope TEXT NOT NULL DEFAULT 'internal'
        CHECK (reuse_scope IN ('customer_facing', 'internal')),
    excerpt_max_chars INTEGER NOT NULL DEFAULT 0,
    verbatim_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    segment TEXT,
    item_type TEXT,
    title TEXT,
    body TEXT NOT NULL,
    cite TEXT,
    lang TEXT NOT NULL DEFAULT 'ko',
    quality_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    emb_model TEXT,
    emb_dim INTEGER,
    collected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eki_source_kind
    ON edu_knowledge_items(source_kind);

CREATE INDEX IF NOT EXISTS idx_eki_segment
    ON edu_knowledge_items(segment);

CREATE INDEX IF NOT EXISTS idx_eki_keywords
    ON edu_knowledge_items USING GIN (keywords);

CREATE UNIQUE INDEX IF NOT EXISTS idx_eki_source_ref
    ON edu_knowledge_items(source_ref)
    WHERE source_ref IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_eki_servable
    ON edu_knowledge_items(reuse_scope, provenance, quality_score DESC);

CREATE INDEX IF NOT EXISTS idx_eki_body_trgm
    ON edu_knowledge_items USING GIN (body gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_eki_cite_trgm
    ON edu_knowledge_items USING GIN (cite gin_trgm_ops);

CREATE OR REPLACE VIEW edu_knowledge_items_customer_facing AS
SELECT *
  FROM public.edu_knowledge_items
 WHERE reuse_scope = 'customer_facing'
   AND provenance IN ('collected', 'curated')
   AND rights_class IN ('public', 'fair_excerpt')
   AND excerpt_max_chars > 0;

CREATE TABLE IF NOT EXISTS edu_rag_accumulation (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    case_id BIGINT,
    query_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    cited_item_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    grounded BOOLEAN NOT NULL DEFAULT FALSE,
    promoted BOOLEAN NOT NULL DEFAULT FALSE,
    verified_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_era_case
    ON edu_rag_accumulation(case_id);

CREATE INDEX IF NOT EXISTS idx_era_promoted
    ON edu_rag_accumulation(promoted);

CREATE INDEX IF NOT EXISTS idx_era_corr
    ON edu_rag_accumulation(correlation_id);
