-- T-06: 구독자 무료→유료 전환 추적 테이블
-- Free→Paid 전환 이벤트를 기록한다. product_upgrade_events는 제품 기능 개선용이므로 별도 테이블.

CREATE TABLE IF NOT EXISTS subscriber_conversion_events (
    id              SERIAL PRIMARY KEY,
    customer_id     INTEGER REFERENCES customer_profiles(id) ON DELETE SET NULL,
    event_type      VARCHAR(50)  NOT NULL,   -- 'free_to_paid', 'paid_to_free', 'churn'
    plan            VARCHAR(100),             -- 'paid_9900_krw'
    source          VARCHAR(100),             -- 'substack'
    snapshot_date   DATE         NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriber_conversion_events_date
    ON subscriber_conversion_events(snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_subscriber_conversion_events_type
    ON subscriber_conversion_events(event_type, created_at DESC);
