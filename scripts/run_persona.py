"""Single-persona runner — the smallest unit of the agentic orchestration loop.

Given a persona handle (from agents/registry.py) and a task, this:
  1. loads the persona's SYSTEM_PROMPT.md,
  2. calls the persona's primary LLM CLI (claude/gemini/codex/copilot),
  3. posts the persona's opinion to its Slack home channel (구어체, Charter §4.3),
  4. appends a factual run-record to the persona's MEMORY.md (Charter §8).

It works for ANY active persona — adding teams later needs no change here, only a
registry entry + active flag + channel. The orchestrator (adapters/content/
orchestrator.py) imports call_persona / post_opinion / call_llm from this module.

Usage:
    python scripts/run_persona.py friday --task "이번 주 무료 구독자 정체 원인 봐줘"
    python scripts/run_persona.py friday --task "..." --dry-run    # no LLM, no post
    python scripts/run_persona.py kitt   --task "..." --no-post     # call LLM, skip Slack
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.content.slack_format import to_slack_mrkdwn  # noqa: E402
from agents.registry import Persona, get_persona  # noqa: E402

load_dotenv(override=True)

PROVIDER_TIMEOUT = 240
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENCLAW_STATUS_PATH = PROJECT_ROOT / "runtime/openclaw_status.json"
AR_TRACKER_PATH = PROJECT_ROOT / "docs/reports/ar_tracker.jsonl"
ORCHESTRATION_RUNS_PATH = PROJECT_ROOT / "docs/reports/orchestration_runs.jsonl"

# Patterns emitted by Claude Code's internal context-compaction machinery.
# These must never propagate into persona responses or conversation history.
_INTERNAL_CLI_RE = re.compile(
    r"CRITICAL:\s*Respond with TEXT ONLY[^\n]*(\n.*?)?(?=\n\n|\Z)"
    r"|<system-reminder>.*?</system-reminder>"
    r"|\[context_compaction[^\]]*\]"
    r"|update_topic\(.*?\)\n?",
    re.DOTALL | re.IGNORECASE,
)
_PERSONA_NOISE_RE = re.compile(
    r"(?is)(\n?---\n?.*)?$"
)
_DIARY_APPEND_RE = re.compile(
    r"(?is)(\*\*diary append\*\*:|diary append:|##\s*diary append).*"
)
_FAILURE_NOISE_PATTERNS = (
    "my apologies",
    "plan mode",
    "update_topic(",
    "reading additional input from stdin",
    "failed to refresh token",
    "i will write the content to the file",
)


def _query_rows(query: str, params: tuple | None = None) -> list[dict]:
    from core.database import execute_query

    rows = execute_query(query, params, fetch=True)
    return [dict(row) for row in (rows or [])]


def _strip_internal_messages(text: str) -> str:
    cleaned = _INTERNAL_CLI_RE.sub("", text).strip()
    return cleaned or text  # return original if everything was stripped


def _compress_persona_output(text: str, max_chars: int = 1200) -> str:
    cleaned = (text or "").strip()
    cleaned = _DIARY_APPEND_RE.sub("", cleaned).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    lines = [line.rstrip() for line in cleaned.splitlines()]
    trimmed: list[str] = []
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if any(pattern in lowered for pattern in _FAILURE_NOISE_PATTERNS):
            continue
        if re.fullmatch(r"(안녕하세요!?|감사합니다!?|좋습니다!?|여러분[, ]*)", stripped):
            continue
        if re.match(r"^(안녕하세요|감사합니다|좋아,|여러분,|법무팀장님, 안녕하세요|대표님, 그리고 팀원 여러분)", stripped):
            continue
        trimmed.append(line)
    cleaned = "\n".join(trimmed).strip()
    if len(cleaned) <= max_chars:
        return cleaned

    window = cleaned[:max_chars].rstrip()
    sentence_cut = max(window.rfind(token) for token in (". ", "! ", "? ", "\n- ", "\n"))
    if sentence_cut >= max_chars * 0.6:
        clipped = window[: sentence_cut + 1].strip()
        if clipped:
            return clipped

    fallback = window.rsplit(" ", 1)[0].strip()
    return (fallback or window).strip()


def _clip_line(text: str, max_chars: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    window = cleaned[:max_chars].rstrip()
    sentence_cut = max(window.rfind(token) for token in (". ", "! ", "? ", ", ", " "))
    if sentence_cut >= max_chars * 0.6:
        clipped = window[:sentence_cut].strip(" ,")
        if clipped:
            return clipped
    return window.strip(" ,")


def _enforce_persona_shape(persona: Persona, text: str) -> str:
    if persona.handle not in {"ledger", "kitt", "watchman", "jarvis", "vision", "friday"}:
        return text

    raw_lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    normalized: list[str] = []
    for line in raw_lines:
        line = re.sub(r"^\s*(#{1,6}|\*+|-+|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        parts = re.split(r"(?<=[.!?])\s+", line)
        normalized.extend(part.strip() for part in parts if part.strip())

    compact = []
    for line in normalized:
        lowered = line.lower()
        if lowered in {"허용", "보류", "금지", "리스크", "트리거", "숫자", "의미"}:
            continue
        compact.append(_clip_line(line, 120))
        if len(compact) >= (4 if persona.handle in {"vision", "friday"} else 3):
            break

    # 기존 레이블 제거 후 재부착 (LLM이 이미 "패키지: ..." 형식으로 쓸 경우 중복 방지)
    _all_labels = {"핵심 판단", "근거", "다음 액션", "패키지", "리스크", "상태", "병목", "수정"}
    def _strip_existing_label(line: str) -> str:
        m = re.match(r"^([\w ]+):\s*", line)
        if m and m.group(1).strip() in _all_labels:
            return line[m.end():].strip()
        return line

    if persona.handle == "jarvis":
        labels = ("핵심 판단", "근거", "다음 액션")
        compact = compact[:3]
        compact = [
            f"{labels[idx]}: {_clip_line(_strip_existing_label(line), 110)}"
            for idx, line in enumerate(compact)
            if line
        ]
    elif persona.handle == "vision":
        labels = ("패키지", "근거", "리스크", "다음 액션")
        compact = compact[:4]
        compact = [
            f"{labels[idx]}: {_clip_line(_strip_existing_label(line), 108)}"
            for idx, line in enumerate(compact)
            if line
        ]
    elif persona.handle == "friday":
        labels = ("상태", "병목", "수정", "다음 액션")
        compact = compact[:4]
        compact = [
            f"{labels[idx]}: {_clip_line(_strip_existing_label(line), 108)}"
            for idx, line in enumerate(compact)
            if line
        ]

    shaped = "\n".join(line for line in compact if line).strip()
    fallback_limit = 420 if persona.handle in {"vision", "friday"} else 360
    return shaped or _clip_line((text or "").strip(), fallback_limit)


def _persona_max_chars(persona: Persona) -> int:
    if persona.handle == "tars":
        return 500
    if persona.handle in {"c3po", "coach"}:
        return 420
    if persona.handle in {"kitt", "ledger", "watchman"}:
        return 360
    if persona.handle in {"vision", "friday"}:
        return 420
    if persona.handle == "scribe":
        return 520
    if persona.handle == "jarvis":
        return 420
    return 700


def _persona_style_instruction(persona: Persona) -> str:
    if persona.handle == "tars":
        return (
            " 추가 규칙: 구현 의견만 말하세요. 설계 감상, 배경 설명, 일반론 금지. "
            "반드시 `무엇을 바꿀지 -> 위험 -> 바로 할 테스트` 순서로 쓰세요. "
            "가능하면 파일명/테스트명/명령 1개씩만 짧게 넣고, 코드 패치 제안이 없으면 구현 가능/불가만 답하세요."
        )
    if persona.handle == "c3po":
        return (
            " 추가 규칙: 마케팅 메시지는 3줄 이내로 끝내세요. "
            "반드시 `타깃 -> 메시지 -> 채널`만 말하고, 형용사성 수식과 브랜드 미사여구는 금지합니다."
        )
    if persona.handle == "coach":
        return (
            " 추가 규칙: 교육 의견은 3줄 이내로 끝내세요. "
            "반드시 `현재 단계 -> 부족한 것 1개 -> 다음 훈련 1개`만 말하고, 격려 문구는 금지합니다."
        )
    if persona.handle == "ledger":
        return (
            " 추가 규칙: 숫자 없는 재무 감상 금지. "
            "반드시 `숫자 -> 의미 -> 한도/다음 액션` 순서로 3줄 이내로 쓰세요. "
            "각 줄은 120자 이하로 유지하고, 달러·원·개월·비율 중 최소 1개를 포함하세요. 장문 배경 설명은 금지합니다."
        )
    if persona.handle == "kitt":
        return (
            " 추가 규칙: 법무 의견은 3줄 이내로 끝내세요. "
            "반드시 `허용/보류/금지 -> 근거 법령 1개 -> 필요한 게이트/다음 액션` 순서로 쓰세요. "
            "각 줄은 120자 이하로 유지하세요. 면책성 서론과 장문 사례 설명은 금지합니다."
        )
    if persona.handle == "watchman":
        return (
            " 추가 규칙: 리스크 의견은 3줄 이내로 끝내세요. "
            "반드시 `리스크 -> 트리거 -> 완화/킬스위치` 순서로 쓰세요. "
            "각 줄은 120자 이하로 유지하세요. 과거 경위 설명과 도구 실행 로그 복붙은 금지합니다."
        )
    if persona.handle == "vision":
        return (
            " 추가 규칙: 상품 의견은 4줄 이내로 끝내세요. "
            "반드시 `패키지 -> 근거 -> 리스크 -> 다음 액션` 순서로 쓰세요. "
            "각 줄은 120자 이하로 유지하고, 미사여구와 장문 시장 설명은 금지합니다."
        )
    if persona.handle == "friday":
        return (
            " 추가 규칙: 운영 의견은 4줄 이내로 끝내세요. "
            "반드시 `상태 -> 병목 -> 수정 -> 다음 액션` 순서로 쓰세요. "
            "각 줄은 120자 이하로 유지하고, 회고성 배경 설명은 금지합니다."
        )
    if persona.handle == "jarvis":
        return (
            " 추가 규칙: 비서실장 정리는 3줄 이내로 끝내세요. "
            "반드시 `핵심 판단 -> 근거 -> 다음 액션` 순서로만 쓰세요. "
            "각 줄은 120자 이하로 유지하고, 인사말/배경 설명/반복/장문 dissent 나열은 금지합니다."
        )
    return ""


def format_persona_output(persona: Persona, text: str) -> str:
    text = _compress_persona_output(text, max_chars=_persona_max_chars(persona))
    return _enforce_persona_shape(persona, text)


def _build_live_company_context() -> str:
    try:
        if not OPENCLAW_STATUS_PATH.exists():
            return ""
        status = json.loads(OPENCLAW_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return ""

    runtime = status.get("runtime") or {}
    integrations = status.get("integrations") or {}
    integrity = status.get("integrity") or {}
    services = status.get("services") or {}

    risks: list[str] = []
    if not (integrations.get("postgres") or {}).get("available"):
        risks.append("Postgres degraded")
    if not services.get("ollama_11434"):
        risks.append("Ollama down")
    if not ((integrations.get("slack_bot") or {}).get("available") or (integrations.get("slack_webhook") or {}).get("available")):
        risks.append("Slack degraded")
    if not (integrations.get("notion") or {}).get("available"):
        risks.append("Notion degraded")
    if not integrity.get("ok", False):
        risks.append("Integrity failed")
    if runtime.get("capital_actions_enabled", "false").lower() != "true":
        risks.append("Capital actions gated off")

    top_risks = ", ".join(risks[:3]) if risks else "No active control-plane degradation detected"
    return (
        "[LIVE COMPANY CONTEXT]\n"
        f"- generated_at: {status.get('generated_at', 'unknown')}\n"
        f"- slack_phase: {runtime.get('slack_phase', 'unknown')}\n"
        f"- capital_actions_enabled: {runtime.get('capital_actions_enabled', 'false')}\n"
        f"- postgres_ok: {bool((integrations.get('postgres') or {}).get('available'))}\n"
        f"- notion_ok: {bool((integrations.get('notion') or {}).get('available'))}\n"
        f"- ollama_ok: {bool(services.get('ollama_11434'))}\n"
        f"- integrity_ok: {bool(integrity.get('ok'))}\n"
        f"- top_risks: {top_risks}\n"
    )


def _load_latest_open_ar() -> str:
    try:
        if not AR_TRACKER_PATH.exists():
            return ""
        entries = []
        for line in AR_TRACKER_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            status = str(payload.get("status", "")).lower()
            if status in {"open", "pending", "hold", "in_progress"}:
                entries.append(payload)
        if not entries:
            return ""
        latest = entries[-1]
        ar_id = latest.get("id", "-")
        owner = latest.get("owner", "-")
        status = latest.get("status", "-")
        title = " ".join(str(latest.get("title", "-")).split())[:140]
        due = latest.get("due") or latest.get("due_by") or "-"
        return f"- latest_ar: {ar_id} | owner={owner} | status={status} | due={due} | title={title}\n"
    except Exception:
        return ""


def _load_latest_orchestration_summary() -> str:
    try:
        if not ORCHESTRATION_RUNS_PATH.exists():
            return ""
        lines = [line.strip() for line in ORCHESTRATION_RUNS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return ""
        latest = json.loads(lines[-1])
        cid = latest.get("correlation_id", "-")
        ts = latest.get("ts", "-")
        personas = latest.get("personas") or []
        persona_count = len(personas)
        decision = " ".join(str(latest.get("decision", "")).split())
        decision = decision[:180]
        return (
            f"- latest_meeting: {cid} | ts={ts} | personas={persona_count}\n"
            f"- latest_decision: {decision}\n"
        )
    except Exception:
        return ""


def _load_goal_kpi_context() -> str:
    try:
        goal_rows = _query_rows(
            """
            SELECT
                g.id,
                g.title,
                g.target_metric,
                g.target_value,
                COALESCE(s.actual_value, g.current_value) AS current_value,
                g.unit,
                g.deadline,
                g.status,
                g.updated_at
            FROM strategic_goals g
            LEFT JOIN LATERAL (
                SELECT actual_value
                FROM goal_progress_snapshots
                WHERE goal_id = g.id
                ORDER BY snapshot_date DESC, created_at DESC
                LIMIT 1
            ) s ON TRUE
            WHERE status NOT IN ('completed', 'cancelled', 'archived')
            ORDER BY
                CASE
                    WHEN g.target_metric = 'paid_subscribers' THEN 0
                    WHEN g.target_metric = 'free_subscribers' THEN 1
                    ELSE 2
                END,
                g.updated_at DESC,
                g.id DESC
            LIMIT 2
            """
        )

        goal_lines: list[str] = []
        forecast_lines: list[str] = []
        for latest_goal in goal_rows:
            goal_id = latest_goal["id"]
            unit = latest_goal.get("unit") or ""
            metric = latest_goal.get("target_metric", "-")
            goal_lines.append(
                f"- latest_goal: #{goal_id} | metric={metric} | status={latest_goal.get('status', '-')} | "
                f"{str(latest_goal.get('title', '-')).strip()[:84]} | "
                f"{latest_goal.get('current_value', 0)}/{latest_goal.get('target_value', 0)} {unit}".rstrip()
            )
            forecast_rows = _query_rows(
                """
                SELECT probability_to_hit, recommended_mode, confidence, narrative
                FROM goal_forecasts
                WHERE goal_id = %s
                ORDER BY forecast_date DESC, created_at DESC
                LIMIT 1
                """,
                (goal_id,),
            )
            snapshot_rows = _query_rows(
                """
                SELECT health_status, variance
                FROM goal_progress_snapshots
                WHERE goal_id = %s
                ORDER BY snapshot_date DESC, created_at DESC
                LIMIT 1
                """,
                (goal_id,),
            )
            latest_forecast = forecast_rows[0] if forecast_rows else {}
            latest_snapshot = snapshot_rows[0] if snapshot_rows else {}
            probability = latest_forecast.get("probability_to_hit")
            probability_text = (
                f"{round(float(probability) * 100)}%" if probability is not None else "unknown"
            )
            mode = latest_forecast.get("recommended_mode", "-")
            health = latest_snapshot.get("health_status", "-")
            forecast_lines.append(
                f"- latest_forecast: goal=#{goal_id} | health={health} | p_hit={probability_text} | mode={mode}"
            )

        snap_rows = _query_rows(
            """
            SELECT snapshot_date, free_subscribers, paid_subscribers
            FROM subscriber_snapshots
            WHERE platform = 'substack'
            ORDER BY snapshot_date DESC
            LIMIT 2
            """
        )
        kpi_line = ""
        if snap_rows:
            latest = snap_rows[0]
            prev = snap_rows[1] if len(snap_rows) > 1 else {}
            free_now = int(latest.get("free_subscribers") or 0)
            paid_now = int(latest.get("paid_subscribers") or 0)
            free_delta = free_now - int(prev.get("free_subscribers") or 0)
            paid_delta = paid_now - int(prev.get("paid_subscribers") or 0)
            kpi_line = (
                f"- latest_kpi: {latest.get('snapshot_date')} | free={free_now} ({free_delta:+d}) | "
                f"paid={paid_now} ({paid_delta:+d})\n"
            )

        return ("\n".join(goal_lines + forecast_lines) + ("\n" if goal_lines or forecast_lines else "")) + kpi_line
    except Exception:
        return ""


# ── LLM invocation ──────────────────────────────────────────────────────────

def _find_cli(name: str) -> str:
    for candidate in (f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}", name):
        if candidate == name or Path(candidate).exists():
            return candidate
    return name


def _build_command(provider: str, prompt: str) -> list[str]:
    cli = _find_cli(provider)
    if provider == "claude":
        return [cli, "-p", prompt]
    if provider == "gemini":
        return [cli, "--skip-trust", "-p", prompt, "-o", "text"]
    if provider == "codex":
        return [cli, "exec", "--sandbox", "read-only", prompt]
    if provider == "copilot":
        return [cli, "-p", prompt, "--no-ask-user", "--silent"]
    raise ValueError(f"Unknown provider: {provider}")


def call_llm(provider: str, prompt: str) -> tuple[str, bool]:
    """Run a provider CLI with a fully-formed prompt. Returns (text, ok)."""
    command = _build_command(provider, prompt)
    # .env의 ANTHROPIC_API_KEY를 환경변수로 명시 전달 (SSH 세션에서 Keychain 미접근 대비)
    from dotenv import dotenv_values
    env_file_vals = dotenv_values(PROJECT_ROOT / ".env")
    run_env = {
        **os.environ,
        "PATH": f"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{os.environ.get('PATH', '')}",
    }
    for key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        val = env_file_vals.get(key) or os.environ.get(key, "")
        if val:
            run_env[key] = val
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=PROVIDER_TIMEOUT,
            check=False,
            env=run_env,
        )
    except Exception as exc:  # noqa: BLE001
        return f"({provider} 호출 실패: {exc})", False

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0 or not stdout:
        return f"({provider} 응답 없음: {stdout or stderr or completed.returncode})", False
    stdout = _compress_persona_output(_strip_internal_messages(stdout))
    return stdout, True


def _build_prompt(persona: Persona, task: str, correlation_id: str, extra_context: str = "") -> str:
    system = ""
    if persona.system_prompt_path.exists():
        system = persona.system_prompt_path.read_text(encoding="utf-8").strip()
    context_block = f"\n[참고 — 다른 팀 발언]\n{extra_context}\n" if extra_context else ""
    live_company_context = (
        _build_live_company_context()
        + _load_latest_open_ar()
        + _load_latest_orchestration_summary()
        + _load_goal_kpi_context()
    )
    return (
        f"{system}\n\n"
        f"{live_company_context}\n"
        "─────────────────────────────────────\n"
        f"[correlation_id: {correlation_id}]\n"
        f"이건 #{persona.team_short} / #회의실 에 올라갈 발언입니다. "
        "【절대 규칙 — 위반 시 발언 무효】 전문용어·영어 약어를 쓸 때는 반드시 바로 뒤에 괄호로 "
        "①영문 풀네임, ②한국어 뜻, ③쉬운 설명 순으로 붙이세요. "
        "형식: 약어(English Full Name, 한국어 — 쉬운 설명). "
        "예) BEP(Break-Even Point, 손익분기점 — 수익과 비용이 딱 같아지는 지점), "
        "CTR(Click-Through Rate, 클릭률 — 광고 100번 노출 중 몇 번 클릭했는지), "
        "CAC(Customer Acquisition Cost, 고객 획득 비용 — 고객 1명 데려오는 데 드는 총 비용), "
        "ARR(Annual Recurring Revenue, 연간 반복 매출 — 1년간 꾸준히 들어오는 구독 수익), "
        "MDD(Maximum Drawdown, 최대 낙폭 — 고점 대비 가장 많이 떨어진 비율), "
        "LTV(Lifetime Value, 고객 생애 가치 — 고객 1명이 평생 가져다주는 총 수익), "
        "KPI(Key Performance Indicator, 핵심 성과 지표 — 목표 달성을 측정하는 숫자), "
        "WTP(Willingness To Pay, 지불 의향 — 고객이 실제로 돈을 낼 의향이 있는지). "
        "대표님·부대표님은 마케팅/투자 비전문가이므로 모든 용어를 초등학생도 이해할 수 있게 설명하세요. "
        "Charter §4.3대로 **공손한 존댓말 구어체**로만 답하세요. "
        "**반말 금지**, **보고서 문체 금지**, **인사말/감탄사/감사 멘트 금지**, **메타 설명 금지**, **자기소개 금지**. "
        "다른 팀을 언급할 때는 'Friday님', 'KITT님'처럼 반드시 '님'을 붙입니다. "
        "반드시 **새로운 정보만** 말하세요. 이미 나온 말을 반복하지 마세요. "
        "형식은 최대 5개 bullet, bullet당 최대 2문장, 전체 600자 안쪽을 목표로 하세요. "
        "가능하면 `핵심 판단 -> 근거 -> 다음 액션` 순서로 짧게 말하세요. "
        "근거(지표/법령 등)는 대화 속에 짧게 녹이고, 추정이면 confidence만 짧게 붙이세요."
        f"{_persona_style_instruction(persona)}"
        f"{context_block}\n"
        f"[TASK]\n{task}\n"
    )


_OOC_PATTERNS = re.compile(
    r"(YouTube|URL|링크|동영상|영상).{0,30}(열람|접근|분석|확인|볼\s*수).{0,20}(없|어렵|불가)|"
    r"(AI|에이전트|저는).{0,20}(직접|URL|링크).{0,20}(없|어렵|불가)|"
    r"텍스트.{0,20}(형태로|로)\s*(주시면|전달)",
    re.IGNORECASE,
)


def call_persona(
    persona: Persona,
    task: str,
    correlation_id: str,
    extra_context: str = "",
) -> tuple[str, bool]:
    """Build the persona prompt and call its primary LLM. Returns (text, ok)."""
    prompt = _build_prompt(persona, task, correlation_id, extra_context)
    text, ok = call_llm(persona.provider, prompt)
    if ok:
        # OOC(책임 회피) 감지 시 재시도 — URL 분석 불가 주장 금지
        if _OOC_PATTERNS.search(text):
            retry_prompt = (
                f"{prompt}\n\n"
                "[중요] 이전 응답에 'URL/링크에 접근할 수 없다'는 표현이 포함됐습니다. "
                "이는 금지된 OOC(책임 회피) 발언입니다. "
                "URL 내용을 직접 열람하지 못해도, 주제와 맥락을 바탕으로 최선의 분석을 제시하세요. "
                "'할 수 없다'는 표현 없이 바로 본론으로 답변하세요."
            )
            text, ok = call_llm(persona.provider, retry_prompt)
        if ok:
            text = format_persona_output(persona, text)
    return text, ok


# ── Slack + memory ────────────────────────────────────────────────────────────

def post_opinion(persona: Persona, text: str, channel_id: str | None = None) -> bool:
    """Post a persona's message to its home channel. Returns True if posted."""
    channel_id = channel_id or (os.getenv(persona.channel_env, "") if persona.channel_env else "")
    if not channel_id:
        return False
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured")
    body = f"*{persona.display}*:\n{to_slack_mrkdwn(text)}"
    resp = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"channel": channel_id, "text": body[:3900]},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack postMessage failed: {data.get('error')}")
    return True


