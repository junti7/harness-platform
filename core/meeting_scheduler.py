"""예약 회의 저장·조회·실행 (Charter §4.4 회의 소집 확장).

CEO가 "5/22 14시 회의 소집: 주제"처럼 미래 시각을 공지하면, 그 시각에
Jarvis 회의(orchestrate)가 자동으로 열린다. 예약은 파일에 저장되므로
수신기(listener) 재시작에도 사라지지 않고, 별도 작업(run_scheduled_meetings.py)이
1분마다 도래한 예약을 실행한다.

한국어 시각 표현 파서는 MVP 범위:
  - 절대: "5/22 14시", "5/22 14:00", "5월 22일 오후 2시"
  - 상대: "오늘/내일/모레 [오전/오후] 2시[:30]"
  - 시각만: "14시" → 오늘(지났으면 내일)
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHED_PATH = PROJECT_ROOT / "runtime" / "scheduled_meetings.json"


def _parse_hm(text: str) -> tuple[int, int] | None:
    is_pm = ("오후" in text) or ("pm" in text.lower())
    is_am = ("오전" in text) or ("am" in text.lower())
    m = re.search(r"(\d{1,2})\s*:\s*(\d{2})", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
    else:
        m2 = re.search(r"(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?", text)
        if not m2:
            return None
        hour, minute = int(m2.group(1)), int(m2.group(2) or 0)
    if is_pm and hour < 12:
        hour += 12
    if is_am and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def parse_meeting_time(text: str, now: datetime | None = None) -> datetime | None:
    """미래 회의 시각을 파싱. 못 찾거나 과거면 None."""
    now = now or datetime.now()
    hm = _parse_hm(text)
    if hm is None:
        return None
    hour, minute = hm

    date_m = re.search(r"(\d{1,2})\s*[/월]\s*(\d{1,2})", text)
    rel_m = re.search(r"(오늘|내일|모레)", text)
    try:
        if date_m:
            mon, day = int(date_m.group(1)), int(date_m.group(2))
            dt = now.replace(month=mon, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if dt < now:
                dt = dt.replace(year=now.year + 1)
        elif rel_m:
            delta = {"오늘": 0, "내일": 1, "모레": 2}[rel_m.group(1)]
            base = now + timedelta(days=delta)
            dt = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if dt < now:
                dt += timedelta(days=1)
    except ValueError:
        return None
    return dt if dt > now else None


def _load() -> list[dict]:
    if not SCHED_PATH.exists():
        return []
    try:
        return json.loads(SCHED_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(items: list[dict]) -> None:
    SCHED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHED_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add_meeting(when: datetime, order: str, channel: str, created_by: str) -> dict:
    items = _load()
    rec = {
        "id": f"sched-{uuid.uuid4().hex[:8]}",
        "when": when.isoformat(timespec="minutes"),
        "order": order,
        "channel": channel,
        "created_by": created_by,
        "status": "pending",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    items.append(rec)
    _save(items)
    return rec


def due_meetings(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    out = []
    for rec in _load():
        if rec.get("status") != "pending":
            continue
        try:
            when = datetime.fromisoformat(rec["when"])
        except (ValueError, KeyError):
            continue
        if when <= now:
            out.append(rec)
    return out


def mark_done(meeting_id: str, status: str = "done") -> None:
    items = _load()
    for rec in items:
        if rec.get("id") == meeting_id:
            rec["status"] = status
            rec["executed_at"] = datetime.now().isoformat(timespec="seconds")
    _save(items)
