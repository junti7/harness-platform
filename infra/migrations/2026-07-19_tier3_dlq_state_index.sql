-- Tier3 일반 worker, DLQ retry worker, backlog KPI 사이 상태 소유권 조회 가속.
-- resolved=false: retry worker 소유, resolved=true: permanent terminal.
CREATE INDEX IF NOT EXISTS idx_dlq_item_state
    ON dead_letter_queue(item_type, item_id, resolved);