def append_diary(persona: Persona, correlation_id: str, task: str, posted: bool, ok: bool) -> None:
    """Append a factual run-record (not a fabricated reflection). Charter §8."""
    if not persona.memory_path.exists():
        return
    today = datetime.now().strftime("%Y-%m-%d")
    task_line = " ".join(task.split())[:80]
    status = "posted" if posted else ("llm_ok_no_post" if ok else "failed")
    entry = (
        f"\n## {today} {correlation_id} {task_line}\n"
        f"- what_i_did: run_persona 실행 → 채널 발언 ({status})\n"
        f"- what_worked: (자기평가 미작성)\n"
        f"- what_failed: (자기평가 미작성)\n"
        f"- lesson: (자기평가 미작성 — auto run-record)\n"
        f"- confidence: {'medium' if ok else 'low'}\n"
    )
    with persona.memory_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single persona on a task.")
    parser.add_argument("handle", help="persona handle (e.g. friday, kitt, jarvis)")
    parser.add_argument("--task", required=True, help="the question/task for the persona")
    parser.add_argument("--correlation-id", default=None)
    parser.add_argument("--dry-run", action="store_true", help="validate wiring; no LLM call, no post")
    parser.add_argument("--no-post", action="store_true", help="call LLM but skip Slack post")
    args = parser.parse_args()

    persona = get_persona(args.handle)
    correlation_id = args.correlation_id or f"persona-{uuid.uuid4().hex[:8]}"

    if persona.frozen:
        print(f"BLOCKED: '{persona.handle}'는 frozen persona (Charter §2.3, 첫 paid subscriber까지 동결).")
        return 2

    channel_id = os.getenv(persona.channel_env, "") if persona.channel_env else ""

    if args.dry_run:
        print(f"[dry-run] persona={persona.display}")
        print(f"[dry-run] provider={persona.provider} escalation={persona.escalation}")
        print(f"[dry-run] active={persona.active} channel_env={persona.channel_env} -> {channel_id or '(unset)'}")
        print(f"[dry-run] system_prompt exists: {persona.system_prompt_path.exists()}")
        print(f"[dry-run] correlation_id={correlation_id}")
        print("[dry-run] OK — 실제 호출/포스트 없음.")
        return 0

    if not persona.active:
        print(f"BLOCKED: '{persona.handle}'는 아직 inactive. registry에서 active=True + 채널 생성 후 실행.")
        return 2

    output, ok = call_persona(persona, args.task, correlation_id)
    print(f"[{persona.display}] provider={persona.provider} ok={ok} cid={correlation_id}")

    posted = False
    if ok and not args.no_post:
        posted = post_opinion(persona, output)
        if posted:
            print(f"[{persona.display}] posted to {persona.channel_env} ({channel_id})")
        else:
            print(f"WARN: {persona.channel_env} 미설정 — 포스트 생략.")

    append_diary(persona, correlation_id, args.task, posted, ok)
    print(f"--- {persona.display} output ---\n{output[:1500]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
