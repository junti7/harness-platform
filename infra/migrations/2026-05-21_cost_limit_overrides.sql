-- CEO-approved daily cost limit overrides (월말까지 유효, 이후 자동 만료)
CREATE TABLE IF NOT EXISTS cost_limit_overrides (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    base_limit NUMERIC(10,2) NOT NULL,
    override_limit NUMERIC(10,2) NOT NULL,
    valid_until DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- daily_cost_alerts에 source 컬럼 추가 (pipeline / openclaw 구분)
ALTER TABLE daily_cost_alerts ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'pipeline';
