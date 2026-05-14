-- T-13: dead_letter_queue에 재시도 추적 컬럼 추가

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMP;

ALTER TABLE dead_letter_queue
    ADD COLUMN IF NOT EXISTS resolved BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_dlq_retry
    ON dead_letter_queue(resolved, retry_count, created_at);
