-- 정제 backlog KPI(/api/pipeline/backlog) 지원 + SoT 드리프트 해소.
--
-- 배경: raw_signals.domain / filtered_signals.domain 컬럼은 프로덕션에는 이미 존재하지만
-- infra/schema.sql 정본 DDL 과 어떤 migration 에도 정의가 없었다(순수 prod 드리프트).
-- 기존 source-stats / pipeline/signals 가 이미 domain 을 조회하므로 fresh env 에서 깨질 수 있었다.
-- 본 migration 이 컬럼을 정본화하고, 폴링되는 backlog 집계용 인덱스를 함께 보강한다.
-- 모두 IF NOT EXISTS 라 idempotent 하며 기존 데이터/동작에 비파괴적이다.

ALTER TABLE raw_signals      ADD COLUMN IF NOT EXISTS domain VARCHAR(50);
ALTER TABLE filtered_signals ADD COLUMN IF NOT EXISTS domain VARCHAR(50);

-- raw_signals: WHERE status = 'pending' AND domain = %s (Tier2 대기 카운트) 가속.
CREATE INDEX IF NOT EXISTS idx_raw_signals_domain_status
    ON raw_signals(domain, status);

-- filtered_signals: WHERE domain = %s (정제 깔때기 스코프) 가속.
CREATE INDEX IF NOT EXISTS idx_filtered_signals_domain_created_at
    ON filtered_signals(domain, created_at);

-- refined_outputs: filtered_signals LEFT JOIN refined_outputs ON r.filtered_signal_id = f.id
-- 및 r.created_at 최근 1시간 FILTER 집계 가속(기존엔 pkey 만 있어 풀스캔).
CREATE INDEX IF NOT EXISTS idx_refined_outputs_filtered_signal_id
    ON refined_outputs(filtered_signal_id);
CREATE INDEX IF NOT EXISTS idx_refined_outputs_created_at
    ON refined_outputs(created_at DESC);
