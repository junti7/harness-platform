"""
LLM Lane Router — LLM Cost-Quality Strategy v1.2
Lane A: Haiku/Ollama (기계적), Lane B: Sonnet (내부 추론), Lane C: Sonnet (고객·자본)

Red Team clear: 2026-06-01
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

DAILY_COST_LIMIT = float(os.getenv("DAILY_COST_LIMIT_USD", "2.00"))
# Lane B를 차단하는 일일 비용 임계 비율 (기본값: 80%)
LANE_B_SUSPEND_RATIO = float(os.getenv("LANE_B_SUSPEND_RATIO", "0.80"))


class Lane(str, Enum):
    A = "mechanical"   # Haiku / Ollama — 기계적 작업
    B = "internal"     # Sonnet — 내부 추론
    C = "customer"     # Sonnet — 고객·자본 (품질 절대 타협 금지)


# 레인별 모델 할당 테이블
LANE_MODELS: dict[Lane, dict[str, str]] = {
    Lane.A: {
        "claude": os.getenv("LANE_A_CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        "gemini": os.getenv("LANE_A_GEMINI_MODEL", "gemini-2.5-flash"),
        "ollama": os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
    },
    Lane.B: {
        "claude": os.getenv("LANE_B_CLAUDE_MODEL", "claude-sonnet-4-5"),
        "gemini": os.getenv("LANE_B_GEMINI_MODEL", "gemini-2.5-flash"),
    },
    Lane.C: {
        "claude": os.getenv("LANE_C_CLAUDE_MODEL", "claude-sonnet-4-5"),
        "gemini": os.getenv("LANE_C_GEMINI_MODEL", "gemini-2.5-pro"),
    },
}

# task_type → Lane 매핑
TASK_LANE_MAP: dict[str, Lane] = {
    # Lane A — 기계적
    "dedup": Lane.A,
    "classify": Lane.A,
    "extract_facts": Lane.A,
    "json_format": Lane.A,
    "tool_routing": Lane.A,
    "tier2_gate": Lane.A,
    "summarize_short": Lane.A,
    # Lane B — 내부 추론
    "persona_opinion": Lane.B,
    "meeting_debate": Lane.B,
    "internal_memo": Lane.B,
    "market_analysis": Lane.B,
    "deep_research_sweep": Lane.B,
    # Lane C — 고객·자본
    "wtp_copy": Lane.C,
    "customer_facing": Lane.C,
    "ceo_decision_card": Lane.C,
    "investment_thesis": Lane.C,
    "qa_review": Lane.C,
    "red_team": Lane.C,
    "paid_artifact": Lane.C,
    "offer_design": Lane.C,
    "landing_copy": Lane.C,
}

# 무조건 Lane C로 강제 승급되는 task
_ALWAYS_LANE_C: frozenset[str] = frozenset({
    "financial_transaction",
    "customer_data_access",
    "capital_action",
    "legal_review",
})


def _must_escalate_to_c(task_type: str, context: dict[str, Any]) -> bool:
    if task_type in _ALWAYS_LANE_C:
        return True
    if context.get("chain_depth", 0) > 3:
        return True
    if context.get("promote_to_customer_facing", False):
        return True
    if context.get("force_lane_c", False):
        return True
    # 외부 claim, 요약-for-decision, cross-agent synthesis
    if context.get("has_external_claim", False):
        return True
    if context.get("is_summary_for_decision", False):
        return True
    return False


def get_lane(task_type: str, context: dict[str, Any] | None = None) -> Lane:
    ctx = context or {}
    if _must_escalate_to_c(task_type, ctx):
        return Lane.C
    return TASK_LANE_MAP.get(task_type, Lane.B)


def get_model(task_type: str, provider: str = "claude", context: dict[str, Any] | None = None) -> str:
    lane = get_lane(task_type, context)
    models = LANE_MODELS.get(lane, LANE_MODELS[Lane.B])
    return models.get(provider, models.get("claude", "claude-sonnet-4-5"))


# ── 볼륨 차단기 (Volume Circuit Breaker) ─────────────────────────────────────

def is_lane_b_available() -> bool:
    """
    일일 비용이 LANE_B_SUSPEND_RATIO 초과 시 Lane B(내부 회의)를 차단.
    Lane C(고객-facing)는 항상 허용.
    비용 조회 실패 시 fail-open (차단하지 않음).
    """
    try:
        from adapters.content.refiner import get_today_cost
        today = get_today_cost()
        threshold = DAILY_COST_LIMIT * LANE_B_SUSPEND_RATIO
        if today >= threshold:
            logger.warning(
                f"[LaneRouter] Lane B 차단 — 일일 비용 ${today:.4f} / ${DAILY_COST_LIMIT} "
                f"(임계값 ${threshold:.4f}, {LANE_B_SUSPEND_RATIO*100:.0f}%)"
            )
            _log_telemetry("lane_b_suspended", {
                "today_cost": round(today, 4),
                "threshold": round(threshold, 4),
                "limit": DAILY_COST_LIMIT,
            })
            return False
        return True
    except Exception as exc:
        logger.error(f"[LaneRouter] 비용 조회 실패, Lane B 허용 유지: {exc}")
        return True  # fail-open


# ── Lane A 검증 게이트 ────────────────────────────────────────────────────────

def validate_lane_a_json(
    output: str,
    required_keys: list[str] | None = None,
    allowed_values: dict[str, list] | None = None,
) -> dict | None:
    """
    Lane A JSON 출력 검증.
    성공: parsed dict 반환.
    실패: None 반환 → 호출부에서 Sonnet으로 자동 재실행(escalate).
    """
    cleaned = re.sub(r"```(?:json)?", "", output).strip().rstrip("`").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        _log_telemetry("lane_a_validation_fail", {"reason": "json_parse_error", "detail": str(exc)})
        return None

    if required_keys:
        missing = [k for k in required_keys if k not in parsed]
        if missing:
            _log_telemetry("lane_a_validation_fail", {"reason": "missing_keys", "keys": missing})
            return None

    if allowed_values:
        for key, allowed in allowed_values.items():
            val = parsed.get(key)
            if val is not None and val not in allowed:
                _log_telemetry("lane_a_validation_fail", {
                    "reason": "invalid_value", "key": key, "value": val, "allowed": allowed,
                })
                return None

    return parsed


# ── 텔레메트리 ────────────────────────────────────────────────────────────────

_TELEMETRY_PATH = ROOT / "logs" / "lane_telemetry.jsonl"


def _log_telemetry(event: str, data: dict[str, Any]) -> None:
    _TELEMETRY_PATH.parent.mkdir(exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **data}
    try:
        with open(_TELEMETRY_PATH, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
    logger.debug(f"[LaneTelemetry] {event}: {data}")


def log_routing(task_type: str, lane: Lane, model: str, escalated: bool = False) -> None:
    _log_telemetry("routing", {
        "task_type": task_type,
        "lane": lane.value,
        "model": model,
        "escalated": escalated,
    })


def log_lane_a_escalation(task_type: str, reason: str) -> None:
    _log_telemetry("lane_a_escalation", {"task_type": task_type, "reason": reason})


def log_rework(source_lane: Lane, reason: str, task_type: str = "") -> None:
    _log_telemetry("rework", {
        "source_lane": source_lane.value,
        "task_type": task_type,
        "reason": reason,
    })


def log_promote(artifact_id: str, from_lane: Lane, task_type: str = "") -> None:
    _log_telemetry("promote_to_customer_facing", {
        "artifact_id": artifact_id,
        "from_lane": from_lane.value,
        "task_type": task_type,
    })
