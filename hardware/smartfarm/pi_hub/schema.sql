CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL,
    metric TEXT NOT NULL,       -- 'soil_pct' | 'soil_raw' | 'temp_c' | 'humidity_pct'
    value REAL NOT NULL,
    -- KST(+09:00)로 저장한다. 오프셋 접미사를 반드시 함께 남긴다 —
    -- 오프셋 없는 값은 읽는 쪽(scripts/smartfarm_ops.py의 _parse_ts)이 UTC로 간주해 9시간 오차가 난다.
    -- 'localtime'이 아니라 '+9 hours'를 쓰는 이유는 호스트 TZ 설정에 의존하지 않게 하기 위함이다.
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', '+9 hours') || '+09:00')
);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_zone_metric_time
    ON sensor_readings (zone_id, metric, recorded_at);

CREATE TABLE IF NOT EXISTS pump_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL,
    action TEXT NOT NULL,       -- 'on' | 'off'
    reason TEXT NOT NULL,       -- 'threshold' | 'target_reached' | 'timeout' | 'sensor_fault' | 'manual'
    soil_pct_at_event REAL,
    -- KST(+09:00)로 저장한다. 오프셋 접미사를 반드시 함께 남긴다 —
    -- 오프셋 없는 값은 읽는 쪽(scripts/smartfarm_ops.py의 _parse_ts)이 UTC로 간주해 9시간 오차가 난다.
    -- 'localtime'이 아니라 '+9 hours'를 쓰는 이유는 호스트 TZ 설정에 의존하지 않게 하기 위함이다.
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', '+9 hours') || '+09:00')
);
CREATE INDEX IF NOT EXISTS idx_pump_events_zone_time
    ON pump_events (zone_id, recorded_at);
