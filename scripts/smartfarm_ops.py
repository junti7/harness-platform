"""Data-driven ops helpers for the smartfarm pilot: alerts, status reports,
and threshold-adjustment proposals for CEO review.

Boundary (mirrors openclaw_smartfarm_research_bridge.py): nothing here issues an
MQTT command or touches an actuator. Pump control stays exclusively in
hardware/smartfarm/pi_hub/hub.py. The only side-effecting function is
apply_threshold_decision(), and it refuses to run unless a prior 'approved'
record already exists in the decision log for that proposal.

config.yaml is hand-commented and intentionally not re-serialized through a
YAML dumper (that would silently drop the Korean explanatory comments). Both
the reader and the patcher work by scanning the known
`zones: / <id>: / <key>: <value>` indentation shape used by
hardware/smartfarm/pi_hub/config.example.yaml.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "hardware/smartfarm/pi_hub/smartfarm.db"
DEFAULT_CONFIG_PATH = REPO_ROOT / "hardware/smartfarm/pi_hub/config.yaml"
DEFAULT_DECISION_LOG_PATH = REPO_ROOT / "docs/reports/smartfarm/threshold_decisions.jsonl"

EXPECTED_READING_INTERVAL_S = 30
METRIC_RANGES = {
    "soil_pct": (0.0, 100.0),
    "temp_c": (-20.0, 60.0),
    "humidity_pct": (0.0, 100.0),
}
STUCK_SAMPLE_COUNT = 6  # last N readings identical => likely a dead/disconnected sensor
SILENCE_MULTIPLIER = 10  # no reading for 10x the expected interval => node considered silent
SHORT_CYCLE_DAILY_ON_EVENTS = 20  # pump 'on' events/day above this => threshold gap too narrow


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(raw: str) -> datetime:
    cleaned = raw.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _proposal_id(zone_id: str, kind: str) -> str:
    """Deterministic (not random) so the same id survives across separate CLI
    invocations: propose -> (human reviews) -> decide -> apply are 4 different
    process runs and must agree on which proposal is being approved."""
    return hashlib.sha256(f"{zone_id}:{kind}".encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# config.yaml (comment-preserving, hand-rolled parser/patcher)
# ---------------------------------------------------------------------------

_ZONE_HEADER_RE = re.compile(r"^  (\w[\w-]*):\s*(?:#.*)?$")
_ZONE_KEY_RE = re.compile(r"^(    )(\w[\w-]*):\s*([0-9]+(?:\.[0-9]+)?)\s*(#.*)?$")


def load_zones_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, dict[str, float]]:
    """Parse the `zones:` block of config.yaml without a YAML dependency.

    Only numeric zone parameters (soil_min_pct, water_duration_s, ...) are
    extracted; that is all the ops logic below needs.
    """
    text = Path(config_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        zones_idx = next(i for i, line in enumerate(lines) if line.rstrip() == "zones:")
    except StopIteration as exc:
        raise ValueError(f"{config_path} has no top-level 'zones:' block") from exc

    zones: dict[str, dict[str, float]] = {}
    current: str | None = None
    for line in lines[zones_idx + 1 :]:
        if not line.strip():
            continue
        header = _ZONE_HEADER_RE.match(line)
        if header:
            current = header.group(1)
            zones[current] = {}
            continue
        key_match = _ZONE_KEY_RE.match(line)
        if key_match and current is not None:
            zones[current][key_match.group(2)] = float(key_match.group(3))
            continue
        if line.startswith(("  ", "\t")) is False:
            break  # dedented back to top level => zones block ended
    if not zones:
        raise ValueError(f"{config_path} 'zones:' block is empty or unparseable")
    return zones


def patch_zone_thresholds(
    config_path: Path,
    zone_id: str,
    updates: dict[str, float],
) -> None:
    """Rewrite only the given numeric keys inside one zone's block, byte-for-byte
    preserving every other line (including comments and formatting)."""
    path = Path(config_path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_target_zone = False
    applied: set[str] = set()

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip("\n")
        header = _ZONE_HEADER_RE.match(line)
        if header:
            in_target_zone = header.group(1) == zone_id
            continue
        if not in_target_zone:
            continue
        key_match = _ZONE_KEY_RE.match(line)
        if key_match and key_match.group(2) in updates:
            indent, key, _old_value, comment = key_match.groups()
            new_value = updates[key]
            rendered = f"{int(new_value)}" if float(new_value).is_integer() else str(new_value)
            newline = "\n" if raw_line.endswith("\n") else ""
            lines[i] = f"{indent}{key}: {rendered}{(' ' + comment) if comment else ''}{newline}"
            applied.add(key)

    missing = set(updates) - applied
    if missing:
        raise ValueError(f"zone '{zone_id}' is missing key(s) to patch: {sorted(missing)}")
    path.write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# SQLite reads
# ---------------------------------------------------------------------------


def _connect(db_path: Path) -> sqlite3.Connection:
    if not Path(db_path).exists():
        raise FileNotFoundError(f"smartfarm db not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_readings(db_path: Path, zone_id: str, metric: str) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT value, recorded_at FROM sensor_readings "
            "WHERE zone_id = ? AND metric = ? ORDER BY recorded_at ASC",
            (zone_id, metric),
        ).fetchall()
        return [{"value": r["value"], "recorded_at": r["recorded_at"]} for r in rows]
    finally:
        conn.close()


def fetch_pump_events(db_path: Path, zone_id: str) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT action, reason, soil_pct_at_event, recorded_at FROM pump_events "
            "WHERE zone_id = ? ORDER BY recorded_at ASC",
            (zone_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def known_zone_ids(db_path: Path) -> list[str]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT DISTINCT zone_id FROM sensor_readings").fetchall()
        return sorted(r["zone_id"] for r in rows)
    finally:
        conn.close()


def _since(rows: list[dict[str, Any]], cutoff: datetime) -> list[dict[str, Any]]:
    return [r for r in rows if _parse_ts(r["recorded_at"]) >= cutoff]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


def detect_alerts(
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    lookback_hours: float = 24.0,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Read-only anomaly scan. Every alert cites the exact readings that
    triggered it so a human can verify the claim against the raw data."""
    now = now or _now()
    cutoff = now - timedelta(hours=lookback_hours)
    zones = load_zones_config(config_path)
    alerts: list[dict[str, Any]] = []

    for zone_id in zones:
        for metric in ("soil_pct", "temp_c", "humidity_pct"):
            try:
                rows = fetch_readings(db_path, zone_id, metric)
            except FileNotFoundError:
                alerts.append(
                    {
                        "type": "db_missing",
                        "severity": "high",
                        "zone_id": zone_id,
                        "metric": metric,
                        "detail": f"smartfarm db not found at {db_path}",
                    }
                )
                return alerts
            if not rows:
                alerts.append(
                    {
                        "type": "no_data_ever",
                        "severity": "medium",
                        "zone_id": zone_id,
                        "metric": metric,
                        "detail": "no readings recorded for this zone/metric yet",
                    }
                )
                continue

            latest = rows[-1]
            latest_ts = _parse_ts(latest["recorded_at"])
            silence_s = (now - latest_ts).total_seconds()
            if silence_s > EXPECTED_READING_INTERVAL_S * SILENCE_MULTIPLIER:
                alerts.append(
                    {
                        "type": "sensor_silent",
                        "severity": "high",
                        "zone_id": zone_id,
                        "metric": metric,
                        "detail": f"no reading in {silence_s / 60:.1f} min (expected every {EXPECTED_READING_INTERVAL_S}s)",
                        "last_reading": latest,
                    }
                )

            lo, hi = METRIC_RANGES[metric]
            out_of_range = [r for r in _since(rows, cutoff) if not (lo <= r["value"] <= hi)]
            if out_of_range:
                alerts.append(
                    {
                        "type": "out_of_range",
                        "severity": "high",
                        "zone_id": zone_id,
                        "metric": metric,
                        "detail": f"{len(out_of_range)} reading(s) outside plausible range [{lo}, {hi}] in last {lookback_hours}h",
                        "examples": out_of_range[:3],
                    }
                )

            tail = rows[-STUCK_SAMPLE_COUNT:]
            if len(tail) == STUCK_SAMPLE_COUNT and len({r["value"] for r in tail}) == 1:
                alerts.append(
                    {
                        "type": "sensor_stuck",
                        "severity": "medium",
                        "zone_id": zone_id,
                        "metric": metric,
                        "detail": f"last {STUCK_SAMPLE_COUNT} readings are all exactly {tail[0]['value']} — likely a disconnected or dead sensor",
                        "since": tail[0]["recorded_at"],
                    }
                )

        pump_events = _since(fetch_pump_events(db_path, zone_id), now - timedelta(hours=24))
        on_events = [e for e in pump_events if e["action"] == "on"]
        if len(on_events) > SHORT_CYCLE_DAILY_ON_EVENTS:
            alerts.append(
                {
                    "type": "pump_short_cycling",
                    "severity": "medium",
                    "zone_id": zone_id,
                    "detail": (
                        f"pump turned on {len(on_events)} times in the last 24h "
                        f"(threshold {SHORT_CYCLE_DAILY_ON_EVENTS}) — soil_min_pct/soil_target_pct "
                        "gap may be too narrow, or a sensor fault is causing false triggers"
                    ),
                }
            )

    return alerts


