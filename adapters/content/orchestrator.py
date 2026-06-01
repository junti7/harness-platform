"""Jarvis orchestration loop — the META environment engine (Charter §4.4).

Flow for a single CEO order:
  1. decompose  — Jarvis (Claude) reads the order + active-persona roster and
                  assigns a tailored sub-task to each relevant team.
  2. round 0    — each assigned persona posts an opinion to its home channel.
  3. convene    — opinions are gathered into #회의실 and personas debate over
                  multiple rounds (구어체), capped at MAX_CC_HOPS (Charter §5).
  4. synthesize — Jarvis writes a consensus/dissent summary and a CEO decision
                  card to #exec-president-decisions.
  5. record     — the run (correlation_id, cost, decision) is appended to
                  docs/reports/orchestration_runs.jsonl.

A per-order CostGuard enforces the $2.00 cap (Charter §5). Costs are *estimates*
(the CLIs do not return token counts); the guard stops new calls before the cap
is crossed and records that it stopped.

Persona ≠ Gate (Charter §3): nothing here records red_team_clear / legal_review_
approve / qa_clear. Those gates still require the separate cross-LLM procedures.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from adapters.content.slack_format import to_slack_mrkdwn
from agents.registry import Persona, get_active_personas, get_persona
from scripts.run_persona import append_diary, call_llm, call_persona, format_persona_output, post_opinion
from scripts.llm_fallback_manager import get_current_provider, get_fallback_info
from scripts.notion_minutes import (
    build_minutes_blocks_from_decision_card as _build_minutes_blocks,
    save_minutes as _save_notion_minutes,
)
from scripts.gate_tracker import extract_gates as _extract_gates
from scripts.ar_tracker import extract_ars_from_decision as _extract_ars

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_LOG_PATH = PROJECT_ROOT / "docs/reports/orchestration_runs.jsonl"
NOTION_MINUTES_RUN_LOG_PATH = PROJECT_ROOT / "docs/reports/notion_minutes_runs.jsonl"

# Deterministic .env loading: Slack/launchd/CLI entrypoints may have varying CWD/call stacks.
load_dotenv(dotenv_path=str(PROJECT_ROOT / ".env"), override=True)

MAX_CC_HOPS = int(os.getenv("ORCHESTRATION_MAX_CC_HOPS", "2"))
MAX_CC_HOPS = max(1, min(MAX_CC_HOPS, 2))  # Strict ceiling of 2 hops
DEFAULT_ROUNDS = min(int(os.getenv("ORCHESTRATION_DEFAULT_ROUNDS", "2")), MAX_CC_HOPS)


# Rough per-call cost estimates (CLIs don't report tokens). USD.
_PROVIDER_COST = {"claude": 0.12, "gemini": 0.05, "codex": 0.10, "copilot": 0.02}


def _orchestration_provider_mode() -> str:
    return (os.getenv("ORCHESTRATION_PROVIDER_MODE", "auto") or "auto").strip().lower()


def _jarvis_reasoning_persona() -> Persona:
    return get_persona("jarvis")


def _jarvis_reasoning_provider() -> str:
    jarvis = _jarvis_reasoning_persona()
    mode = _orchestration_provider_mode()
    if mode == "force_gemini":
        return "gemini"
    if mode == "force_primary":
        return jarvis.provider
    return get_current_provider(jarvis.handle, jarvis.provider, jarvis.fallback_provider)


class CostStop(Exception):
    """Raised when the per-order cost cap would be exceeded."""


class CostGuard:
    def __init__(self, cap_usd: float):
        self.cap = cap_usd
        self.spent = 0.0
        self.calls = 0
        self.stopped = False

    def charge(self, provider: str, force: bool = False) -> None:
        """force=True면 cap을 넘어도 청구 (최종 정리·CEO 카드는 항상 보장)."""
        est = _PROVIDER_COST.get(provider, 0.12)
        if not force and self.spent + est > self.cap:
            self.stopped = True
            raise CostStop(f"per-order cost cap ${self.cap:.2f} 도달 (지출 추정 ${self.spent:.2f})")
        self.spent += est
        self.calls += 1


def _conference_channel() -> str:
    return os.getenv("SLACK_CHANNEL_CONFERENCE_ROOM", "")


def _exec_channel() -> str:
    return os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")


def _post_raw(channel_id: str, text: str) -> bool:
    """Post plain text (used for Jarvis kickoff/synthesis in shared channels)."""
    if not channel_id:
        return False
    import httpx

    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured")
    resp = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"channel": channel_id, "text": to_slack_mrkdwn(text)[:3900]},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack postMessage failed: {data.get('error')}")
    return True


def _extract_json(text: str) -> dict | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if not candidate:
        start, end = text.find("{"), text.rfind("}")
        candidate = text[start : end + 1] if start != -1 and end > start else None
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _decompose(order: str, correlation_id: str, guard: CostGuard) -> list[tuple[Persona, str]]:
    """Jarvis assigns sub-tasks to relevant active personas. Fallback: all active."""
    candidates = [p for p in get_active_personas() if p.handle != "jarvis"]
    roster = "\n".join(f"- {p.handle}: {p.team_short} — {p.role}" for p in candidates)
    prompt = (
        "너는 Harness 비서실장 Jarvis다. 아래 CEO order를 받아서, 어떤 팀(persona)에게 "
        "무슨 sub-task를 줄지 정한다. 관련 없는 팀은 빼라.\n\n"
        f"[CEO ORDER]\n{order}\n\n"
        f"[가용 팀 (active personas)]\n{roster}\n\n"
        "아래 JSON만 출력해라. 다른 말 금지:\n"
        '{"assignments": [{"persona": "<handle>", "task": "<그 팀에게 줄 구체 sub-task>"}], '
        '"rationale": "<왜 이렇게 나눴는지 한 줄>"}'
    )
    reasoning_provider = _jarvis_reasoning_provider()
    jarvis = _jarvis_reasoning_persona()
    guard.charge(reasoning_provider)
    out, ok = call_llm(reasoning_provider, prompt, jarvis.handle, jarvis)
    parsed = _extract_json(out) if ok else None

    if parsed and isinstance(parsed.get("assignments"), list):
        result: list[tuple[Persona, str]] = []
        for a in parsed["assignments"]:
            try:
                p = get_persona(a["persona"])
            except (KeyError, TypeError):
                continue
            if p.active and p.handle != "jarvis":
                result.append((p, str(a.get("task", order)).strip() or order))
        if result:
            return result
    # Fallback: every active non-jarvis persona gets the raw order.
    return [(p, order) for p in candidates]


def _synthesize(order: str, transcript: list[dict], correlation_id: str, guard: CostGuard) -> str:
    convo = "\n".join(f"[{t['persona']}] {t['text']}" for t in transcript)
    prompt = (
        "당신은 Harness 비서실장 Jarvis입니다. 아래는 한 CEO 지시에 대한 팀별 회의실 토론입니다. "
        "이를 CEO 모바일 decision card로 정리해 주세요. **공손한 존댓말**로, 팀을 언급할 땐 'OO님' 호칭. 구조적으로:\n"
        "1) 한 줄 요약\n2) 합의된 점(consensus)\n3) 미합의/이견(dissent)\n"
        "4) 권고 액션\n5) 막힌 게이트(있으면). Persona 의견은 게이트 충족이 아님을 명심.\n\n"
        f"[CEO ORDER]\n{order}\n\n[회의실 토론]\n{convo}\n"
    )
    reasoning_provider = _jarvis_reasoning_provider()
    jarvis = _jarvis_reasoning_persona()
    guard.charge(reasoning_provider, force=True)  # 최종 정리는 cap 넘어도 보장
    out, ok = call_llm(reasoning_provider, prompt, jarvis.handle, jarvis)
    if not ok:
        return "(synthesis 실패 — 회의실 transcript 참조)"
    return format_persona_output(get_persona("jarvis"), out)


def _simplify_minutes(order: str, decision: str) -> str:
    """Rewrite Decision Card as simple meeting minutes (초등학생 수준, 인사이트 중심)."""
    prompt = (
        "당신은 Harness 비서실장 Jarvis입니다. 아래 회의 결과를 Notion 회의록으로 정리해 주세요.\n"
        "규칙: (1) 초등학생도 이해할 수 있는 쉬운 말, (2) 최대한 짧고 간결하게, "
        "(3) 가장 중요한 인사이트(핵심 결론 1~2개)를 ## 핵심 인사이트 섹션으로 맨 앞에, "
        "(4) ## 오늘 결정한 것, ## 아직 못 정한 것, ## 다음에 할 일 섹션 포함. "
        "존댓말 구어체. 전문 용어는 괄호 안에 쉬운 말 병기.\n\n"
        f"[회의 주제]\n{order}\n\n[회의 결과]\n{decision}\n"
    )
    reasoning_provider = _jarvis_reasoning_provider()
    jarvis = _jarvis_reasoning_persona()
    out, ok = call_llm(reasoning_provider, prompt, jarvis.handle, jarvis)
    return out if ok else decision


def _record_run(record: dict) -> None:
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _record_notion_minutes_run(payload: dict) -> None:
    """Append-only audit trail for Notion minutes saves (success or failure)."""
    NOTION_MINUTES_RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NOTION_MINUTES_RUN_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def respond_as_persona(
    handle: str,
    question: str,
    channel_id: str | None = None,
    correlation_id: str | None = None,
    post: bool = True,
) -> dict:
    """A single persona answers a CEO question, posted to the given channel.

    Used when the CEO addresses someone by name in a meeting (e.g. 'Friday님 ...').
    """
    persona = get_persona(handle)
    cid = correlation_id or f"mention-{uuid.uuid4().hex[:8]}"
    text, ok = call_persona(persona, question, cid)
    if post:
        post_opinion(persona, text, channel_id=channel_id or None)
    append_diary(persona, cid, question, posted=post, ok=ok)
    return {"persona": persona.display, "text": text, "ok": ok, "correlation_id": cid}


def orchestrate(
    order: str,
    correlation_id: str | None = None,
    *,
    rounds: int = DEFAULT_ROUNDS,
    dry_run: bool = False,
    post: bool = True,
) -> dict:
    correlation_id = correlation_id or f"orch-{uuid.uuid4().hex[:8]}"
    rounds = max(0, min(rounds, MAX_CC_HOPS))
    cap = float(os.getenv("ORCHESTRATION_PER_ORDER_COST_LIMIT_USD", "2.00"))
    guard = CostGuard(cap)
    room = _conference_channel()
    transcript: list[dict] = []
    cost_stopped = False

    if dry_run:
        candidates = [p for p in get_active_personas() if p.handle != "jarvis"]
        return {
            "correlation_id": correlation_id,
            "dry_run": True,
            "would_involve": [p.display for p in candidates],
            "rounds": rounds,
            "cost_cap": cap,
            "conference_channel": room or "(unset)",
            "exec_channel": _exec_channel() or "(unset)",
        }

    try:
        # 1. decompose
        assignments = _decompose(order, correlation_id, guard)
        # Policy: CFO(ledger) attends every meeting (if active).
        try:
            from agents.registry import get_persona

            ledger = get_persona("ledger")
            if ledger.active and all(p.handle != "ledger" for p, _ in assignments):
                assignments.append((ledger, "CFO 관점: 비용/리스크/재무 영향 중심으로 점검해 주세요."))
        except Exception:
            pass
        if post and room:
            who = ", ".join(f"{p.name}님" for p, _ in assignments)
            _post_raw(room, f"*Jarvis(비서실장)*: CEO 지시 받았습니다. 이번 건은 {who} 모시고 함께 보겠습니다.\n> {order}")

        # 2. round 0 — each persona's initial opinion to home channel + 회의실
        for persona, subtask in assignments:
            guard.charge(persona.provider)
            text, ok = call_persona(persona, subtask, correlation_id, check_lane_b_budget=True)
            if not ok and "Lane B 일시 정지" in text:
                if post and room:
                    _post_raw(room, f"*Jarvis(비서실장)*: ⚠️ Lane B 예산 임계값 도달 — {persona.display}님 의견 생략됩니다.")
                continue
            if post:
                post_opinion(persona, text)  # home channel
                if room:
                    post_opinion(persona, text, channel_id=room)  # mirror into 회의실
            transcript.append({"persona": persona.display, "round": 0, "text": text, "ok": ok})
            append_diary(persona, correlation_id, subtask, posted=post, ok=ok)

        # 3. debate rounds — each persona reacts to others (구어체) in 회의실
        for rnd in range(1, rounds + 1):
            for persona, _ in assignments:
                others = "\n".join(
                    f"[{t['persona']}] {t['text']}" for t in transcript if t["persona"] != persona.display
                )
                react_task = (
                    "위 다른 팀 발언을 보시고, 본인 팀 관점에서 동의/반박/보완할 점을 공손한 존댓말 구어체로 짧게 말씀해 주세요. "
                    "다른 팀을 언급할 때는 'OO님'으로 호칭합니다. 반말 금지. 이미 한 말 반복 금지, 새로운 포인트만."
                )
                guard.charge(persona.provider)
                text, ok = call_persona(persona, react_task, correlation_id, extra_context=others, check_lane_b_budget=True)
                if not ok and "Lane B 일시 정지" in text:
                    continue
                if post and room:
                    post_opinion(persona, text, channel_id=room)
                transcript.append({"persona": persona.display, "round": rnd, "text": text, "ok": ok})

    except CostStop as exc:
        cost_stopped = True
        if post and room:
            _post_raw(room, f"*Jarvis(비서실장)*: ⛔ {exc} — 여기서 토론을 멈추고 정리하겠습니다.")

    # 4. synthesize → CEO decision card
    decision = _synthesize(order, transcript, correlation_id, guard) if transcript else "(no transcript)"
    if post:
        if room:
            _post_raw(room, f"*Jarvis(비서실장)* 정리:\n{decision}")
        if _exec_channel():
            _post_raw(_exec_channel(), f"*Jarvis(비서실장)* — CEO Decision Card [{correlation_id}]:\n{decision}")

    # 5. record
    persona_names = [p.display for p, _ in assignments] if transcript else []
    record = {
        "correlation_id": correlation_id,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "order": order,
        "personas": persona_names,
        "jarvis_reasoning_provider": _jarvis_reasoning_provider(),
        "jarvis_fallback_state": get_fallback_info("jarvis"),
        "rounds": rounds,
        "turns": len(transcript),
        "estimated_cost_usd": round(guard.spent, 3),
        "llm_calls": guard.calls,
        "cost_stopped": cost_stopped,
        "decision": decision,
    }
    _record_run(record)

    # 6. 미이행 게이트 추출 및 tracker 등록
    if transcript:
        try:
            new_gates = _extract_gates(decision, correlation_id, order)
            if new_gates and post and _exec_channel():
                gate_names = ", ".join(f"`{g['gate_type']}`" for g in new_gates)
                _post_raw(
                    _exec_channel(),
                    f"*Jarvis(비서실장)*: 📌 {len(new_gates)}개 게이트가 이행 추적 목록에 등록됐습니다.\n"
                    f"{gate_names}\n매일 오전 9시에 담당 팀에게 현황을 확인하고 보고드리겠습니다.",
                )
        except Exception as exc:
            print(f"[orchestrate] 게이트 추출 실패: {exc}")

    # 7. 권고 액션 → AR 자동 등록
    if transcript:
        try:
            new_ars = _extract_ars(decision, correlation_id)
            if new_ars and post and _exec_channel():
                _post_raw(
                    _exec_channel(),
                    f"*Jarvis(비서실장)*: 📋 {len(new_ars)}개 AR(Action Required)이 등록됐습니다.\n"
                    + "\n".join(f"• [{a['id']}] {a['title']} (담당: {a['owner']}님, 기한: {a['due_by']})" for a in new_ars),
                )
        except Exception as exc:
            print(f"[orchestrate] AR 추출 실패: {exc}")

    # 8. Notion 회의록 저장 (Slack 포스트 여부와 무관하게 내부 기록은 남긴다)
    if transcript:
        try:
            blocks = _build_minutes_blocks(decision, ts=record.get("ts"), correlation_id=correlation_id, limit=90)
            notion_url = _save_notion_minutes(
                correlation_id=correlation_id,
                order=order,
                personas=persona_names,
                minutes_text="",
                cost_usd=guard.spent,
                minutes_blocks=blocks,
            )
            _record_notion_minutes_run(
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "correlation_id": correlation_id,
                    "notion_url": notion_url,
                    "ok": bool(notion_url),
                }
            )
            if post and notion_url and _exec_channel():
                _post_raw(_exec_channel(), f"*Jarvis(비서실장)*: 📒 회의록이 Notion에 저장됐습니다.\n{notion_url}")
        except Exception as exc:
            _record_notion_minutes_run(
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "correlation_id": correlation_id,
                    "notion_url": None,
                    "ok": False,
                    "error": str(exc),
                }
            )
            print(f"[orchestrate] Notion 회의록 저장 실패: {exc}")

    return record
