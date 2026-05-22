"""AR (Action Required) Tracker — 비서실장 일일 이행 점검.

Usage:
  python ar_tracker.py check          # 일일 점검 실행
  python ar_tracker.py list           # 전체 AR 목록
  python ar_tracker.py list --open    # 미완 AR만
  python ar_tracker.py complete <id> "완료 메모"
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import httpx

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AR_LOG_PATH = PROJECT_ROOT / "docs" / "reports" / "ar_tracker.jsonl"

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
EXEC_CHANNEL = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")
VP_USER_ID = os.getenv("SLACK_VP_USER_ID", "")

# AR 담당자 우선순위 매핑 (권고 액션 텍스트 키워드 → 페르소나)
_OWNER_PATTERNS: list[tuple[str, str]] = [
    (r"KITT|법무|legal|약관|disclaimer|저작권", "kitt"),
    (r"TARS|엔지니어링|코드|파이프라인|스크립트|publisher|adapter", "tars"),
    (r"Friday|사업운영|KPI|forecast|지표|구독자", "friday"),
    (r"Vision|상품기획|spec|파이럿|발행.*계획", "vision"),
    (r"Scribe|QA|검증|qa_clear|fact.*check", "scribe"),
    (r"Watchman|리스크|red.?team|pre.?mortem|cross.*LLM", "watchman"),
    (r"C3PO|마케팅|카피|채널|acquisition", "c3po"),
    (r"Coach|인사|교육|OJT", "coach"),
    (r"부대표|VP|vice.?president", "vp"),
]

_PRIORITY_DAYS = {"critical": 0, "high": 2, "medium": 5, "low": 14}


# ── Storage ───────────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if not AR_LOG_PATH.exists():
        return []
    records = []
    for line in AR_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def _rewrite(records: list[dict]) -> None:
    AR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AR_LOG_PATH.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _append(record: dict) -> None:
    AR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AR_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── Creation ──────────────────────────────────────────────────────────────────

def _infer_owner(text: str) -> str:
    for pattern, owner in _OWNER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return owner
    return "jarvis"


def _infer_priority(text: str) -> str:
    if re.search(r"즉시|긴급|critical|오늘|당일", text, re.IGNORECASE):
        return "critical"
    if re.search(r"high|우선|필수|게이트|blocking", text, re.IGNORECASE):
        return "high"
    if re.search(r"low|낮음|나중|optional", text, re.IGNORECASE):
        return "low"
    return "medium"


def create_ar(
    title: str,
    description: str,
    owner: str | None = None,
    priority: str | None = None,
    due_by: str | None = None,
    source_correlation_id: str = "",
    evidence_required: str = "담당자 완료 보고 + 결과물 링크/경로",
) -> dict:
    inferred_owner = owner or _infer_owner(title + " " + description)
    inferred_priority = priority or _infer_priority(title + " " + description)
    due_days = _PRIORITY_DAYS.get(inferred_priority, 5)
    inferred_due = due_by or (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")

    today = datetime.now().strftime("%Y%m%d")
    existing_today = [r for r in _load() if r.get("id", "").startswith(f"AR-{today}")]
    seq = len(existing_today) + 1

    ar: dict[str, Any] = {
        "id": f"AR-{today}-{seq:03d}",
        "title": title[:120],
        "owner": inferred_owner,
        "source_correlation_id": source_correlation_id,
        "priority": inferred_priority,
        "status": "open",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "due_by": inferred_due,
        "description": description[:500],
        "evidence_required": evidence_required,
        "last_checked_at": None,
        "reminder_count": 0,
        "completed_at": None,
        "completion_note": None,
    }
    _append(ar)
    print(f"[ar_tracker] AR 등록: {ar['id']} — {title[:60]} (owner={inferred_owner}, due={inferred_due})")
    return ar


def complete_ar(ar_id: str, note: str) -> bool:
    records = _load()
    for r in records:
        if r["id"] == ar_id:
            r["status"] = "completed"
            r["completed_at"] = datetime.now().isoformat(timespec="seconds")
            r["completion_note"] = note[:500]
            _rewrite(records)
            return True
    return False


# ── Extraction from Decision Card ─────────────────────────────────────────────

def extract_ars_from_decision(decision_text: str, correlation_id: str) -> list[dict]:
    """권고 액션 섹션에서 AR 자동 추출."""
    existing_cids = {r.get("source_correlation_id") for r in _load()}
    if correlation_id in existing_cids:
        return []

    section = re.search(
        r"(?:권고\s*액션|recommended\s*action|다음\s*할\s*일)[^\n]*\n(.*?)(?=\n#{1,3} |\Z)",
        decision_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not section:
        return []

    block = section.group(1)
    new_ars = []
    for line in block.splitlines():
        line = line.strip()
        # 번호 목록 또는 bullet 항목
        m = re.match(r"^(?:\d+\.|[-*•])\s+\*{0,2}(.+?)\*{0,2}(?:\s*[-—]\s*(.*))?$", line)
        if not m:
            continue
        title = m.group(1).strip()
        desc = m.group(2).strip() if m.group(2) else title
        if len(title) < 5:
            continue
        ar = create_ar(
            title=title,
            description=desc,
            source_correlation_id=correlation_id,
        )
        new_ars.append(ar)

    return new_ars


# ── Daily Check ───────────────────────────────────────────────────────────────

def _post_slack(channel: str, text: str) -> None:
    if not SLACK_BOT_TOKEN or not channel:
        print(f"[ar_tracker] Slack 미설정 — 메시지 생략: {text[:80]}")
        return
    try:
        httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={"channel": channel, "text": text[:3900]},
            timeout=10,
        )
    except Exception as exc:
        print(f"[ar_tracker] Slack 전송 실패: {exc}")


def _persona_ping(owner: str, ar: dict) -> str:
    """담당 페르소나에게 AR 이행 현황 질의."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.run_persona import call_persona
    from agents.registry import get_persona

    days_overdue = (
        datetime.now().date() - datetime.fromisoformat(ar["due_by"]).date()
    ).days

    if days_overdue > 0:
        urgency = f"⚠️ 기한이 {days_overdue}일 지났습니다. 즉시 완료하거나 완료 불가 사유를 보고해 주세요."
    elif days_overdue == 0:
        urgency = "⏰ 오늘이 기한입니다. 오늘 내 완료해 주세요."
    else:
        urgency = "현재 진행 현황을 간략히 보고해 주세요."

    prompt = (
        f"AR(Action Required) 이행 현황 보고 요청입니다.\n\n"
        f"AR ID: {ar['id']}\n"
        f"제목: {ar['title']}\n"
        f"내용: {ar['description']}\n"
        f"기한: {ar['due_by']}\n"
        f"필요 산출물: {ar['evidence_required']}\n\n"
        f"{urgency}\n\n"
        f"완료됐다면 결과물(파일 경로, URL, 요약)을 명시해 주세요. "
        f"진행 중이라면 완료 예상 시점을 알려주세요. "
        f"2~3문장으로 간결하게 보고해 주세요."
    )

    try:
        persona = get_persona(owner)
        text, ok = call_persona(persona, prompt, f"ar-check-{ar['id']}")
        return text[:400] if ok else "(페르소나 응답 없음)"
    except Exception as exc:
        return f"(오류: {exc})"