# ---------------------------------------------------------------------------
# Status report
# ---------------------------------------------------------------------------


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(sum(values) / len(values), 2),
    }


def build_status_report(
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    period_hours: float = 24.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or _now()
    cutoff = now - timedelta(hours=period_hours)
    zones = load_zones_config(config_path)
    report: dict[str, Any] = {
        "generated_at": _iso(now),
        "period_hours": period_hours,
        "zones": {},
    }

    for zone_id, cfg in zones.items():
        zone_report: dict[str, Any] = {"thresholds": cfg}
        for metric in ("soil_pct", "temp_c", "humidity_pct"):
            try:
                rows = _since(fetch_readings(db_path, zone_id, metric), cutoff)
            except FileNotFoundError:
                zone_report[metric] = {"error": "db_missing"}
                continue
            zone_report[metric] = _stats([r["value"] for r in rows]) if rows else {"count": 0}

        pump_events = _since(fetch_pump_events(db_path, zone_id), cutoff)
        on_events = [e for e in pump_events if e["action"] == "on"]
        off_events = {e["recorded_at"]: e for e in pump_events if e["action"] == "off"}
        zone_report["pump"] = {
            "on_count": len(on_events),
            "reasons": sorted({e["reason"] for e in pump_events}),
        }
        report["zones"][zone_id] = zone_report

    return report


# ---------------------------------------------------------------------------
# Threshold-adjustment proposals (data-driven suggestion, never auto-applied)
# ---------------------------------------------------------------------------


def propose_threshold_adjustments(
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    lookback_hours: float = 168.0,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Heuristic, evidence-cited suggestions only. Each proposal states the
    observed pattern it is based on; it is not agronomic advice and always
    requires an explicit CEO decision (threshold-decide) before
    apply_threshold_decision() will touch config.yaml."""
    now = now or _now()
    cutoff = now - timedelta(hours=lookback_hours)
    zones = load_zones_config(config_path)
    alerts = detect_alerts(db_path, config_path, lookback_hours=24.0, now=now)
    # Only a stuck *soil* sensor should block a soil-threshold proposal; a stuck
    # temp/humidity sensor in the same zone is unrelated to the irrigation logic.
    stuck_zones = {
        a["zone_id"] for a in alerts if a["type"] == "sensor_stuck" and a.get("metric") == "soil_pct"
    }
    proposals: list[dict[str, Any]] = []

    for zone_id, cfg in zones.items():
        soil_min = cfg.get("soil_min_pct")
        soil_target = cfg.get("soil_target_pct")
        if soil_min is None or soil_target is None:
            continue

        try:
            soil_rows = _since(fetch_readings(db_path, zone_id, "soil_pct"), cutoff)
        except FileNotFoundError:
            continue
        if not soil_rows:
            continue
        values = [r["value"] for r in soil_rows]
        observed_min = min(values)
        pump_events = _since(fetch_pump_events(db_path, zone_id), cutoff)
        on_count = len([e for e in pump_events if e["action"] == "on"])
        days = max(lookback_hours / 24.0, 1e-6)
        on_per_day = on_count / days

        if zone_id in stuck_zones:
            proposals.append(
                {
                    "proposal_id": _proposal_id(zone_id, "investigate_before_adjusting"),
                    "zone_id": zone_id,
                    "kind": "investigate_before_adjusting",
                    "current": {"soil_min_pct": soil_min, "soil_target_pct": soil_target},
                    "suggested": None,
                    "rationale": (
                        "soil sensor reading looks stuck (flat) in the last 24h — a threshold "
                        "change would be tuning against a broken signal. Fix/recalibrate the "
                        "sensor first, then reassess."
                    ),
                    "evidence": {"lookback_hours": 24.0, "alert_type": "sensor_stuck"},
                }
            )
            continue

        if on_per_day > SHORT_CYCLE_DAILY_ON_EVENTS:
            widened_target = round(min(soil_target + 10, 95), 1)
            proposals.append(
                {
                    "proposal_id": _proposal_id(zone_id, "widen_hysteresis_band"),
                    "zone_id": zone_id,
                    "kind": "widen_hysteresis_band",
                    "current": {"soil_min_pct": soil_min, "soil_target_pct": soil_target},
                    "suggested": {"soil_min_pct": soil_min, "soil_target_pct": widened_target},
                    "rationale": (
                        f"pump cycled on {on_per_day:.1f} times/day over the last "
                        f"{lookback_hours:.0f}h (threshold {SHORT_CYCLE_DAILY_ON_EVENTS}/day). "
                        f"The {soil_target - soil_min:.1f}pt gap between soil_min_pct and "
                        "soil_target_pct is likely too narrow for the sensor's noise floor, "
                        "causing short-cycling. Widening soil_target_pct increases the buffer."
                    ),
                    "evidence": {
                        "lookback_hours": lookback_hours,
                        "pump_on_events": on_count,
                        "pump_on_per_day": round(on_per_day, 2),
                    },
                }
            )
        elif observed_min > soil_min + 15:
            proposals.append(
                {
                    "proposal_id": _proposal_id(zone_id, "informational_never_triggered"),
                    "zone_id": zone_id,
                    "kind": "informational_never_triggered",
                    "current": {"soil_min_pct": soil_min, "soil_target_pct": soil_target},
                    "suggested": None,
                    "rationale": (
                        f"soil_pct never dropped below {observed_min:.1f}% in the last "
                        f"{lookback_hours:.0f}h, well above soil_min_pct={soil_min}. Irrigation "
                        "has not triggered at all in this window. This is informational only — "
                        "raising soil_min_pct is an agronomic judgment call, not something this "
                        "script can decide from soil data alone."
                    ),
                    "evidence": {
                        "lookback_hours": lookback_hours,
                        "observed_min_soil_pct": round(observed_min, 2),
                        "pump_on_events": on_count,
                    },
                }
            )

    return proposals


# ---------------------------------------------------------------------------
# Decision log (append-only JSONL; last record per proposal_id wins)
# ---------------------------------------------------------------------------


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def record_threshold_decision(
    proposal: dict[str, Any],
    decision: str,
    decided_by: str,
    note: str = "",
    log_path: Path = DEFAULT_DECISION_LOG_PATH,
) -> dict[str, Any]:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be 'approved' or 'rejected'")
    record = {
        "proposal_id": proposal["proposal_id"],
        "zone_id": proposal["zone_id"],
        "kind": proposal["kind"],
        "suggested": proposal.get("suggested"),
        "decision": decision,
        "decided_by": decided_by,
        "note": note,
        "decided_at": _iso(_now()),
        "status": decision,
    }
    _append_jsonl(log_path, record)
    return record


def _latest_decision(proposal_id: str, log_path: Path) -> dict[str, Any] | None:
    matches = [r for r in _read_jsonl(log_path) if r.get("proposal_id") == proposal_id]
    return matches[-1] if matches else None


def apply_threshold_decision(
    proposal_id: str,
    config_path: Path = DEFAULT_CONFIG_PATH,
    log_path: Path = DEFAULT_DECISION_LOG_PATH,
) -> dict[str, Any]:
    """Refuses unless the last recorded decision for this proposal_id is
    'approved' and carries a concrete 'suggested' value set. This is the only
    function in this module that writes to config.yaml."""
    decision = _latest_decision(proposal_id, log_path)
    if decision is None:
        raise PermissionError(f"no recorded decision for proposal_id={proposal_id}; run threshold-decide first")
    if decision.get("status") != "approved":
        raise PermissionError(f"proposal_id={proposal_id} is not approved (status={decision.get('status')})")
    suggested = decision.get("suggested")
    if not suggested:
        raise ValueError(f"proposal_id={proposal_id} has no concrete suggested values to apply")

    patch_zone_thresholds(config_path, decision["zone_id"], suggested)
    applied_record = {**decision, "status": "applied", "applied_at": _iso(_now())}
    _append_jsonl(log_path, applied_record)
    return applied_record
