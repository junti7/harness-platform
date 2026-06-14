"""Gate commitment tracker — 회의에서 약속한 게이트의 이행 여부를 추적·보고.

Flow:
  1. orchestrator가 회의 후 extract_gates()를 호출 → gate_tracker.jsonl에 저장
  2. 매일 오전 9시 check_gates_and_report()가 실행 → 담당 페르소나에게 현황 보고 요청
  3. 페르소나 답변을 CEO #exec-president-decisions 채널에 자동 보고
  4. 게이트 완료 시 update_gate()로 상태 갱신

Gate ownership:
  legal_review_approve   → kitt
  red_team_clear         → watchman
  pre_mortem_approve     → vision
  qa_clear               → scribe
  vp_content_review      → (인간, Slack DM으로 VP에게 알림)
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import httpx

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE_LOG_PATH = PROJECT_ROOT / "docs" / "reports" / "gate_tracker.jsonl"

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
EXEC_CHANNEL = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")
VP_USER_ID = os.getenv("SLACK_VP_USER_ID", "")

# 게이트 타입 → 담당 페르소나 핸들 (None = 인간)
GATE_OWNERS: dict[str, str | None] = {
    "legal_review_approve": "kitt",
    "red_team_clear": "watchman",
    "pre_mortem_approve": "vision",
    "qa_clear": "scribe",
    "vp_content_review": None,  # 인간(부대표)
}

# 게이트 타입별 기본 기한 (영업일)
GATE_DUE_DAYS: dict[str, int] = {
    "legal_review_approve": 4,
    "red_team_clear": 1,
    "pre_mortem_approve": 2,
    "qa_clear": 1,
    "vp_content_review": 2,
}

# 게이트 타입별 점검 요청 메시지
GATE_CHECK_PROMPTS: dict[str, str] = {
    "legal_review_approve": (
        "메일리·스티비 약관 legal review 진행 현황을 보고해 주세요. "
        "현재까지 완료된 항목(결제 수수료 / 구독자 소유권 / 환불 정책 / 저작권), "
        "남은 항목, 예상 완료 시점을 구체적으로 알려주세요. "
        "완료됐다면 최종 결론(통과/보류/조건부 통과)과 핵심 리스크를 명시해 주세요."
    ),
    "red_team_clear": (
        "메일리·스티비 플랫폼 전환 결정에 대한 cross-LLM red team 검증(Claude+Gemini+Codex 2-of-3) 진행 현황을 보고해 주세요. "
        "언제 시작할 수 있는지, 완료 예상 시점은 언제인지 알려주세요."
    ),
    "pre_mortem_approve": (
        "메일리+스티비 플랫폼 전환 결정에 대한 Pre-Mortem(최악 시나리오 3개 이상) 작성 현황을 보고해 주세요. "
        "완료됐다면 핵심 worst-case 시나리오와 mitigation을 요약해 주세요."
    ),
    "qa_clear": (
        "#003 이슈 QA 검증 현황을 보고해 주세요. "
        "콘텐츠가 draft 단계인지 QA 가능 단계인지, 시작할 수 있는 시점은 언제인지 알려주세요."
    ),
}


def _load_gates() -> list[dict]:
    if not GATE_LOG_PATH.exists():
        return []
    gates = []
    for line in GATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                gates.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return gates


def _save_gate(gate: dict) -> None:
    GATE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GATE_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(gate, ensure_ascii=False) + "\n")


def _rewrite_gates(gates: list[dict]) -> None:
    # 원자적 재작성: 전체를 temp 파일에 쓰고 fsync 후 os.replace 로 한 번에 교체한다.
    # 비원자적 open("w") 는 재작성 도중 "유효한 JSONL prefix"(앞줄만 완성) 상태가 잠깐 생겨,
    # 이를 읽는 쪽(decision-record-sync 의 _is_stable)이 잘린 원장을 정상으로 오인해 커밋할 수 있다.
    # os.replace 는 POSIX 상 원자적이라 읽는 쪽은 항상 옛 파일 또는 새 파일만 본다(중간 절단본 없음).
    GATE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(GATE_LOG_PATH.parent), prefix=".gate_tracker_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for g in gates:
                fh.write(json.dumps(g, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, GATE_LOG_PATH)  # 원자적 교체
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _post_slack(channel: str, text: str) -> None:
    if not SLACK_BOT_TOKEN or not channel:
        return
    httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": channel, "text": text[:3900]},
        timeout=10,
    )


def _parse_gate_type(text: str) -> str | None:
    """Decision Card 텍스트에서 게이트 타입 추출."""
    for gate_type in GATE_OWNERS:
        pattern = gate_type.replace("_", r"[_\s]?")
        if re.search(pattern, text, re.IGNORECASE):
            return gate_type
    if re.search(r"vp.*review|부대표.*검토|vice.?president", text, re.IGNORECASE):
        return "vp_content_review"
    return None


def extract_gates(decision_text: str, correlation_id: str, order: str) -> list[dict]:
    """Decision Card에서 미이행 게이트를 파싱하여 저장. 새 게이트 리스트 반환."""
    # 이미 저장된 게이트 (중복 방지)
    existing = {g["gate_type"] + g["correlation_id"] for g in _load_gates()}

    # 게이트 섹션 파싱 — "❌" 표시된 행 추출
    gate_section = re.search(r"막힌 게이트.*?(?=\n#{1,3} |\Z)", decision_text, re.DOTALL | re.IGNORECASE)
    block = gate_section.group(0) if gate_section else decision_text

    new_gates = []
    for line in block.splitlines():
        if "❌" not in line and "미발급" not in line and "미수행" not in line and "미실행" not in line and "미작성" not in line:
            continue
        gate_type = _parse_gate_type(line)
        if not gate_type:
            continue
        key = gate_type + correlation_id
        if key in existing:
            continue

        due_days = GATE_DUE_DAYS.get(gate_type, 3)
        due_by = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")

        gate: dict[str, Any] = {
            "id": f"gate-{uuid.uuid4().hex[:8]}",
            "correlation_id": correlation_id,
            "gate_type": gate_type,
            "owner": GATE_OWNERS.get(gate_type),
            "order_summary": order[:120],
            "status": "pending",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "due_by": due_by,
            "last_checked_at": None,
            "completed_at": None,
            "last_report": None,
        }
        _save_gate(gate)
        new_gates.append(gate)
        print(f"[gate_tracker] 게이트 등록: {gate_type} (due {due_by}) [{correlation_id}]")

    return new_gates


def update_gate(gate_id: str, status: str, report: str = "") -> bool:
    """게이트 상태 갱신. status: pending | in_progress | completed | overdue"""
    gates = _load_gates()
    updated = False
    for g in gates:
        if g["id"] == gate_id:
            g["status"] = status
            g["last_report"] = report[:500] if report else g.get("last_report")
            g["last_checked_at"] = datetime.now().isoformat(timespec="seconds")
            if status == "completed":
                g["completed_at"] = datetime.now().isoformat(timespec="seconds")
            updated = True
            break
    if updated:
        _rewrite_gates(gates)
    return updated


def check_gates_and_report() -> None:
    """미이행 게이트 점검 → 담당 페르소나에게 현황 질의 → CEO 채널 보고."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.run_persona import call_persona
    from agents.registry import get_persona

    gates = _load_gates()
    pending = [g for g in gates if g["status"] in ("pending", "in_progress")]

    if not pending:
        print("[gate_tracker] 미이행 게이트 없음.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    report_lines = [f"*Jarvis(비서실장)* — 게이트 이행 현황 점검 ({today})\n"]

    for gate in pending:
        gate_type = gate["gate_type"]
        owner_handle = gate["owner"]
        due_by = gate["due_by"]
        cid = gate["correlation_id"]
        is_overdue = today > due_by

        status_emoji = "🔴 지연" if is_overdue else "🟡 진행중"

        if owner_handle is None:
            # VP는 인간 — Slack DM으로 알림
            if VP_USER_ID and is_overdue:
                _post_slack(VP_USER_ID, f"부대표님, `{gate_type}` 게이트 검토 기한({due_by})이 지났습니다. [{cid}]")
            report_lines.append(f"• {status_emoji} `{gate_type}` — 부대표님 검토 대기 (기한: {due_by}) [{cid}]")
            continue

        # 페르소나에게 현황 질의
        prompt = GATE_CHECK_PROMPTS.get(
            gate_type,
            f"`{gate_type}` 게이트 이행 현황을 간략히 보고해 주세요. 완료 여부, 남은 작업, 예상 완료 시점을 알려주세요."
        )
        prompt += f"\n\n[관련 회의 ID: {cid} | 약속한 주제: {gate['order_summary']}]"

        try:
            persona = get_persona(owner_handle)
            text, ok = call_persona(persona, prompt, f"gate-check-{gate['id'][:8]}")
            report = text[:400] if ok else "(응답 없음)"
        except Exception as exc:
            report = f"(오류: {exc})"

        # 게이트 기록 업데이트
        update_gate(gate["id"], "in_progress" if not is_overdue else "overdue", report)

        report_lines.append(
            f"\n{'🔴 *지연*' if is_overdue else '🟡 *진행중*'} `{gate_type}` — 기한: {due_by} [{cid}]\n"
            f"담당: {owner_handle}님 보고:\n> {report[:300]}"
        )

    summary = "\n".join(report_lines)
    _post_slack(EXEC_CHANNEL, summary)
    print(f"[gate_tracker] CEO 채널 보고 완료 — {len(pending)}개 게이트 점검")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_gates_and_report()
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        gates = _load_gates()
        for g in gates:
            print(json.dumps(g, ensure_ascii=False, indent=2))
    else:
        print("Usage: python gate_tracker.py check | list")
