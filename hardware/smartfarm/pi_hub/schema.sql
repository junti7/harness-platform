CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL,
    metric TEXT NOT NULL,       -- 'soil_pct' | 'temp_c' | 'humidity_pct'
    value REAL NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_zone_metric_time
    ON sensor_readings (zone_id, metric, recorded_at);

CREATE TABLE IF NOT EXISTS pump_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL,
    action TEXT NOT NULL,       -- 'on' | 'off'
    reason TEXT NOT NULL,       -- 'threshold' | 'target_reached' | 'timeout' | 'manual'
    soil_pct_at_event REAL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_pump_events_zone_time
    ON pump_events (zone_id, recorded_at);
