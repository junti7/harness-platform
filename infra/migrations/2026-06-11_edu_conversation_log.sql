-- Edu 대화 전수 기록(append-only) — "빠짐없이 기록" (CEO 지시 2026-06-11)
-- diagnose/curriculum 등 모든 대화 엔드포인트의 요청+응답을 case_id/성공여부와 무관하게 보존한다.
-- edu_case_turns(구조화·resume용)와 별개로, 누락 0을 보장하는 raw 원장(system of record).
-- append-only: UPDATE/DELETE 하지 않는다. PII 포함 가능 → 내부 전용, IP는 해시로만 저장.

CREATE TABLE IF NOT EXISTS edu_conversation_log (
    id            BIGSERIAL PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    endpoint      TEXT NOT NULL,            -- 예: '/api/public/edu/curriculum'
    kind          TEXT NOT NULL,            -- 'diagnose' | 'curriculum'
    authed        BOOLEAN NOT NULL DEFAULT FALSE,  -- 인증(내부) vs 공개(익명 PoC)
    segment       TEXT,                     -- 'parent' | 'worker'
    track         TEXT,                     -- curriculum: 'free_start' | 'next_steps'
    turn          INTEGER,
    case_id       BIGINT,                   -- 있으면 edu_cases 연결(FK 없음: 익명도 보존)
    user_text     TEXT,                     -- diagnose 최신 사용자 입력(빠른 스캔용)
    locale        TEXT,
    ok            BOOLEAN,                  -- 응답 생성 성공(비어있지 않은 dict) 여부
    ip_hash       TEXT,                     -- sha256(ip)[:16], 원본 IP 미저장
    request_json  JSONB,                    -- 인바운드 요청 전체(history 포함)
    response_json JSONB                     -- 응답 전체(fallback 포함)
);

CREATE INDEX IF NOT EXISTS idx_edu_conv_log_created ON edu_conversation_log (created_at);
CREATE INDEX IF NOT EXISTS idx_edu_conv_log_case ON edu_conversation_log (case_id);
CREATE INDEX IF NOT EXISTS idx_edu_conv_log_kind ON edu_conversation_log (kind);