def check_ars_and_report() -> None:
    """매일 08:00 실행 — 미완 AR 점검 후 CEO 채널 보고."""
    records = _load()
    today = datetime.now().strftime("%Y-%m-%d")

    open_ars = [r for r in records if r["status"] in ("open", "in_progress", "overdue")]
    if not open_ars:
        _post_slack(EXEC_CHANNEL, "*Jarvis(비서실장)*: ✅ 오늘 미완 AR이 없습니다.")
        return

    report_sections: list[str] = [
        f"*Jarvis(비서실장)* — AR 이행 일일 점검 ({today})\n"
        f"미완: {len(open_ars)}건\n"
    ]

    updated_records = {r["id"]: r for r in records}

    for ar in sorted(open_ars, key=lambda x: (x["due_by"], x["priority"])):
        ar_id = ar["id"]
        due = ar["due_by"]
        days_diff = (datetime.fromisoformat(due).date() - datetime.now().date()).days
        owner = ar.get("owner", "jarvis")

        # 상태 업데이트
        if days_diff < 0:
            updated_records[ar_id]["status"] = "overdue"
            updated_records[ar_id]["reminder_count"] = ar.get("reminder_count", 0) + 1
        elif ar["status"] == "open":
            updated_records[ar_id]["status"] = "in_progress"

        updated_records[ar_id]["last_checked_at"] = datetime.now().isoformat(timespec="seconds")

        # 페르소나 ping (VP는 Slack DM으로 대체)
        if owner == "vp":
            response = "(부대표님께 Slack DM으로 알림)"
            if VP_USER_ID and days_diff <= 0:
                _post_slack(
                    VP_USER_ID,
                    f"부대표님, AR 이행 기한이 {'지났습니다' if days_diff < 0 else '오늘입니다'}.\n"
                    f"[{ar_id}] {ar['title']}\n기한: {due}",
                )
        else:
            response = _persona_ping(owner, ar)

        updated_records[ar_id]["last_report"] = response[:400]

        # 심각도별 이모지
        if days_diff < -3:
            emoji = "🔴🔴"
        elif days_diff < 0:
            emoji = "🔴"
        elif days_diff == 0:
            emoji = "⏰"
        else:
            emoji = "🟡"

        report_sections.append(
            f"\n{emoji} *[{ar_id}]* {ar['title']}\n"
            f"담당: {owner}님 | 기한: {due} ({'+' if days_diff >= 0 else ''}{days_diff}일)\n"
            f"보고: {response[:250]}"
        )

    _rewrite(list(updated_records.values()))
    summary = "\n".join(report_sections)
    _post_slack(EXEC_CHANNEL, summary)
    print(f"[ar_tracker] 일일 점검 완료 — {len(open_ars)}건 보고")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cmd_list(open_only: bool = False) -> None:
    records = _load()
    if open_only:
        records = [r for r in records if r["status"] not in ("completed", "waived")]
    if not records:
        print("AR 없음.")
        return
    for r in records:
        flag = "✅" if r["status"] == "completed" else ("🔴" if r["status"] == "overdue" else "🟡")
        print(f"{flag} [{r['id']}] {r['title']} | owner={r['owner']} | due={r['due_by']} | status={r['status']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "check":
        check_ars_and_report()
    elif cmd == "list":
        _cmd_list(open_only="--open" in sys.argv)
    elif cmd == "complete" and len(sys.argv) >= 4:
        ok = complete_ar(sys.argv[2], sys.argv[3])
        print("완료 처리됨" if ok else "AR ID를 찾을 수 없음")
    else:
        print(__doc__)
