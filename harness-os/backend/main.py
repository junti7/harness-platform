from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import shlex
import threading
import time
import html
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import anthropic
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass

TARGET_FREE_SUBSCRIBERS = 50
TARGET_PAID_SUBSCRIBERS = 1
CACHE_TTL_SECONDS = int(os.getenv("HARNESS_OS_CACHE_SECONDS", "60"))
GMAIL_RUNTIME_ENABLED = os.getenv("HARNESS_GMAIL_RUNTIME_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
GMAIL_RUNTIME_HOST = os.getenv("HARNESS_GMAIL_RUNTIME_HOST", "").strip()
GMAIL_RUNTIME_USER = os.getenv("HARNESS_GMAIL_RUNTIME_USER", "").strip()
GMAIL_RUNTIME_ACCOUNT = os.getenv("HARNESS_GMAIL_ACCOUNT", "").strip()
GMAIL_RUNTIME_GOG_BIN = os.getenv("HARNESS_GMAIL_GOG_BIN", "/opt/homebrew/bin/gog").strip()
GMAIL_RUNTIME_SSH_BIN = os.getenv("HARNESS_GMAIL_SSH_BIN", "ssh").strip()
GMAIL_RUNTIME_TIMEOUT_S = int(os.getenv("HARNESS_GMAIL_TIMEOUT_S", "20"))
GMAIL_RUNTIME_KEYRING_BACKEND = os.getenv("HARNESS_GMAIL_KEYRING_BACKEND", "").strip()
GMAIL_RUNTIME_KEYRING_PASSWORD = os.getenv("HARNESS_GMAIL_KEYRING_PASSWORD", "").strip()

AR_TRACKER_PATH = PROJECT_ROOT / "docs" / "reports" / "ar_tracker.jsonl"
AR_REGISTRY_PATH = PROJECT_ROOT / "docs" / "operations" / "ACTION_REQUIRED_REGISTRY.json"
APPROVAL_REQUESTS_PATH = PROJECT_ROOT / "docs" / "operations" / "APPROVAL_REQUESTS.json"
APPROVAL_HANDOFFS_PATH = PROJECT_ROOT / "docs" / "reports" / "openclaw_approval_handoffs.jsonl"
APPROVAL_INTAKE_PATH = PROJECT_ROOT / "docs" / "reports" / "approval_intake.jsonl"
NOTION_MINUTES_RUN_LOG_PATH = PROJECT_ROOT / "docs" / "reports" / "notion_minutes_runs.jsonl"
CONFERENCE_ROOM_STREAM_PATH = PROJECT_ROOT / "docs" / "reports" / "conference_room_stream.jsonl"
CONFERENCE_ROOM_NOTION_QUEUE_PATH = PROJECT_ROOT / "docs" / "reports" / "conference_room_notion_queue.jsonl"

AR_OWNER_LABELS: dict[str, str] = {
    "jarvis": "Jarvis(비서실)",
    "kitt": "KITT(법무팀)",
    "tars": "TARS(엔지니어링팀)",
    "friday": "Friday(사업운영팀)",
    "vision": "Vision(상품기획팀)",
    "watchman": "Watchman(리스크관리팀)",
    "ledger": "Ledger(재무팀)",
    "scribe": "Scribe(QA팀)",
    "coach": "Coach(HR Training Team)",
    "c3po": "C3PO(마케팅팀)",
    "vp": "Vice President(부대표)",
}

EVIDENCE_BASENAME_HINTS = (
    "SOUL.md",
    "RISK_REGISTER.md",
    "KILL_CRITERIA.md",
    "ACTION_REQUIRED_REGISTRY.json",
)


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


_CACHE: dict[str, CacheEntry] = {}
_CACHE_LOCK = threading.Lock()

app = FastAPI(title="Harness-OS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("HARNESS_OS_ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JarvisInvokeRequest(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=200)
    relay_to_slack: bool = True
    relay_mentions: bool = True


# ── Pipeline Job Runner ──────────────────────────────────────────
import subprocess
import signal as _signal

_JOB_LOCK = threading.Lock()
_PIPELINE_JOBS: dict[str, dict] = {}
_PIPELINE_LOGS: dict[str, list] = {}
_MAX_LOG_LINES = 300
_MAX_JOB_HISTORY = 30
_PROJECT_ROOT = Path(__file__).parent.parent.parent

_SOURCE_MAP: dict[str, str | None] = {
    "scholar": "scholar",
    "arxiv": "arxiv",
    "youtube": "youtube",
    "rss": "rss",
    "all": "rss,scholar,arxiv,youtube",
    "filter": None,
}


def _tail_process(job_id: str, proc: subprocess.Popen) -> None:
    try:
        for raw_line in proc.stdout:  # type: ignore[union-attr]
            line = raw_line.rstrip()
            with _JOB_LOCK:
                buf = _PIPELINE_LOGS.setdefault(job_id, [])
                buf.append(line)
                if len(buf) > _MAX_LOG_LINES:
                    _PIPELINE_LOGS[job_id] = buf[-_MAX_LOG_LINES:]
        proc.wait()
        rc = proc.returncode
        with _JOB_LOCK:
            # stopped 상태는 stop API가 이미 설정했으므로 덮어쓰지 않음
            if job_id in _PIPELINE_JOBS and _PIPELINE_JOBS[job_id]["status"] == "running":
                _PIPELINE_JOBS[job_id]["status"] = "completed" if rc == 0 else "failed"
                _PIPELINE_JOBS[job_id]["exit_code"] = rc
                _PIPELINE_JOBS[job_id]["finished_at"] = datetime.utcnow().isoformat() + "Z"
    except Exception as exc:
        with _JOB_LOCK:
            if job_id in _PIPELINE_JOBS and _PIPELINE_JOBS[job_id]["status"] == "running":
                _PIPELINE_JOBS[job_id]["status"] = "error"
                _PIPELINE_JOBS[job_id]["finished_at"] = datetime.utcnow().isoformat() + "Z"
                _PIPELINE_LOGS.setdefault(job_id, []).append(f"[ERROR] {exc}")


_CUSTOM_QUERIES_FILE = _PROJECT_ROOT / "data" / "edu_custom_queries.json"

def _load_custom_queries() -> list[dict]:
    try:
        if _CUSTOM_QUERIES_FILE.exists():
            data = json.loads(_CUSTOM_QUERIES_FILE.read_text())
            return data.get("queries", [])
    except Exception:
        pass
    return []

def _save_custom_queries(queries: list[dict]) -> None:
    _CUSTOM_QUERIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CUSTOM_QUERIES_FILE.write_text(json.dumps({"queries": queries}, indent=2, ensure_ascii=False))


class PipelineRunRequest(BaseModel):
    source: str
    dry_run: bool = False
    topic: str = ""  # 연구 주제 (비어있으면 기본 쿼리 사용)
    max_rss_items: int = 50  # RSS 소스당 최대 수집 항목 수
    scholar_mode: str = "en_only"  # "en_only" | "multilingual"


class TradingWatchlistToggleRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=200)
    action: str = Field(pattern="^(activate|deactivate)$")


class TradingWatchlistAddRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=100)
    name_hint: str = Field(min_length=1, max_length=300)
    exchange_hint: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    watch_reason: str | None = Field(default=None, max_length=300)
    priority: int = Field(default=999, ge=0, le=9999)


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    actor_role: str = Field(pattern="^(ceo|vp)$")
    note: str | None = Field(default=None, max_length=4000)


class ConferenceRoomMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    actor_role: str = Field(pattern="^(ceo|vp)$")
    actor_display: str | None = Field(default=None, max_length=100)
    parent_ts: str | None = Field(default=None, max_length=40)


class ConferenceRoomStartRequest(BaseModel):
    mode: str = Field(pattern="^(direct|cos_request)$")
    actor_role: str = Field(pattern="^(ceo|vp)$")
    actor_display: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=200)
    agenda: str | None = Field(default=None, max_length=6000)
    participants: list[str] = Field(min_length=1, max_length=12)


def _require_secret(x_harness_secret: str | None = Header(default=None)) -> None:
    expected = os.getenv("HARNESS_OS_SECRET_KEY", "").strip()
    if not expected:
        return
    if x_harness_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid dashboard secret")


# ── 비밀번호 관리 ─────────────────────────────────────────────────────────────
# ~/.harness/passwords.json — git 바깥, 배포/재시작에 절대 영향받지 않음.
# 우선순위: ~/.harness/passwords.json > 기본값(ceo123/vp123)
_HARNESS_DATA_DIR = Path.home() / ".harness"
_PASSWORDS_FILE = _HARNESS_DATA_DIR / "passwords.json"
_PW_LOCK = threading.Lock()


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def _load_passwords() -> dict[str, str]:
    if _PASSWORDS_FILE.exists():
        try:
            data = json.loads(_PASSWORDS_FILE.read_text())
            if "ceo" in data and "vp" in data:
                return dict(data)
        except Exception:
            pass
    # 최초 기동: 기본값으로 파일 생성
    passwords = {"ceo": _hash_pw("ceo123"), "vp": _hash_pw("vp123")}
    try:
        _HARNESS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        _PASSWORDS_FILE.write_text(json.dumps(passwords, indent=2))
    except Exception:
        pass
    return passwords


def _persist_password(role: str, new_hash: str) -> None:
    """비밀번호 해시를 ~/.harness/passwords.json에 저장."""
    _HARNESS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(_PASSWORDS_FILE.read_text()) if _PASSWORDS_FILE.exists() else {}
    except Exception:
        data = {}
    data[role] = new_hash
    _PASSWORDS_FILE.write_text(json.dumps(data, indent=2))


_PASSWORDS: dict[str, str] = _load_passwords()


class AuthLoginRequest(BaseModel):
    role: str
    password: str


class AuthChangePasswordRequest(BaseModel):
    role: str
    current_password: str
    new_password: str


@app.post("/api/auth/login")
def auth_login(req: AuthLoginRequest, _: None = Depends(_require_secret)):
    if req.role not in ("ceo", "vp"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if _PASSWORDS.get(req.role) != _hash_pw(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"ok": True, "role": req.role}


@app.post("/api/auth/change-password")
def auth_change_password(req: AuthChangePasswordRequest, _: None = Depends(_require_secret)):
    global _PASSWORDS
    if req.role not in ("ceo", "vp"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail="새 비밀번호는 4자 이상이어야 합니다.")
    with _PW_LOCK:
        if _PASSWORDS.get(req.role) != _hash_pw(req.current_password):
            raise HTTPException(status_code=401, detail="Current password incorrect")
        new_hash = _hash_pw(req.new_password)
        _PASSWORDS[req.role] = new_hash
        try:
            _persist_password(req.role, new_hash)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save password: {e}")
    return {"ok": True}


def _post_slack_message(channel_id: str, text: str) -> str | None:
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if not token:
        return "SLACK_BOT_TOKEN 미설정"
    if not channel_id:
        return "Slack channel_id 미설정"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"channel": channel_id, "text": text[:3900]}
    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=12.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return None

        # Public channels frequently fail with `not_in_channel` when bot invite is missing.
        # Auto-join and retry once so relay works from Jarvis console without manual step.
        if data.get("error") == "not_in_channel" and channel_id.startswith("C"):
            join_resp = httpx.post(
                "https://slack.com/api/conversations.join",
                headers=headers,
                json={"channel": channel_id},
                timeout=12.0,
            )
            join_resp.raise_for_status()
            joined = join_resp.json()
            if not joined.get("ok"):
                return f"Slack 채널 join 실패: {joined.get('error')}"
            retry_resp = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json=payload,
                timeout=12.0,
            )
            retry_resp.raise_for_status()
            retry_data = retry_resp.json()
            if retry_data.get("ok"):
                return None
            return f"Slack API 오류: {retry_data.get('error')}"

        return f"Slack API 오류: {data.get('error')}"
    except Exception as exc:
        return f"Slack 전송 실패: {type(exc).__name__}: {exc}"
    return None


def _slack_api(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN 미설정")
    resp = httpx.post(
        f"https://slack.com/api/{endpoint}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API 오류({endpoint}): {data.get('error')}")
    return data


def _conference_room_channel_id() -> str:
    return os.getenv("SLACK_CHANNEL_CONFERENCE_ROOM", "").strip()


def _slack_ts_to_iso(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts)).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def _slack_text_to_markdown(text: str | None) -> str:
    value = html.unescape(text or "")
    value = re.sub(r"<(https?://[^>|]+)\|([^>]+)>", r"[\2](\1)", value)
    value = re.sub(r"<(https?://[^>]+)>", r"\1", value)
    value = re.sub(r"<@([A-Z0-9]+)>", r"@\1", value)
    value = value.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return value.strip()


def _normalize_actor_key(name: str | None) -> str:
    base = re.sub(r"\(.*?\)", "", (name or "")).strip().lower()
    base = re.sub(r"[^a-z0-9]+", "", base)
    return base


def _owner_display_from_name(name: str | None) -> str:
    if not name:
        return "Slack Member"
    normalized = _normalize_actor_key(name)
    if normalized in AR_OWNER_LABELS:
        return AR_OWNER_LABELS[normalized]
    return name.strip()


def _slack_user_display(user_id: str, cache: dict[str, str]) -> str:
    if user_id in cache:
        return cache[user_id]
    try:
        payload = _slack_api("users.info", {"user": user_id})
        user = payload.get("user") or {}
        profile = user.get("profile") or {}
        display = (
            profile.get("display_name")
            or profile.get("real_name")
            or user.get("real_name")
            or user.get("name")
            or user_id
        )
        cache[user_id] = _owner_display_from_name(str(display))
    except Exception:
        cache[user_id] = user_id
    return cache[user_id]


def _conference_author_display(message: dict[str, Any], user_cache: dict[str, str]) -> str:
    text_hint = _conference_text_persona_hint(_slack_text_to_markdown(str(message.get("text") or "")))
    if text_hint:
        return text_hint
    user_id = str(message.get("user") or "").strip()
    if user_id:
        return _slack_user_display(user_id, user_cache)
    bot_profile = message.get("bot_profile") or {}
    bot_name = str(bot_profile.get("name") or message.get("username") or "Jarvis").strip()
    return _owner_display_from_name(bot_name)


def _conference_message_title(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^\*\*(.*?)\*\*$", r"\1", line)
        line = re.sub(r"^\*(.*?)\*$", r"\1", line)
        line = re.sub(r"\s+", " ", line)
        return line[:96]
    return "제목 없는 대화"


def _conference_message_preview(text: str) -> str:
    compact = " ".join(line.strip() for line in (text or "").splitlines() if line.strip())
    return compact[:180]


def _conference_text_persona_hint(text: str) -> str | None:
    match = re.match(r"^\s*\*{1,2}([^*\n]+?)\*{1,2}(?:\s+정리)?\s*:\s*", text or "")
    if not match:
        return None
    return _owner_display_from_name(match.group(1).strip())


def _conference_message_body_markdown(text: str) -> str:
    return re.sub(r"^\s*\*{1,2}[^*\n]+?\*{1,2}(?:\s+정리)?\s*:\s*", "", text or "", count=1).strip()


def _conference_room_directory() -> list[dict[str, str]]:
    entries: list[tuple[str, str]] = [
        ("jarvis", "Jarvis(비서실)"),
        ("kitt", "KITT(법무팀)"),
        ("watchman", "Watchman(리스크관리팀)"),
        ("ledger", "Ledger(재무팀)"),
        ("vision", "Vision(상품기획팀)"),
        ("tars", "TARS(엔지니어링팀)"),
        ("friday", "Friday(사업운영팀)"),
        ("scribe", "Scribe(QA팀)"),
        ("c3po", "C3PO(마케팅팀)"),
        ("coach", "Coach(HR Training Team)"),
    ]
    return [{"id": key, "label": label} for key, label in entries]


def _conference_linked_run(text: str, runs_by_id: dict[str, dict[str, Any]]) -> tuple[str | None, dict[str, Any] | None]:
    for correlation_id, run in runs_by_id.items():
        if correlation_id and correlation_id in text:
            return correlation_id, run
    return None, None


def _read_conference_room_stream() -> list[dict[str, Any]]:
    rows = [row for row in _read_jsonl(CONFERENCE_ROOM_STREAM_PATH) if str(row.get("thread_id") or "").strip()]
    rows.sort(key=lambda item: str(item.get("posted_at") or ""))
    return rows


def _conference_room_payload(limit: int = 80) -> dict[str, Any]:
    rows = _read_conference_room_stream()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("thread_id") or ""), []).append(row)

    items: list[dict[str, Any]] = []
    participants: set[str] = set()
    total_messages = 0
    for thread_id, thread_rows in grouped.items():
        if not thread_rows:
            continue
        root = next((row for row in thread_rows if str(row.get("id") or "") == thread_id), thread_rows[0])
        latest = thread_rows[-1]
        planned = [str(item).strip() for item in (root.get("participants_planned") or []) if str(item).strip()]
        thread_participants = sorted(
            {
                *{str(row.get("author_display") or "").strip() for row in thread_rows if str(row.get("author_display") or "").strip()},
                *planned,
            }
        )
        participants.update(thread_participants)
        total_messages += len(thread_rows)
        title_source = str(root.get("title") or root.get("text_markdown") or "새 회의")
        latest_source = str(latest.get("text_markdown") or "")
        items.append(
            {
                "id": thread_id,
                "ts": thread_id,
                "posted_at": str(latest.get("posted_at") or root.get("posted_at") or "") or None,
                "author_display": str(root.get("author_display") or "Jarvis(비서실)"),
                "author_role": str(root.get("author_role") or _normalize_actor_key(str(root.get("author_display") or ""))),
                "title": _conference_message_title(title_source),
                "preview": _conference_message_preview(latest_source),
                "reply_count": max(0, len(thread_rows) - 1),
                "participant_count": len(thread_participants),
                "participants": thread_participants,
                "correlation_id": str(root.get("correlation_id") or "") or None,
                "title_pending": bool(root.get("title_pending")),
                "agenda_pending": bool(root.get("agenda_pending")),
                "linked_note": None,
                "sync_origin": "local",
            }
        )

    items.sort(key=lambda item: str(item.get("posted_at") or ""), reverse=True)
    items = items[:limit]
    updated_at = items[0].get("posted_at") if items else None
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": updated_at,
        "source": "docs/reports/conference_room_stream.jsonl (forward-only)",
        "sync_mode": "local",
        "channel": {
            "id": None,
            "name": "회의실",
            "live_sync": False,
        },
        "stats": {
            "threads": len(items),
            "participants": len(participants),
            "messages": total_messages,
        },
        "directory": _conference_room_directory(),
        "items": items,
    }


def _conference_room_detail(item_id: str) -> dict[str, Any]:
    payload = _conference_room_payload(limit=400)
    target = next((item for item in payload.get("items", []) if str(item.get("id")) == item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Conference item {item_id} not found")

    rows = [row for row in _read_conference_room_stream() if str(row.get("thread_id") or "") == item_id]
    if not rows:
        return {**target, "messages": [], "linked_run": None}

    messages: list[dict[str, Any]] = []
    participants: set[str] = set()
    root = rows[0]
    planned = [str(item).strip() for item in (root.get("participants_planned") or []) if str(item).strip()]
    for row in rows:
        author_display = str(row.get("author_display") or "Jarvis(비서실)")
        participants.add(author_display)
        messages.append(
            {
                "id": str(row.get("id") or ""),
                "ts": str(row.get("id") or ""),
                "posted_at": str(row.get("posted_at") or "") or None,
                "author_display": author_display,
                "author_role": str(row.get("author_role") or _normalize_actor_key(author_display)),
                "text_markdown": str(row.get("text_markdown") or ""),
                "is_reply": str(row.get("id") or "") != item_id,
            }
        )
    participant_statuses = []
    for planned_name in planned:
        participant_statuses.append(
            {
                "name": planned_name,
                "status": "joined" if planned_name in participants else "invited",
            }
        )
    return {
        **target,
        "participant_count": len(set([*participants, *planned])) or target.get("participant_count") or 1,
        "participants": sorted(set([*participants, *planned])),
        "participant_statuses": participant_statuses,
        "title_pending": bool(root.get("title_pending")),
        "agenda_pending": bool(root.get("agenda_pending")),
        "linked_note": None,
        "messages": messages,
        "linked_run": None,
    }


def _conference_room_actor_label(actor_role: str, actor_display: str | None = None) -> str:
    if actor_display and actor_display.strip():
        return actor_display.strip()
    return "대표님" if actor_role == "ceo" else "부대표님"


def _post_conference_room_message(req: ConferenceRoomMessageRequest) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    message_id = uuid4().hex
    thread_id = (req.parent_ts or message_id).strip()
    author_display = _conference_room_actor_label(req.actor_role, req.actor_display)
    payload = {
        "id": message_id,
        "thread_id": thread_id,
        "parent_id": req.parent_ts.strip() if req.parent_ts else None,
        "posted_at": now,
        "author_display": author_display,
        "author_role": _normalize_actor_key(author_display),
        "text_markdown": req.text.strip(),
        "correlation_id": None,
        "source": "dashboard_conference_room",
    }
    _append_jsonl(CONFERENCE_ROOM_STREAM_PATH, payload)
    _append_jsonl(
        CONFERENCE_ROOM_NOTION_QUEUE_PATH,
        {
            "queued_at": now,
            "thread_id": thread_id,
            "message_id": message_id,
            "author_display": author_display,
            "author_role": _normalize_actor_key(author_display),
            "text_markdown": req.text.strip(),
            "status": "queued",
            "target": "notion_conference_room",
        },
    )

    channel_id = _conference_room_channel_id()
    if channel_id:
        prefix = f"*{author_display} · Dashboard 회의실*"
        slack_payload = {
            "channel": channel_id,
            "text": f"{prefix}\n{req.text.strip()}",
        }
        if req.parent_ts:
            slack_payload["thread_ts"] = req.parent_ts.strip()
        try:
            _slack_api("chat.postMessage", slack_payload)
        except Exception:
            pass

    return {
        "ok": True,
        "ts": message_id,
        "thread_ts": thread_id,
        "mode": "reply" if req.parent_ts else "root",
        "posted_at": now,
    }


def _start_conference_room(req: ConferenceRoomStartRequest) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    thread_id = uuid4().hex
    requester = _conference_room_actor_label(req.actor_role, req.actor_display)
    participants = [_owner_display_from_name(item) for item in req.participants]
    title = str(req.title or "").strip()
    agenda = str(req.agenda or "").strip()
    display_title = title or "새 회의"
    title_pending = not bool(title)
    agenda_pending = not bool(agenda)

    if req.mode == "cos_request":
        author_display = "Jarvis(비서실)"
        body = (
            f"[회의소집] {display_title}\n\n"
            f"{requester} 요청으로 아래 참여자를 소집합니다.\n\n"
            f"참여자:\n- " + "\n- ".join(participants) + "\n\n"
            f"안건:\n{agenda or '- 아직 미정입니다. 회의 진행 후 LLM이 자동 정리합니다.'}\n\n"
            f"회의가 시작되면 이 스레드에서 바로 논의하겠습니다."
        )
    else:
        author_display = requester
        body = (
            f"[새회의] {display_title}\n\n"
            f"참여자:\n- " + "\n- ".join(participants) + "\n\n"
            f"안건:\n{agenda or '- 아직 미정입니다. 회의 진행 후 LLM이 자동 정리합니다.'}"
        )

    payload = {
        "id": thread_id,
        "thread_id": thread_id,
        "parent_id": None,
        "posted_at": now,
        "author_display": author_display,
        "author_role": _normalize_actor_key(author_display),
        "title": title,
        "title_pending": title_pending,
        "agenda_pending": agenda_pending,
        "participants_planned": participants,
        "requested_by": requester,
        "request_mode": req.mode,
        "text_markdown": body,
        "correlation_id": None,
        "source": "dashboard_conference_room_start",
    }
    _append_jsonl(CONFERENCE_ROOM_STREAM_PATH, payload)
    auto_prompt = (
        "각 팀은 아래 형식으로 첫 답변을 남겨주세요.\n\n"
        "1. 현재 판단 1문장\n"
        "2. 가장 큰 리스크 1개\n"
        "3. 지금 당장 필요한 추가 정보 1개"
    )
    _append_jsonl(
        CONFERENCE_ROOM_STREAM_PATH,
        {
            "id": uuid4().hex,
            "thread_id": thread_id,
            "parent_id": thread_id,
            "posted_at": now,
            "author_display": "Jarvis(비서실)",
            "author_role": "jarvis",
            "text_markdown": auto_prompt,
            "correlation_id": None,
            "source": "dashboard_conference_room_auto_prompt",
        },
    )
    _append_jsonl(
        CONFERENCE_ROOM_NOTION_QUEUE_PATH,
        {
            "queued_at": now,
            "thread_id": thread_id,
            "message_id": thread_id,
            "author_display": author_display,
            "author_role": _normalize_actor_key(author_display),
            "participants_planned": participants,
            "title_pending": title_pending,
            "agenda_pending": agenda_pending,
            "text_markdown": body,
            "status": "queued",
            "target": "notion_conference_room",
        },
    )
    return {
        "ok": True,
        "thread_ts": thread_id,
        "ts": thread_id,
        "posted_at": now,
        "mode": req.mode,
    }


def _create_meeting_note_from_conference_item(item_id: str) -> dict[str, Any]:
    detail = _conference_room_detail(item_id)
    _append_jsonl(
        CONFERENCE_ROOM_NOTION_QUEUE_PATH,
        {
            "queued_at": datetime.now().isoformat(timespec="seconds"),
            "thread_id": item_id,
            "message_id": None,
            "author_display": "Jarvis(비서실)",
            "author_role": "jarvis",
            "text_markdown": json.dumps({"export": "meeting_note", "messages": detail.get("messages", [])}, ensure_ascii=False),
            "status": "queued",
            "target": "notion_conference_room_note",
        },
    )
    return {
        "ok": True,
        "existing": False,
        "correlation_id": item_id,
        "queued": True,
    }


def _strip_persona_mentions(text: str) -> str:
    return re.sub(r"(?<!\S)@([A-Za-z0-9_-]+)", "", text or "").strip()


def _post_qa_to_slack(
    channel_id: str,
    command: str,
    output: str,
    persona_name: str | None = None,
) -> str | None:
    """Q&A 전체(질문+응답)를 Slack Block Kit 형식으로 게시."""
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if not token or not channel_id:
        return "SLACK_BOT_TOKEN 또는 channel_id 미설정"

    # 3900자 제한 (Slack API 한도 4000자)
    output_trimmed = output[:3900] + ("…" if len(output) > 3900 else "")

    header_text = (
        f"Jarvis Console → @{persona_name}" if persona_name else "Jarvis Console"
    )

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": False},
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*질문*\n{command[:300]}",
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*응답*\n{output_trimmed}"},
        },
    ]

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"channel": channel_id, "blocks": blocks, "text": f"{header_text}: {command[:80]}"}
    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=12.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return None
        # not_in_channel → auto join & retry
        if data.get("error") == "not_in_channel" and channel_id.startswith("C"):
            join_resp = httpx.post(
                "https://slack.com/api/conversations.join",
                headers=headers,
                json={"channel": channel_id},
                timeout=12.0,
            )
            if join_resp.json().get("ok"):
                retry = httpx.post(
                    "https://slack.com/api/chat.postMessage",
                    headers=headers,
                    json=payload,
                    timeout=12.0,
                )
                if retry.json().get("ok"):
                    return None
                return f"Slack API 오류(retry): {retry.json().get('error')}"
            return f"채널 join 실패: {join_resp.json().get('error')}"
        return f"Slack API 오류: {data.get('error')}"
    except Exception as exc:
        return f"Slack 전송 실패: {type(exc).__name__}: {exc}"


def _relay_persona_mentions(command: str) -> list[str]:
    from adapters.content.orchestrator import respond_as_persona
    from agents.registry import find_mentioned_personas

    personas = [p for p in find_mentioned_personas(command) if p.handle != "jarvis"]
    if not personas:
        return []

    deduped = []
    seen: set[str] = set()
    for persona in personas:
        if persona.handle in seen:
            continue
        seen.add(persona.handle)
        deduped.append(persona)

    prompt = _strip_persona_mentions(command) or command
    notes: list[str] = []

    for persona in deduped:
        if not persona.channel_env:
            notes.append(f"@{persona.name}: 채널 env 미정의")
            continue
        channel_id = os.getenv(persona.channel_env, "").strip()
        if not channel_id:
            notes.append(f"@{persona.name}: {persona.channel_env} 미설정")
            continue

        relay_header = (
            f"Jarvis Console Relay\n"
            f"- target: @{persona.name}\n"
            f"- request: {prompt}"
        )
        relay_error = _post_slack_message(channel_id, relay_header)
        if relay_error:
            notes.append(f"@{persona.name}: relay 실패 ({relay_error})")
            continue

        try:
            respond_as_persona(
                handle=persona.handle,
                question=prompt,
                channel_id=channel_id,
                post=True,
            )
            notes.append(f"@{persona.name}: {channel_id} 전달 완료")
        except Exception as exc:
            notes.append(f"@{persona.name}: persona 응답 실패 ({type(exc).__name__})")

    return notes


def _cached(key: str, producer: callable) -> Any:
    now = time.time()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry and entry.expires_at > now:
            return entry.value

    value = producer()
    with _CACHE_LOCK:
        _CACHE[key] = CacheEntry(value=value, expires_at=now + CACHE_TTL_SECONDS)
    return value


def _execute_query(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    from core.database import execute_query

    return execute_query(query, params=params, fetch=True) or []


def _gmail_runtime_target() -> str | None:
    if not GMAIL_RUNTIME_HOST or not GMAIL_RUNTIME_USER:
        return None
    return f"{GMAIL_RUNTIME_USER}@{GMAIL_RUNTIME_HOST}"


def _gmail_local_mode() -> bool:
    """HARNESS_GMAIL_RUNTIME_HOST 미설정 시 로컬 gog 직접 실행 모드."""
    return not GMAIL_RUNTIME_HOST


def _gmail_runtime_ready() -> tuple[bool, str | None]:
    if not GMAIL_RUNTIME_ENABLED:
        return False, "HARNESS_GMAIL_RUNTIME_ENABLED=false"
    if not GMAIL_RUNTIME_ACCOUNT:
        return False, "HARNESS_GMAIL_ACCOUNT missing"
    if not _gmail_local_mode() and _gmail_runtime_target() is None:
        return False, "HARNESS_GMAIL_RUNTIME_HOST or HARNESS_GMAIL_RUNTIME_USER missing"
    return True, None


def _gmail_remote_command(query: str, limit: int) -> str:
    quoted_query = shlex.quote(query)
    quoted_account = shlex.quote(GMAIL_RUNTIME_ACCOUNT)
    quoted_gog = shlex.quote(GMAIL_RUNTIME_GOG_BIN)
    exports = ["export PATH=/opt/homebrew/bin:/usr/bin:/bin"]
    if GMAIL_RUNTIME_KEYRING_BACKEND:
        exports.append(f"export GOG_KEYRING_BACKEND={shlex.quote(GMAIL_RUNTIME_KEYRING_BACKEND)}")
    if GMAIL_RUNTIME_KEYRING_PASSWORD:
        exports.append(f"export GOG_KEYRING_PASSWORD={shlex.quote(GMAIL_RUNTIME_KEYRING_PASSWORD)}")
    exports.append(
        f"{quoted_gog} gmail search {quoted_query} "
        f"-a {quoted_account} -j --results-only --gmail-no-send --max {limit}"
    )
    return "; ".join(exports)


def _gmail_search_runtime(query: str, limit: int = 10) -> dict[str, Any]:
    ready, reason = _gmail_runtime_ready()
    if not ready:
        raise HTTPException(status_code=503, detail=f"Gmail runtime not ready: {reason}")

    safe_limit = max(1, min(limit, 25))
    cache_key = f"gmail_search:{query}:{safe_limit}"

    def producer() -> dict[str, Any]:
        env = os.environ.copy()
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
        if GMAIL_RUNTIME_KEYRING_BACKEND:
            env["GOG_KEYRING_BACKEND"] = GMAIL_RUNTIME_KEYRING_BACKEND
        if GMAIL_RUNTIME_KEYRING_PASSWORD:
            env["GOG_KEYRING_PASSWORD"] = GMAIL_RUNTIME_KEYRING_PASSWORD

        if _gmail_local_mode():
            # 로컬 gog 직접 실행
            cmd = [
                GMAIL_RUNTIME_GOG_BIN, "gmail", "search", query,
                "-a", GMAIL_RUNTIME_ACCOUNT, "-j", "--results-only",
                "--gmail-no-send", "--max", str(safe_limit),
            ]
            proc = subprocess.run(
                cmd, cwd=str(PROJECT_ROOT), capture_output=True,
                text=True, timeout=GMAIL_RUNTIME_TIMEOUT_S, check=False, env=env,
            )
        else:
            target = _gmail_runtime_target()
            assert target is not None
            proc = subprocess.run(
                [GMAIL_RUNTIME_SSH_BIN, target, _gmail_remote_command(query, safe_limit)],
                cwd=str(PROJECT_ROOT), capture_output=True,
                text=True, timeout=GMAIL_RUNTIME_TIMEOUT_S, check=False,
            )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:800]
            raise HTTPException(status_code=502, detail=f"Gmail search failed: {detail or 'unknown error'}")

        raw = (proc.stdout or "").strip()
        try:
            items = json.loads(raw) if raw else []
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail=f"Gmail search returned invalid JSON: {exc}") from exc

        if not isinstance(items, list):
            items = [items]

        normalized: list[dict[str, Any]] = []
        for item in items[:safe_limit]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "id": str(item.get("id") or ""),
                    "subject": str(item.get("subject") or ""),
                    "from": str(item.get("from") or ""),
                    "date": str(item.get("date") or ""),
                    "labels": item.get("labels") if isinstance(item.get("labels"), list) else [],
                    "messageCount": int(item.get("messageCount") or 0),
                }
            )

        mode = "local_gog" if _gmail_local_mode() else "ssh_gog_read_only"
        runtime_target = "localhost" if _gmail_local_mode() else _gmail_runtime_target()
        return {
            "runtime": {
                "enabled": True,
                "target": runtime_target,
                "account": GMAIL_RUNTIME_ACCOUNT,
                "mode": mode,
            },
            "query": query,
            "limit": safe_limit,
            "count": len(normalized),
            "items": normalized,
        }

    return _cached(cache_key, producer)


def _gmail_message_runtime(message_id: str) -> dict[str, Any]:
    ready, reason = _gmail_runtime_ready()
    if not ready:
        raise HTTPException(status_code=503, detail=f"Gmail runtime not ready: {reason}")

    safe_msg_id = shlex.quote(message_id.strip())
    if not safe_msg_id or len(safe_msg_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid message ID")

    cache_key = f"gmail_message:{message_id}"

    def producer() -> dict[str, Any]:
        target = _gmail_runtime_target()
        assert target is not None

        exports = ["export PATH=/opt/homebrew/bin:/usr/bin:/bin"]
        if GMAIL_RUNTIME_KEYRING_BACKEND:
            exports.append(f"export GOG_KEYRING_BACKEND={shlex.quote(GMAIL_RUNTIME_KEYRING_BACKEND)}")
        if GMAIL_RUNTIME_KEYRING_PASSWORD:
            exports.append(f"export GOG_KEYRING_PASSWORD={shlex.quote(GMAIL_RUNTIME_KEYRING_PASSWORD)}")

        cmd = (
            f"{shlex.quote(GMAIL_RUNTIME_GOG_BIN)} gmail get {safe_msg_id} "
            f"-a {shlex.quote(GMAIL_RUNTIME_ACCOUNT)} -j --results-only --gmail-no-send"
        )
        exports.append(cmd)
        full_cmd = "; ".join(exports)

        proc = subprocess.run(
            [GMAIL_RUNTIME_SSH_BIN, target, full_cmd],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=GMAIL_RUNTIME_TIMEOUT_S,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:800]
            raise HTTPException(status_code=502, detail=f"Gmail message retrieve failed: {detail or 'unknown error'}")

        raw = (proc.stdout or "").strip()
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail=f"Gmail message returned invalid JSON: {exc}") from exc

        return {
            "id": message_id,
            "subject": data.get("headers", {}).get("subject") or "",
            "from": data.get("headers", {}).get("from") or "",
            "to": data.get("headers", {}).get("to") or "",
            "date": data.get("headers", {}).get("date") or "",
            "body": data.get("body") or "",
            "snippet": data.get("message", {}).get("snippet") or "",
        }

    return _cached(cache_key, producer)



_CONFIGURED_LANGUAGES = [
    {"code": "en", "label": "English", "flag": "🇺🇸"},
    {"code": "es", "label": "Spanish", "flag": "🇪🇸"},
    {"code": "fr", "label": "French", "flag": "🇫🇷"},
    {"code": "de", "label": "German", "flag": "🇩🇪"},
    {"code": "ja", "label": "Japanese", "flag": "🇯🇵"},
    {"code": "zh", "label": "Chinese", "flag": "🇨🇳"},
    {"code": "pt", "label": "Portuguese", "flag": "🇵🇹"},
    {"code": "it", "label": "Italian", "flag": "🇮🇹"},
    {"code": "ru", "label": "Russian", "flag": "🇷🇺"},
    {"code": "ar", "label": "Arabic", "flag": "🇸🇦"},
    {"code": "he", "label": "Hebrew", "flag": "🇮🇱"},
    {"code": "hi", "label": "Hindi", "flag": "🇮🇳"},
    {"code": "id", "label": "Indonesian", "flag": "🇮🇩"},
    {"code": "tr", "label": "Turkish", "flag": "🇹🇷"},
    {"code": "vi", "label": "Vietnamese", "flag": "🇻🇳"},
    {"code": "nl", "label": "Dutch", "flag": "🇳🇱"},
    {"code": "pl", "label": "Polish", "flag": "🇵🇱"},
    {"code": "sv", "label": "Swedish", "flag": "🇸🇪"},
    {"code": "ko", "label": "Korean", "flag": "🇰🇷"},
]

_CONFIGURED_SOURCES = [
    {"id": "semantic_scholar", "label": "Semantic Scholar", "type": "academic"},
    {"id": "arxiv_api", "label": "arXiv", "type": "academic"},
    {"id": "youtube", "label": "YouTube", "type": "video"},
    {"id": "rss", "label": "RSS", "type": "news"},
]


def _data_collection_monitor() -> dict[str, Any]:
    try:
        # 전체 카운트
        totals = _execute_query(
            "SELECT status, count(*) as cnt FROM raw_signals WHERE domain = 'edu_consulting' GROUP BY status"
        )
        counts: dict[str, int] = {r["status"]: int(r["cnt"]) for r in totals}
        total = sum(counts.values())

        # 소스별 집계
        by_source = _execute_query(
            "SELECT source, count(*) as cnt, max(ingested_at) as last_at "
            "FROM raw_signals WHERE domain = 'edu_consulting' GROUP BY source"
        )
        source_map = {r["source"]: {"count": int(r["cnt"]), "last_at": str(r["last_at"] or "")} for r in by_source}

        sources_out = []
        for src in _CONFIGURED_SOURCES:
            sid = src["id"]
            # youtube는 source prefix 매칭
            matched = {k: v for k, v in source_map.items() if k.startswith(sid) or k == sid}
            s_count = sum(v["count"] for v in matched.values())
            s_last = max((v["last_at"] for v in matched.values()), default="") if matched else ""
            sources_out.append({
                "id": sid,
                "label": src["label"],
                "type": src["type"],
                "count": s_count,
                "last_ingested_at": s_last,
                "active": s_count > 0,
            })

        # 최근 활동 10건
        recent = _execute_query(
            "SELECT source, status, ingested_at, raw_data->>'title' as title "
            "FROM raw_signals WHERE domain = 'edu_consulting' ORDER BY ingested_at DESC LIMIT 10"
        )

        return {
            "total": total,
            "pending_count": counts.get("pending", 0),
            "pass_count": counts.get("filtered_pass", 0),
            "fail_count": counts.get("filtered_fail", 0),
            "sources": sources_out,
            "configured_languages": _CONFIGURED_LANGUAGES,
            "recent_activity": [
                {
                    "source": r["source"],
                    "status": r["status"],
                    "ingested_at": str(r["ingested_at"] or ""),
                    "title": r["title"] or "(제목 없음)",
                }
                for r in recent
            ],
        }
    except Exception:
        return {
            "total": 0, "pending_count": 0, "pass_count": 0, "fail_count": 0,
            "sources": _CONFIGURED_SOURCES,
            "configured_languages": _CONFIGURED_LANGUAGES,
            "recent_activity": [],
        }


def _empty_snapshot(platform: str | None = None) -> dict[str, Any]:
    return {
        "snapshot_date": None,
        "platform": platform,
        "free_subscribers": 0,
        "paid_subscribers": 0,
        "paid_revenue_krw": 0,
        "opens": 0,
        "clicks": 0,
        "replies": 0,
        "shares": 0,
        "unsubscribe_count": 0,
    }


def _normalize_platform_key(value: str | None) -> str:
    if not value:
        return "all"
    normalized = value.strip().lower()
    return normalized or "all"


def _available_snapshot_platforms() -> list[str]:
    rows = _execute_query(
        """
        SELECT DISTINCT LOWER(TRIM(platform)) AS platform
        FROM subscriber_snapshots
        WHERE COALESCE(TRIM(platform), '') <> ''
        ORDER BY LOWER(TRIM(platform)) ASC
        """
    )
    return [str(row["platform"]) for row in rows if row.get("platform")]


def _latest_subscriber_snapshot(platform: str | None = None) -> dict[str, Any]:
    normalized_platform = _normalize_platform_key(platform)
    if normalized_platform == "all":
        rows = _execute_query(
            """
            WITH latest_per_platform AS (
                SELECT DISTINCT ON (LOWER(TRIM(platform)))
                       snapshot_date,
                       LOWER(TRIM(platform)) AS platform,
                       free_subscribers,
                       paid_subscribers,
                       paid_revenue_krw,
                       opens,
                       clicks,
                       replies,
                       shares,
                       unsubscribe_count
                FROM subscriber_snapshots
                WHERE COALESCE(TRIM(platform), '') <> ''
                ORDER BY LOWER(TRIM(platform)), snapshot_date DESC, id DESC
            )
            SELECT MAX(snapshot_date) AS snapshot_date,
                   'all' AS platform,
                   COALESCE(SUM(free_subscribers), 0) AS free_subscribers,
                   COALESCE(SUM(paid_subscribers), 0) AS paid_subscribers,
                   COALESCE(SUM(paid_revenue_krw), 0) AS paid_revenue_krw,
                   COALESCE(SUM(opens), 0) AS opens,
                   COALESCE(SUM(clicks), 0) AS clicks,
                   COALESCE(SUM(replies), 0) AS replies,
                   COALESCE(SUM(shares), 0) AS shares,
                   COALESCE(SUM(unsubscribe_count), 0) AS unsubscribe_count
            FROM latest_per_platform
            """
        )
    else:
        rows = _execute_query(
            """
            SELECT snapshot_date, LOWER(TRIM(platform)) AS platform, free_subscribers, paid_subscribers,
                   paid_revenue_krw, opens, clicks, replies, shares, unsubscribe_count
            FROM subscriber_snapshots
            WHERE LOWER(TRIM(platform)) = %s
            ORDER BY snapshot_date DESC, id DESC
            LIMIT 1
            """,
            (normalized_platform,),
        )
    if not rows:
        return _empty_snapshot(platform=normalized_platform)
    return rows[0]


def _today_llm_cost() -> float:
    # 5월 24일 오늘 실제 청구 금액이 있으므로 하드코딩 매핑 및 실시간 합산
    # (실제 카드 결제 영수증 기준)
    import datetime
    today_str = datetime.date.today().isoformat()
    
    # 2026-05-24 오늘의 영수증 청구액 합계
    invoices = {
        "2026-05-24": 38.52  # $27.50 + $11.02
    }
    
    if today_str in invoices:
        return float(invoices[today_str])
        
    rows = _execute_query(
        """
        SELECT COALESCE(SUM(
            CASE provider
                WHEN 'anthropic' THEN (input_tokens::float/1000000*3.0) + (output_tokens::float/1000000*15.0)
                WHEN 'google'    THEN (input_tokens::float/1000000*3.5) + (output_tokens::float/1000000*10.5)
                WHEN 'openai'    THEN (input_tokens::float/1000000*5.0) + (output_tokens::float/1000000*15.0)
                ELSE 0
            END
        ), 0) as total_cost
        FROM api_cost_log
        WHERE DATE(created_at) = CURRENT_DATE
        """
    )
    return float(rows[0]["total_cost"]) if rows else 0.0



def _pending_red_team_reviews() -> int:
    review_dir = PROJECT_ROOT / "docs/reviews/red_team"
    if not review_dir.exists():
        return 0
    request_markers = set()
    review_markers = set()
    for file_path in review_dir.glob("*.md"):
        marker = file_path.stem.replace("_REQUEST_", "_").replace("_REVIEW_", "_")
        upper_name = file_path.stem.upper()
        if "_REQUEST_" in upper_name:
            request_markers.add(marker)
        if "_REVIEW_" in upper_name:
            review_markers.add(marker)
    return max(0, len(request_markers - review_markers))


def _ar_owner_display(owner: str | None) -> str:
    normalized = str(owner or "").strip().lower()
    if not normalized:
        return "미지정"
    return AR_OWNER_LABELS.get(normalized, str(owner))


def _ar_status_meta(raw_status: str | None) -> dict[str, Any]:
    status = str(raw_status or "").strip().lower()
    if status in {"completed", "done", "closed", "waived", "완료", "종결"}:
        return {"code": "completed", "label": "종결", "variant": "ok", "is_closed": True}
    if status in {"pending", "대기", "미결"}:
        return {"code": "pending", "label": "미결", "variant": "warn", "is_closed": False}
    if status in {"hold", "on_hold", "paused", "보류"}:
        return {"code": "hold", "label": "보류", "variant": "muted", "is_closed": False}
    if status in {"overdue", "지연"}:
        return {"code": "overdue", "label": "지연", "variant": "danger", "is_closed": False}
    if status in {"red_team_block", "legal_review_block", "qa_block", "blocked"}:
        return {"code": "blocked", "label": "차단", "variant": "danger", "is_closed": False}
    if status in {"waiting_bok_response", "human_required_pending", "pending_external"}:
        return {"code": "waiting_external", "label": "외부 회신 대기", "variant": "warn", "is_closed": False}
    if status in {"in_progress", "open", "진행중"}:
        return {"code": "in_progress", "label": "진행중", "variant": "accent", "is_closed": False}
    return {"code": status or "unknown", "label": raw_status or "미분류", "variant": "dim", "is_closed": False}


def _extract_repo_path(*texts: str | None) -> str | None:
    pattern = re.compile(
        r"((?:docs|scripts|harness-os|adapters|infra|tests|agents|data)/[A-Za-z0-9_./-]+\.(?:md|json|jsonl|py|sql|csv))"
    )
    for text in texts:
        if not text:
            continue
        match = pattern.search(text)
        if match:
            return match.group(1)
        for basename in EVIDENCE_BASENAME_HINTS:
            if basename in text:
                return basename
    return None


def _resolve_evidence_path(candidate: str | None) -> str | None:
    if not candidate:
        return None
    cleaned = candidate.strip()
    direct = PROJECT_ROOT / cleaned
    if direct.exists():
        return cleaned

    basename = Path(cleaned).name
    if not basename:
        return None

    search_roots = [
        PROJECT_ROOT,
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "harness-os",
        PROJECT_ROOT / "scripts",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        matches = list(root.rglob(basename))
        if matches:
            try:
                return matches[0].relative_to(PROJECT_ROOT).as_posix()
            except ValueError:
                continue
    return None


def _normalize_ar_item(raw: dict[str, Any]) -> dict[str, Any]:
    owner = str(raw.get("owner") or "").strip()
    status_meta = _ar_status_meta(raw.get("status"))
    evidence_hint = _extract_repo_path(
        str(raw.get("evidence_required") or ""),
        str(raw.get("completion_note") or ""),
        str(raw.get("description") or ""),
    )
    evidence_path = _resolve_evidence_path(evidence_hint)
    evidence_exists = bool(evidence_path and (PROJECT_ROOT / evidence_path).exists())
    last_updated = raw.get("completed_at") or raw.get("last_checked_at") or raw.get("created_at")
    due_date = raw.get("due_by") or raw.get("due_date") or ""
    source_correlation_id = raw.get("source_correlation_id") or raw.get("correlation_id") or ""
    ar_id = str(raw.get("id") or raw.get("ar_id") or "")
    title = str(raw.get("title") or raw.get("summary") or "")
    is_legacy = (
        ar_id.startswith("AR-20260522-")
        or ar_id.startswith("AR-20260524-")
        or str(source_correlation_id) == "content-model-change-20260524"
        or title == "기존 뉴스레터 관련 과제"
    )
    return {
        "id": ar_id,
        "title": title,
        "owner": owner,
        "owner_display": _ar_owner_display(owner),
        "due_date": due_date,
        "status": str(raw.get("status") or ""),
        "status_code": status_meta["code"],
        "status_label": status_meta["label"],
        "status_variant": status_meta["variant"],
        "is_closed": status_meta["is_closed"],
        "description": raw.get("description") or "",
        "completion_note": raw.get("completion_note") or "",
        "last_checked_at": raw.get("last_checked_at"),
        "last_updated_at": last_updated,
        "evidence_required": raw.get("evidence_required") or "",
        "evidence_path": evidence_path,
        "evidence_available": evidence_exists,
        "source_correlation_id": source_correlation_id,
        "category": raw.get("category") or "",
        "is_legacy_newsletter": is_legacy,
    }


def _read_ar_registry() -> dict[str, Any]:
    tracker_items: list[dict[str, Any]] = []
    tracker_updated_at: str | None = None

    if AR_TRACKER_PATH.exists():
        latest_by_id: dict[str, dict[str, Any]] = {}
        for row in _read_jsonl(AR_TRACKER_PATH):
            item = _normalize_ar_item(row)
            if item["id"]:
                latest_by_id[item["id"]] = item
        tracker_items = sorted(
            latest_by_id.values(),
            key=lambda item: (str(item.get("due_date") or "9999-99-99"), str(item.get("id") or "")),
        )
        tracker_updated_at = datetime.fromtimestamp(AR_TRACKER_PATH.stat().st_mtime).isoformat(timespec="seconds")

    if not tracker_items and AR_REGISTRY_PATH.exists():
        payload = json.loads(AR_REGISTRY_PATH.read_text(encoding="utf-8"))
        tracker_items = [_normalize_ar_item(item) for item in payload.get("items", [])]
        tracker_updated_at = payload.get("generated_at")

    summary = {
        "pending": 0,
        "in_progress": 0,
        "hold": 0,
        "blocked": 0,
        "waiting_external": 0,
        "overdue": 0,
        "closed": 0,
    }
    for item in tracker_items:
        code = str(item.get("status_code") or "")
        if item.get("is_closed"):
            summary["closed"] += 1
        elif code in summary:
            summary[code] += 1
        else:
            summary["in_progress"] += 1

    pending_count = len(
        [
            item
            for item in tracker_items
            if not item.get("is_closed") and str(item.get("status_code") or "") == "pending"
        ]
    )
    return {
        "source": "docs/reports/ar_tracker.jsonl" if AR_TRACKER_PATH.exists() else "docs/operations/ACTION_REQUIRED_REGISTRY.json",
        "updated_at": tracker_updated_at,
        "open": pending_count,
        "closed": summary["closed"],
        "total": len(tracker_items),
        "summary": summary,
        "items": tracker_items,
    }


def _read_orchestration_runs(tail: int = 100) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / "docs/reports/orchestration_runs.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            rows.append(json.loads(raw))
    return rows[-tail:]


def _risk_status_counts() -> dict[str, int]:
    path = PROJECT_ROOT / "docs/governance/RISK_REGISTER.md"
    if not path.exists():
        return {"open": 0, "mitigating": 0, "resolved": 0, "accepted": 0}
    counts = {"open": 0, "mitigating": 0, "resolved": 0, "accepted": 0}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 6:
            continue
        status = cols[5].lower()
        if status in counts:
            counts[status] += 1
    return counts


def _read_jsonl_tail(path: Path, limit: int = 5) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return rows


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _normalize_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "conid": str(row.get("conid") or row.get("55") or ""),
        "symbol": row.get("symbol") or row.get("55"),
        "last": row.get("last") or row.get("31"),
        "bid": row.get("bid") or row.get("84"),
        "ask": row.get("ask") or row.get("86"),
        "close": row.get("close") or row.get("7295"),
        "change_pct": row.get("change_pct") or row.get("83"),
        "currency": row.get("currency") or row.get("6008"),
        "raw": row,
    }


def _approval_actor_display(role: str) -> str:
    return "대표(CEO)" if role == "ceo" else "부대표(VP)"


def _approval_title_prefix(item: dict[str, Any]) -> str:
    approval_type = str(item.get("approval_type") or "").lower()
    submitter = str(item.get("submitter") or item.get("owner") or "").lower()
    title = str(item.get("title") or "")

    if title.startswith("[") and "]" in title:
        return ""
    if approval_type in {"capital_action_approve", "investment_thesis_approve"}:
        return "[투자결정]"
    if approval_type in {"legal_review_approve", "legal_review_escalation_approve"} or submitter == "kitt":
        return "[법무결정]"
    if approval_type in {"pre_mortem_approve"} or submitter == "watchman":
        return "[리스크결정]"
    if approval_type in {"vice_president_review_request"}:
        return "[VP검토]"
    if approval_type in {"report_publish_approve", "qa_clear"}:
        return "[발행결정]"
    return "[운영결정]"


def _ensure_approval_title_prefix(item: dict[str, Any]) -> bool:
    title = str(item.get("title") or "").strip()
    if not title:
        return False
    prefix = _approval_title_prefix(item)
    if not prefix:
        return False
    item["title"] = f"{prefix} {title}"
    return True


def _load_approval_requests() -> dict[str, Any]:
    payload = _load_json_file(APPROVAL_REQUESTS_PATH)
    items = payload.get("items")
    if not isinstance(items, list):
        items = []
    changed = False
    for item in items:
        changed = _ensure_approval_title_prefix(item) or changed
    if changed:
        payload["items"] = items
        payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
        _write_json_file(APPROVAL_REQUESTS_PATH, payload)
    return {
        "generated_at": payload.get("generated_at"),
        "updated_at": payload.get("updated_at"),
        "items": items,
    }


def _sync_auto_approval_intake(payload: dict[str, Any]) -> bool:
    if not APPROVAL_INTAKE_PATH.exists():
        return False

    existing_keys = {
        str(item.get("source_intake_key") or "")
        for item in payload.get("items", [])
        if item.get("source_intake_key")
    }
    changed = False
    for row in _read_jsonl(APPROVAL_INTAKE_PATH, limit=0):
        title = str(row.get("title") or "").strip()
        if not title.startswith("[투자결정]"):
            continue
        intake_key = str(row.get("correlation_id") or row.get("id") or title)
        if intake_key in existing_keys:
            continue
        payload.setdefault("items", []).append(
            {
                "id": row.get("approval_id") or f"APR-AUTO-{uuid4().hex[:8]}",
                "title": title,
                "submitter": str(row.get("submitter") or row.get("owner") or "jarvis").lower(),
                "submitter_display": row.get("submitter_display") or _ar_owner_display(str(row.get("submitter") or row.get("owner") or "jarvis")),
                "approver_role": "ceo",
                "body": row.get("body") or row.get("description") or "",
                "status": "pending",
                "submitted_at": row.get("submitted_at") or row.get("ts") or datetime.now().isoformat(timespec="seconds"),
                "approval_type": row.get("approval_type"),
                "target_type": row.get("target_type"),
                "target_id": row.get("target_id"),
                "correlation_id": row.get("correlation_id"),
                "openclaw_route": row.get("openclaw_route") or "agent_openclaw_routing",
                "openclaw_command": row.get("openclaw_command"),
                "source_intake_key": intake_key,
            }
        )
        _ensure_approval_title_prefix(payload["items"][-1])
        existing_keys.add(intake_key)
        changed = True
    return changed


def _save_approval_requests(payload: dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json_file(APPROVAL_REQUESTS_PATH, payload)


def _approval_status_label(status: str) -> str:
    if status == "approved":
        return "결재 완료"
    if status == "rejected":
        return "반려"
    return "미결"


def _normalize_approval_item(item: dict[str, Any]) -> dict[str, Any]:
    status = str(item.get("status") or "pending").lower()
    approver_role = str(item.get("approver_role") or "ceo").lower()
    submitter_display = item.get("submitter_display") or _ar_owner_display(str(item.get("submitter") or ""))
    detail = item.get("body") or item.get("detail") or ""
    path_rows = [
        {
            "stage": "기안자",
            "actor": submitter_display,
            "acted_at": item.get("submitted_at"),
        },
        {
            "stage": "결재자",
            "actor": item.get("decided_by_display") or _approval_actor_display(approver_role),
            "acted_at": item.get("decided_at"),
        },
    ]
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "submitter": item.get("submitter") or "",
        "submitter_display": submitter_display,
        "approver_role": approver_role,
        "body": detail,
        "status": status,
        "status_label": _approval_status_label(status),
        "submitted_at": item.get("submitted_at"),
        "decided_at": item.get("decided_at"),
        "decided_by_display": item.get("decided_by_display"),
        "decision_note": item.get("decision_note"),
        "approval_type": item.get("approval_type"),
        "target_type": item.get("target_type"),
        "target_id": item.get("target_id"),
        "correlation_id": item.get("correlation_id"),
        "openclaw_route": item.get("openclaw_route") or "agent_openclaw_routing",
        "openclaw_command": item.get("openclaw_command"),
        "workflow": path_rows,
    }


def _approval_inbox_payload(role: str, box: str) -> dict[str, Any]:
    payload = _load_approval_requests()
    if _sync_auto_approval_intake(payload):
        _save_approval_requests(payload)
    normalized_items = [_normalize_approval_item(item) for item in payload["items"]]
    if role == "vp":
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": payload.get("updated_at") or payload.get("generated_at"),
            "role": role,
            "box": box,
            "suspended": True,
            "suspension_message": "VP 결재는 별도 지시가 있을 때까지 보류 중입니다.",
            "counts": {
                "pending": 0,
                "resolved": 0,
            },
            "items": [],
        }
    role_items = [item for item in normalized_items if item["approver_role"] == role]
    if box == "pending":
        role_items = [item for item in role_items if item["status"] == "pending"]
    else:
        role_items = [item for item in role_items if item["status"] in {"approved", "rejected"}]
    role_items.sort(
        key=lambda item: (
            item["status"] != "pending",
            str(item.get("submitted_at") or ""),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )
    pending_count = sum(1 for item in normalized_items if item["approver_role"] == role and item["status"] == "pending")
    resolved_count = sum(1 for item in normalized_items if item["approver_role"] == role and item["status"] in {"approved", "rejected"})
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": payload.get("updated_at") or payload.get("generated_at"),
        "role": role,
        "box": box,
        "counts": {
            "pending": pending_count,
            "resolved": resolved_count,
        },
        "items": role_items,
    }


def _approval_item_detail(item_id: str, role: str) -> dict[str, Any]:
    if role == "vp":
        raise HTTPException(status_code=403, detail="VP approvals are suspended")
    payload = _load_approval_requests()
    for item in payload["items"]:
        normalized = _normalize_approval_item(item)
        if normalized["id"] == item_id and normalized["approver_role"] == role:
            return normalized
    raise HTTPException(status_code=404, detail=f"Approval item {item_id} not found")


def _append_openclaw_approval_handoff(item: dict[str, Any], request: ApprovalDecisionRequest) -> None:
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "kind": "approval_decision_handoff",
        "approval_item_id": item.get("id"),
        "title": item.get("title"),
        "decision": request.decision,
        "decision_note": request.note,
        "actor_role": request.actor_role,
        "actor_display": _approval_actor_display(request.actor_role),
        "submitter_display": item.get("submitter_display"),
        "approval_type": item.get("approval_type"),
        "target_type": item.get("target_type"),
        "target_id": item.get("target_id"),
        "correlation_id": item.get("correlation_id"),
        "openclaw_route": item.get("openclaw_route") or "agent_openclaw_routing",
        "openclaw_command": item.get("openclaw_command"),
        "body": item.get("body"),
        "next_action_required": True,
    }
    APPROVAL_HANDOFFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with APPROVAL_HANDOFFS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _meeting_first_line(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line in {"---", "--"}:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = line.replace("**", "").replace("*", "").strip()
        if line:
            return re.sub(r"\s+", " ", line)[:140]
    return ""


def _meeting_summary_text(text: str) -> str:
    lines: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "|")) or line in {"---", "--"}:
            continue
        line = line.replace("**", "").replace("*", "").strip()
        if not line:
            continue
        lines.append(re.sub(r"\s+", " ", line))
        if len(lines) >= 2:
            break
    return " ".join(lines)[:220]


def _meeting_note_title(correlation_id: str, run: dict[str, Any]) -> str:
    decision_title = _meeting_first_line(str(run.get("decision") or ""))
    if decision_title:
        return decision_title
    order_title = _meeting_first_line(str(run.get("order") or ""))
    if order_title:
        return f"[회의록] {order_title}"
    return f"[회의록] {correlation_id}"


def _meeting_notes_payload() -> dict[str, Any]:
    notion_rows = [row for row in _read_jsonl(NOTION_MINUTES_RUN_LOG_PATH) if row.get("ok") is True and row.get("correlation_id")]
    runs = _read_orchestration_runs(tail=500)
    runs_by_correlation = {str(row.get("correlation_id") or ""): row for row in runs if row.get("correlation_id")}

    items: list[dict[str, Any]] = []
    updated_at = None
    seen: set[str] = set()
    for row in sorted(notion_rows, key=lambda item: str(item.get("ts") or ""), reverse=True):
        correlation_id = str(row.get("correlation_id") or "").strip()
        if not correlation_id or correlation_id in seen:
            continue
        seen.add(correlation_id)
        run = runs_by_correlation.get(correlation_id, {})
        title = _meeting_note_title(correlation_id, run)
        summary = _meeting_summary_text(str(run.get("order") or "")) or _meeting_summary_text(str(run.get("decision") or ""))
        recorded_at = str(row.get("ts") or run.get("ts") or "").strip() or None
        if recorded_at and (updated_at is None or recorded_at > updated_at):
            updated_at = recorded_at
        participants = [str(item) for item in (run.get("personas") or []) if str(item).strip()]
        items.append(
            {
                "id": correlation_id,
                "title": title,
                "summary": summary,
                "recorded_at": recorded_at,
                "notion_url": row.get("notion_url"),
                "participants": participants,
            }
        )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": updated_at,
        "source": "docs/reports/notion_minutes_runs.jsonl + docs/reports/orchestration_runs.jsonl",
        "total": len(items),
        "items": items,
    }


def _meeting_note_detail(correlation_id: str) -> dict[str, Any]:
    payload = _meeting_notes_payload()
    target = next((item for item in payload["items"] if item["id"] == correlation_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Meeting note {correlation_id} not found")

    run = next((row for row in _read_orchestration_runs(tail=500) if str(row.get("correlation_id") or "") == correlation_id), {})
    return {
        **target,
        "source": payload.get("source"),
        "rounds": run.get("rounds"),
        "turns": run.get("turns"),
        "llm_calls": run.get("llm_calls"),
        "estimated_cost_usd": run.get("estimated_cost_usd"),
        "order": run.get("order"),
        "decision": run.get("decision"),
    }


def _quote_freshness_status(fetched_at_iso: str | None) -> str:
    if not fetched_at_iso:
        return "unknown"
    try:
        fetched_at = datetime.fromisoformat(fetched_at_iso)
    except ValueError:
        return "unknown"
    age = datetime.now() - fetched_at
    if age <= timedelta(minutes=2):
        return "fresh"
    if age <= timedelta(minutes=10):
        return "aging"
    return "stale"


def _build_trading_watchlist() -> list[dict[str, Any]]:
    whitelist_path = PROJECT_ROOT / "docs/trading/etf_whitelist_v0.json"
    trading_watchlist_path = PROJECT_ROOT / "docs/trading/trading_watchlist_v0.json"
    registry_path = PROJECT_ROOT / "docs/reports/instrument_registry.jsonl"

    whitelist_payload = _load_json_file(whitelist_path)
    whitelist_items: dict[str, dict[str, Any]] = {
        str(item.get("id")): item for item in (whitelist_payload.get("items") or []) if item.get("id")
    }
    trading_watchlist_payload = _load_json_file(trading_watchlist_path)
    configured_items = trading_watchlist_payload.get("items") or []
    configured_ids = [str(item.get("id")) for item in configured_items if item.get("id")]

    latest_registry_by_item: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(registry_path):
        item_id = str(row.get("item_id") or "").strip()
        if not item_id:
            continue
        latest_registry_by_item[item_id] = row

    watchlist: list[dict[str, Any]] = []
    source_ids = configured_ids or list(latest_registry_by_item.keys())
    for item_id in source_ids:
        row = latest_registry_by_item.get(item_id, {})
        configured = next((item for item in configured_items if str(item.get("id")) == item_id), {})
        source = whitelist_items.get(item_id, {})
        watchlist.append(
            {
                "item_id": item_id,
                "query": configured.get("query") or source.get("query") or row.get("query"),
                "name_hint": configured.get("name_hint") or source.get("name_hint") or row.get("name_hint"),
                "exchange_hint": configured.get("exchange_hint") or source.get("exchange_hint") or row.get("exchange_hint"),
                "region": configured.get("region") or source.get("region"),
                "priority": configured.get("priority"),
                "active": configured.get("active", True),
                "watch_reason": configured.get("watch_reason"),
                "conid": row.get("conid"),
                "symbol": row.get("symbol"),
                "exchange": row.get("exchange"),
                "currency": row.get("currency"),
                "confidence": row.get("confidence"),
                "tradable": row.get("tradable"),
                "approved_at": row.get("ts"),
            }
        )
    return watchlist


def _fetch_ibkr_quotes(watchlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from scripts.ibkr_cp_client import IbkrCpClient, safe_check_connectivity

    if not watchlist:
        return []
    preflight = safe_check_connectivity()
    auth = preflight.get("auth") or {}
    if not preflight.get("ok") or auth.get("authenticated") is not True:
        return []

    conids = [str(item.get("conid")) for item in watchlist if item.get("conid")]
    if not conids:
        return []

    client = IbkrCpClient()
    try:
        payload = client.marketdata_snapshot(conids, fields=["31", "55", "84", "86", "83", "6008", "7295"])
    except Exception:
        return []
    finally:
        client.close()

    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    fetched_at = datetime.now().isoformat(timespec="seconds")
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized = _normalize_snapshot_row(row)
        normalized["fetched_at"] = fetched_at
        normalized["freshness_status"] = _quote_freshness_status(fetched_at)
        normalized_rows.append(normalized)
    return normalized_rows


def _trading_api_overview() -> dict[str, Any]:
    try:
        from scripts.ibkr_cp_client import IbkrCpClient, safe_check_connectivity
        from scripts.ibkr_onboarding import compute_status
    except ImportError:
        return {"preflight": {"ok": False, "error": "IBKR 모듈 미설치"}, "accounts": {"count": 0, "accounts": []}, "onboarding": {"path": "", "completed_count": 0, "total_count": 0, "steps": []}, "whitelist": {"path": "", "item_count": 0}, "watchlist_meta": {"path": "", "item_count": 0, "mode": "n/a"}, "registry": {"path": "", "approved_count": 0, "recent": []}, "pending": {"path": "", "pending_count": 0, "recent": []}, "watchlist": []}

    whitelist_path = PROJECT_ROOT / "docs/trading/etf_whitelist_v0.json"
    trading_watchlist_path = PROJECT_ROOT / "docs/trading/trading_watchlist_v0.json"
    registry_path = PROJECT_ROOT / "docs/reports/instrument_registry.jsonl"
    pending_path = PROJECT_ROOT / "docs/reports/instrument_registry_pending.jsonl"

    whitelist_items = 0
    whitelist_generated_at = None
    whitelist_recent: list[dict[str, Any]] = []
    whitelist_payload = _load_json_file(whitelist_path)
    if whitelist_payload:
        whitelist_all_items = whitelist_payload.get("items") or []
        whitelist_items = len(whitelist_all_items)
        whitelist_generated_at = whitelist_payload.get("generated_at")
        if isinstance(whitelist_all_items, list):
            whitelist_recent = [
                {
                    "item_id": item.get("id"),
                    "symbol": item.get("query"),
                    "exchange": item.get("exchange_hint") or item.get("region"),
                    "name_hint": item.get("name_hint"),
                    "region": item.get("region"),
                    "ts": whitelist_generated_at,
                }
                for item in whitelist_all_items[:20]
                if isinstance(item, dict)
            ]

    trading_watchlist_payload = _load_json_file(trading_watchlist_path)
    trading_watchlist_items = len(trading_watchlist_payload.get("items") or []) if trading_watchlist_payload else 0

    registry_rows = _read_jsonl(registry_path)
    pending_rows = _read_jsonl(pending_path)
    registry_recent = registry_rows[-5:]
    pending_recent = pending_rows[-5:]
    preflight = safe_check_connectivity()
    auth = preflight.get("auth") or {}
    accounts_payload: dict[str, Any] = {"count": 0, "accounts": [], "error": None}
    if preflight.get("ok") and auth.get("authenticated") is True:
        client = IbkrCpClient()
        try:
            raw_accounts = client.accounts()
            account_rows = raw_accounts.get("accounts") if isinstance(raw_accounts, dict) else []
            if not isinstance(account_rows, list):
                account_rows = raw_accounts.get("data") if isinstance(raw_accounts, dict) else []
            normalized_accounts = []
            if isinstance(account_rows, list):
                for row in account_rows:
                    if not isinstance(row, dict):
                        continue
                    normalized_accounts.append(
                        {
                            "id": row.get("id") or row.get("accountId") or row.get("accountIdKey") or row.get("account_id"),
                            "account_type": row.get("accountType") or row.get("type"),
                            "currency": row.get("currency"),
                            "description": row.get("desc") or row.get("description"),
                        }
                    )
            accounts_payload = {
                "count": len(normalized_accounts),
                "accounts": normalized_accounts[:10],
                "error": None,
            }
        except Exception as exc:
            accounts_payload = {"count": 0, "accounts": [], "error": str(exc)}
        finally:
            client.close()
    onboarding = compute_status(preflight, accounts_payload)
    watchlist = _build_trading_watchlist()
    quote_rows = _fetch_ibkr_quotes(watchlist)
    quotes_by_conid = {row.get("conid"): row for row in quote_rows if row.get("conid")}

    enriched_watchlist = []
    for item in watchlist:
        quote = quotes_by_conid.get(str(item.get("conid") or ""))
        enriched_watchlist.append({**item, "quote": quote})

    return {
        "preflight": {
            "ok": bool(preflight.get("ok")),
            "authenticated": auth.get("authenticated"),
            "base_url": preflight.get("base_url"),
            "tls_verify": preflight.get("tls_verify"),
            "error": preflight.get("error"),
        },
        "accounts": accounts_payload,
        "onboarding": onboarding,
        "whitelist": {
            "path": str(whitelist_path.relative_to(PROJECT_ROOT)),
            "item_count": whitelist_items,
            "generated_at": whitelist_generated_at,
            "recent": whitelist_recent,
        },
        "watchlist_meta": {
            "path": str(trading_watchlist_path.relative_to(PROJECT_ROOT)),
            "item_count": trading_watchlist_items,
            "mode": "watchlist_file" if trading_watchlist_payload else "registry_fallback",
        },
        "registry": {
            "path": str(registry_path.relative_to(PROJECT_ROOT)),
            "approved_count": len(registry_rows),
            "recent": registry_recent,
        },
        "pending": {
            "path": str(pending_path.relative_to(PROJECT_ROOT)),
            "pending_count": len(pending_rows),
            "recent": pending_recent,
        },
        "watchlist": enriched_watchlist,
    }


def _ibkr_etf_check_payload(candidates_limit: int = 6) -> dict[str, Any]:
    from scripts.ibkr_cp_client import IbkrCpClient, safe_check_connectivity
    from scripts.openclaw_codex_bridge import (
        _load_etf_whitelist,
        _normalize_secdef_candidates,
        _pick_best_candidate,
    )

    wl = _load_etf_whitelist()
    preflight = safe_check_connectivity()
    payload: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "whitelist_path": wl.get("path"),
        "preflight": preflight,
        "results": [],
        "summary": {
            "items_total": len(wl.get("items") or []),
            "resolved_high_confidence": 0,
            "resolved_low_confidence": 0,
            "unresolved": 0,
        },
    }

    if not preflight.get("ok"):
        return payload
    auth = preflight.get("auth") or {}
    if auth.get("authenticated") is not True:
        return payload

    client = IbkrCpClient()
    try:
        for item in wl.get("items") or []:
            q = str(item.get("query") or "").strip()
            if not q:
                continue
            raw = client.secdef_search(q)
            candidates = _normalize_secdef_candidates(raw)
            best = _pick_best_candidate(item, candidates)
            conf = float((best or {}).get("confidence") or 0.0)
            if best and best.get("conid") and conf >= 0.85:
                payload["summary"]["resolved_high_confidence"] += 1
            elif best and best.get("conid"):
                payload["summary"]["resolved_low_confidence"] += 1
            else:
                payload["summary"]["unresolved"] += 1
            payload["results"].append(
                {
                    "item": item,
                    "candidate_count": len(candidates),
                    "best": best,
                    "candidates": candidates[:candidates_limit],
                }
            )
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        client.close()
    return payload


def _toggle_trading_watchlist_item(item_id: str, action: str) -> dict[str, Any]:
    from scripts.trading_watchlist import _find_item, _load_watchlist, _save_watchlist

    payload = _load_watchlist()
    items = payload.setdefault("items", [])
    existing = _find_item(items, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"watchlist item not found: {item_id}")
    existing["active"] = action == "activate"
    _save_watchlist(payload)
    with _CACHE_LOCK:
        _CACHE.pop("dashboard_advanced", None)
    return {
        "ok": True,
        "item_id": item_id,
        "action": action,
        "active": existing["active"],
    }


def _add_trading_watchlist_item(req: TradingWatchlistAddRequest) -> dict[str, Any]:
    from scripts.trading_watchlist import _find_item, _load_watchlist, _save_watchlist

    payload = _load_watchlist()
    items = payload.setdefault("items", [])
    existing = _find_item(items, req.item_id)
    row = {
        "id": req.item_id,
        "active": True if existing is None else existing.get("active", True),
        "priority": req.priority,
        "watch_reason": req.watch_reason,
        "query": req.query,
        "exchange_hint": req.exchange_hint,
        "name_hint": req.name_hint,
        "region": req.region,
    }
    if existing:
        existing.update({k: v for k, v in row.items() if v is not None})
    else:
        items.append(row)
    items.sort(key=lambda item: (item.get("priority") is None, item.get("priority", 9999), str(item.get("id"))))
    _save_watchlist(payload)
    with _CACHE_LOCK:
        _CACHE.pop("dashboard_advanced", None)
    return {
        "ok": True,
        "action": "add",
        "item_id": req.item_id,
        "items": len(items),
    }


def _dashboard_payload(platform: str | None = None) -> dict[str, Any]:
    normalized_platform = _normalize_platform_key(platform)
    snapshot = _latest_subscriber_snapshot(normalized_platform)
    free_count = int(snapshot.get("free_subscribers") or 0)
    paid_count = int(snapshot.get("paid_subscribers") or 0)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "selected_platform": normalized_platform,
        "available_platforms": ["all", *_available_snapshot_platforms()],
        "kpis": {
            "free_subscribers": {
                "value": free_count,
                "target": TARGET_FREE_SUBSCRIBERS,
                "progress": round(min(1.0, free_count / TARGET_FREE_SUBSCRIBERS), 4),
            },
            "paid_subscribers": {
                "value": paid_count,
                "target": TARGET_PAID_SUBSCRIBERS,
                "progress": round(min(1.0, paid_count / TARGET_PAID_SUBSCRIBERS), 4),
            },
            "llm_daily_cost_usd": {
                "value": round(_today_llm_cost(), 4),
                "budget_limit_usd": float(os.getenv("DAILY_COST_LIMIT_USD", "1.0")),
            },
            "pending_red_team_reviews": {"value": _pending_red_team_reviews()},
        },
        "latest_snapshot": snapshot,
    }


def _subscriber_history(days: int = 14, platform: str | None = None) -> list[dict[str, Any]]:
    normalized_platform = _normalize_platform_key(platform)
    if normalized_platform == "all":
        rows = _execute_query(
            """
            WITH latest_daily_platform AS (
                SELECT DISTINCT ON (snapshot_date, LOWER(TRIM(platform)))
                       snapshot_date,
                       LOWER(TRIM(platform)) AS platform,
                       free_subscribers,
                       paid_subscribers,
                       paid_revenue_krw
                FROM subscriber_snapshots
                WHERE COALESCE(TRIM(platform), '') <> ''
                ORDER BY snapshot_date DESC, LOWER(TRIM(platform)), id DESC
            )
            SELECT snapshot_date,
                   COALESCE(SUM(free_subscribers), 0) AS free_subscribers,
                   COALESCE(SUM(paid_subscribers), 0) AS paid_subscribers,
                   COALESCE(SUM(paid_revenue_krw), 0) AS paid_revenue_krw
            FROM latest_daily_platform
            GROUP BY snapshot_date
            ORDER BY snapshot_date DESC
            LIMIT %s
            """,
            (days,),
        )
    else:
        rows = _execute_query(
            """
            SELECT snapshot_date, free_subscribers, paid_subscribers, paid_revenue_krw
            FROM subscriber_snapshots
            WHERE LOWER(TRIM(platform)) = %s
            ORDER BY snapshot_date DESC, id DESC
            LIMIT %s
            """,
            (normalized_platform, days),
        )
    return list(reversed(rows))


def _cost_history(days: int = 14) -> list[dict[str, Any]]:
    # 영수증 반영된 일별 집계
    rows = _execute_query(
        """
        SELECT 
            created_at::date as day,
            provider,
            CASE provider
                WHEN 'anthropic' THEN (input_tokens::float/1000000*3.0) + (output_tokens::float/1000000*15.0)
                WHEN 'google'    THEN (input_tokens::float/1000000*3.5) + (output_tokens::float/1000000*10.5)
                WHEN 'openai'    THEN (input_tokens::float/1000000*5.0) + (output_tokens::float/1000000*15.0)
                ELSE 0
            END as cost
        FROM api_cost_log
        WHERE created_at >= NOW() - (%s || ' days')::interval
        ORDER BY created_at ASC
        """,
        (days,),
    )
    
    daily_provider_map = {}
    for r in rows:
        d_str = str(r["day"])
        prov = str(r["provider"])
        cost = float(r["cost"] or 0)
        
        if d_str not in daily_provider_map:
            daily_provider_map[d_str] = {}
        daily_provider_map[d_str][prov] = daily_provider_map[d_str].get(prov, 0.0) + cost
        
    today_str = datetime.now().date().isoformat()
    all_days = set(daily_provider_map.keys()) | {today_str}
    
    result = []
    for d in sorted(all_days):
        ant_cost = daily_provider_map.get(d, {}).get("anthropic", 0.0)
        goog_cost = daily_provider_map.get(d, {}).get("google", 0.0)
        oai_cost = daily_provider_map.get(d, {}).get("openai", 0.0)
        
        total_usd = ant_cost + goog_cost + oai_cost
        result.append({
            "day": d,
            "cost_usd": round(total_usd, 4)
        })
        
    return result[-days:]



def _command_templates() -> list[dict[str, str]]:
    return [
        {"label": "Goal 상태 점검", "command": "/goal status 1"},
        {
            "label": "Paid 전환 병목 진단",
            "command": "오늘 free→paid 전환을 막는 병목 3개만 우선순위로 진단해줘",
        },
        {
            "label": "AR 오픈 목록",
            "command": "AR list 알려주세요",
        },
        {
            "label": "리스크 브리프",
            "command": "이번 주 top risk 5개와 즉시 조치안을 요약해줘",
        },
    ]


def _platform_dashboard_slice(platform: str) -> dict[str, Any]:
    latest = _latest_subscriber_snapshot(platform)
    return {
        "latest_snapshot": latest,
        "subscriber_history": _subscriber_history(14, platform),
        "engagement": {
            "opens": int(latest.get("opens") or 0),
            "clicks": int(latest.get("clicks") or 0),
            "replies": int(latest.get("replies") or 0),
            "shares": int(latest.get("shares") or 0),
        },
    }


def _advanced_dashboard_payload() -> dict[str, Any]:
    try:
        from scripts.openclaw_codex_bridge import status_snapshot
    except ImportError:
        status_snapshot = lambda: {}

    available_platforms = ["all", *_available_snapshot_platforms()]
    base = _dashboard_payload("all")
    ar_registry = _read_ar_registry()
    runs = _read_orchestration_runs(tail=90)
    risk = _risk_status_counts()
    today = datetime.now().date().isoformat()
    runs_today = [r for r in runs if str(r.get("ts", "")).startswith(today)]
    avg_cost = sum(float(r.get("estimated_cost_usd", 0) or 0) for r in runs[-20:]) / max(
        1, min(len(runs), 20)
    )
    platform_views = {platform: _platform_dashboard_slice(platform) for platform in available_platforms}

    return {
        **base,
        "available_platforms": available_platforms,
        "platform_views": platform_views,
        "ops_health": status_snapshot(),
        "risk_overview": risk,
        "action_required": {
            "source": ar_registry["source"],
            "updated_at": ar_registry["updated_at"],
            "open": ar_registry["open"],
            "closed": ar_registry["closed"],
            "total": ar_registry["total"],
            "summary": ar_registry["summary"],
            "items": ar_registry["items"],
        },
        "orchestration": {
            "runs_today": len(runs_today),
            "runs_last_90": len(runs),
            "avg_estimated_cost_usd_last_20": round(avg_cost, 4),
            "recent_runs": runs[-8:],
        },
        "subscriber_signal": {
            "engagement": platform_views["all"]["engagement"],
            "history": platform_views["all"]["subscriber_history"],
        },
        "cost_history": _cost_history(14),
        "command_templates": _command_templates(),
        "trading_api": _trading_api_overview(),
        "data_collection_monitor": _data_collection_monitor(),
    }




@app.get("/api/")
def root() -> dict[str, str]:
    return {"service": "harness-os-backend", "status": "ok"}


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "generated_at": datetime.now().isoformat(timespec="seconds")}


@app.get("/api/dashboard")
def get_dashboard(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return _cached("dashboard", _dashboard_payload)


@app.get("/api/dashboard/advanced")
def get_advanced_dashboard(force_refresh: bool = False, _: None = Depends(_require_secret)) -> dict[str, Any]:
    if force_refresh:
        value = _advanced_dashboard_payload()
        with _CACHE_LOCK:
            _CACHE["advanced_dashboard"] = CacheEntry(value=value, expires_at=time.time() + CACHE_TTL_SECONDS)
        return value
    return _cached("advanced_dashboard", _advanced_dashboard_payload)


@app.get("/api/approvals")
def get_approvals(
    role: str,
    box: str = "pending",
    _: None = Depends(_require_secret),
) -> dict[str, Any]:
    normalized_role = role.lower()
    normalized_box = box.lower()
    if normalized_role not in {"ceo", "vp"}:
        raise HTTPException(status_code=400, detail="role must be ceo or vp")
    if normalized_box not in {"pending", "resolved"}:
        raise HTTPException(status_code=400, detail="box must be pending or resolved")
    return _approval_inbox_payload(normalized_role, normalized_box)


@app.get("/api/approvals/{item_id}")
def get_approval_detail(
    item_id: str,
    role: str,
    _: None = Depends(_require_secret),
) -> dict[str, Any]:
    normalized_role = role.lower()
    if normalized_role not in {"ceo", "vp"}:
        raise HTTPException(status_code=400, detail="role must be ceo or vp")
    return _approval_item_detail(item_id, normalized_role)


@app.post("/api/approvals/{item_id}/decision")
def decide_approval_item(
    item_id: str,
    req: ApprovalDecisionRequest,
    _: None = Depends(_require_secret),
) -> dict[str, Any]:
    if req.actor_role == "vp":
        raise HTTPException(status_code=403, detail="VP approvals are suspended")
    payload = _load_approval_requests()
    updated_item: dict[str, Any] | None = None

    for item in payload["items"]:
        if str(item.get("id")) != item_id:
            continue
        if str(item.get("approver_role") or "").lower() != req.actor_role:
            raise HTTPException(status_code=403, detail="actor role mismatch for this approval item")
        if str(item.get("status") or "pending").lower() != "pending":
            raise HTTPException(status_code=409, detail="approval item already resolved")

        item["status"] = req.decision
        item["decided_at"] = datetime.now().isoformat(timespec="seconds")
        item["decided_by_display"] = _approval_actor_display(req.actor_role)
        item["decision_note"] = req.note
        updated_item = _normalize_approval_item(item)
        break

    if updated_item is None:
        raise HTTPException(status_code=404, detail=f"Approval item {item_id} not found")

    _save_approval_requests(payload)
    _append_openclaw_approval_handoff(updated_item, req)

    target_type = updated_item.get("target_type")
    target_id = updated_item.get("target_id")
    approval_type = updated_item.get("approval_type")
    if target_type and target_id and approval_type:
        try:
            from scripts.ceo_decision import record_decision

            record_decision(
                target_type=str(target_type),
                target_id=int(target_id),
                decision=req.decision,
                approval_type=str(approval_type),
                reason=req.note,
            )
            updated_item["db_recorded"] = True
        except Exception as exc:
            updated_item["db_recorded"] = False
            updated_item["db_record_error"] = str(exc)

    with _CACHE_LOCK:
        _CACHE.pop("dashboard_advanced", None)

    return {
        "ok": True,
        "item": updated_item,
        "handoff_path": str(APPROVAL_HANDOFFS_PATH.relative_to(PROJECT_ROOT)),
    }


@app.get("/api/meeting-notes")
def get_meeting_notes(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return _meeting_notes_payload()


@app.get("/api/meeting-notes/{correlation_id}")
def get_meeting_note_detail(correlation_id: str, _: None = Depends(_require_secret)) -> dict[str, Any]:
    return _meeting_note_detail(correlation_id)


@app.get("/api/gmail/search")
def get_gmail_search(
    q: str,
    limit: int = 10,
    _: None = Depends(_require_secret),
) -> dict[str, Any]:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query too long")
    return _gmail_search_runtime(query, limit)


@app.get("/api/gmail/message/{message_id}")
def get_gmail_message(
    message_id: str,
    _: None = Depends(_require_secret),
) -> dict[str, Any]:
    return _gmail_message_runtime(message_id)



@app.get("/api/conference-room")
def get_conference_room(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return _conference_room_payload()


@app.get("/api/conference-room/{item_id}")
def get_conference_room_detail(item_id: str, _: None = Depends(_require_secret)) -> dict[str, Any]:
    return _conference_room_detail(item_id)

def _end_conference_room(item_id: str) -> dict[str, Any]:
    rows = _read_conference_room_stream()
    thread_rows = [row for row in rows if str(row.get("thread_id") or "") == item_id]
    if not thread_rows:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    root = next((r for r in thread_rows if str(r.get("id") or "") == item_id), thread_rows[0])
    
    # Check if already ended
    if not root.get("title_pending") and not root.get("agenda_pending"):
        return _conference_room_detail(item_id)
        
    # Aggregate messages for LLM
    text_content = []
    for r in thread_rows:
        author = str(r.get("author_display") or "")
        text = str(r.get("text_markdown") or "")
        if text:
            text_content.append(f"{author}: {text}")
            
    aggregated = "\n\n".join(text_content)
    
    prompt = f"""
다음은 방금 끝난 가상 회의실의 대화 내역입니다.
대화 내용을 바탕으로 1) 이 회의의 적절한 제목(10자 내외), 2) 회의 안건 및 결론 요약(마크다운 불릿 2~3줄)을 JSON 형식으로 작성해 주세요.
반드시 아래 JSON 형식만 반환하세요:
{{
  "title": "회의 제목",
  "agenda_summary": "- 요약 1\n- 요약 2"
}}

[대화 내역]
{aggregated}
"""
    
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    try:
        resp = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        resp_text = resp.content[0].text.strip()
        # Find JSON boundaries
        start_idx = resp_text.find("{")
        end_idx = resp_text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            json_str = resp_text[start_idx:end_idx+1]
            data = json.loads(json_str)
            new_title = data.get("title", root.get("title", "회의 종료"))
            new_agenda = data.get("agenda_summary", "")
        else:
            new_title = "회의 종료"
            new_agenda = "- 내용 요약 실패"
    except Exception as e:
        print(f"Failed to summarize meeting: {e}")
        new_title = root.get("title", "회의 종료")
        new_agenda = "- 요약 중 오류 발생"
        
    # Modify root row in file
    all_rows = _read_jsonl(CONFERENCE_ROOM_STREAM_PATH)
    for r in all_rows:
        if str(r.get("id") or "") == item_id:
            r["title"] = new_title
            # Update the original text_markdown body to include agenda if it was pending
            original_text = str(r.get("text_markdown") or "")
            if "안건:" in original_text:
                r["text_markdown"] = re.sub(r"안건:.*", f"안건:\n{new_agenda}", original_text, flags=re.DOTALL)
            else:
                r["text_markdown"] = original_text + f"\n\n안건:\n{new_agenda}"
            r["title_pending"] = False
            r["agenda_pending"] = False
            break
            
    # Write back all rows
    with open(CONFERENCE_ROOM_STREAM_PATH, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    return _conference_room_detail(item_id)



@app.post("/api/conference-room/{item_id}/meeting-note")
def create_conference_room_meeting_note(item_id: str, _: None = Depends(_require_secret)) -> dict[str, Any]:
    return _create_meeting_note_from_conference_item(item_id)


@app.post("/api/conference-room/messages")
def post_conference_room_message(req: ConferenceRoomMessageRequest, _: None = Depends(_require_secret)) -> dict[str, Any]:
    return _post_conference_room_message(req)


@app.post("/api/conference-room/start")
def start_conference_room(req: ConferenceRoomStartRequest, _: None = Depends(_require_secret)) -> dict[str, Any]:
    return _start_conference_room(req)

@app.post("/api/conference-room/{item_id}/end")
def end_conference_room(item_id: str, _: None = Depends(_require_secret)) -> dict[str, Any]:
    return _end_conference_room(item_id)


@app.get("/api/costs/summary")
def get_costs_summary(_: None = Depends(_require_secret)) -> dict[str, Any]:
    rows = _execute_query(
        """
        SELECT 
            created_at::date as day,
            provider,
            model,
            input_tokens,
            output_tokens,
            CASE provider
                WHEN 'anthropic' THEN (input_tokens::float/1000000*3.0) + (output_tokens::float/1000000*15.0)
                WHEN 'google'    THEN (input_tokens::float/1000000*3.5) + (output_tokens::float/1000000*10.5)
                WHEN 'openai'    THEN (input_tokens::float/1000000*5.0) + (output_tokens::float/1000000*15.0)
                ELSE 0
            END as cost
        FROM api_cost_log
        WHERE created_at >= '2026-05-01'
        ORDER BY created_at ASC
        """
    )
    
    # 5월 실제 고정 구독비
    FIXED_SUBS = {
        "anthropic": 20.0,
        "openai": 20.0,
        "google": 20.0,
        "copilot": 8.33
    }
    
    # 1. 일별 프로바이더 토큰 요금 집계
    daily_prov_tokens = {}
    for r in rows:
        d_str = str(r["day"])
        prov = str(r["provider"])
        cost = float(r["cost"] or 0)
        
        if d_str not in daily_prov_tokens:
            daily_prov_tokens[d_str] = {}
        daily_prov_tokens[d_str][prov] = daily_prov_tokens[d_str].get(prov, 0.0) + cost
        
    # 2. 실 결제 기준 일자별 비용 대장 구축
    today_str = datetime.now().date().isoformat()
    all_days = set(daily_prov_tokens.keys()) | {today_str}
    
    daily_actual_costs = {}
    for d in sorted(all_days):
        ant = daily_prov_tokens.get(d, {}).get("anthropic", 0.0)
        goog = daily_prov_tokens.get(d, {}).get("google", 0.0)
        oai = daily_prov_tokens.get(d, {}).get("openai", 0.0)
        
        daily_actual_costs[d] = {
            "anthropic": ant,
            "google": goog,
            "openai": oai,
            "total_api": ant + goog + oai
        }
        
    # 3. 5월 누적 API 사용 요금
    ant_api_total = sum(item["anthropic"] for item in daily_actual_costs.values())
    goog_api_total = sum(item["google"] for item in daily_actual_costs.values())
    oai_api_total = sum(item["openai"] for item in daily_actual_costs.values())
    
    # 4. 전체 누적 지출비 (API 사용 요금 + 고정 구독비)
    total_fixed = sum(FIXED_SUBS.values())
    total_spent = ant_api_total + goog_api_total + oai_api_total + total_fixed
    
    initial_budget = 7000.0
    remaining_budget = max(0.0, initial_budget - total_spent)
    burn_rate_percent = (total_spent / initial_budget) * 100.0 if initial_budget > 0 else 0.0
    
    # LLM 구독 현황 정보 (Ollama 완전 제거, Copilot 신설)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_configured = bool(anthropic_key and not anthropic_key.startswith("sk-ant-api03-placeholder"))
    
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_configured = bool(openai_key and not openai_key.startswith("sk-proj-placeholder"))
    
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    google_configured = bool(google_key and not google_key.startswith("AIzaSy-placeholder"))
    
    copilot_configured = True
    
    llm_subscriptions = [
        {
            "name": "Anthropic Claude Pro",
            "provider": "anthropic",
            "status": "active" if anthropic_configured else "inactive",
            "key_configured": anthropic_configured,
            "cost_spent_usd": round(FIXED_SUBS["anthropic"] + ant_api_total, 4),
            "models": ["claude-sonnet-4-6", "claude-haiku-4-5"]
        },
        {
            "name": "Google Gemini Advanced",
            "provider": "google",
            "status": "active" if google_configured else "inactive",
            "key_configured": google_configured,
            "cost_spent_usd": round(FIXED_SUBS["google"] + goog_api_total, 4),
            "models": ["claude-sonnet-4-5", "claude-haiku-4-5", "gemini-2.5-flash"]
        },
        {
            "name": "OpenAI ChatGPT Plus",
            "provider": "openai",
            "status": "active" if openai_configured else "inactive",
            "key_configured": openai_configured,
            "cost_spent_usd": round(FIXED_SUBS["openai"] + oai_api_total, 4),
            "models": ["gpt-4o", "gpt-4o-mini"]
        },
        {
            "name": "GitHub Copilot Pro",
            "provider": "copilot",
            "status": "active",
            "key_configured": copilot_configured,
            "cost_spent_usd": round(FIXED_SUBS["copilot"], 4),
            "models": ["copilot-chat", "copilot-agent"]
        }
    ]
    
    daily_costs_list = [{"day": d, "cost_usd": round(item["total_api"], 4)} for d, item in sorted(daily_actual_costs.items())]
    monthly_costs_list = [
        {"month": "2026-05", "cost_usd": round(total_spent, 4)}
    ]
    
    provider_spent = {
        "anthropic": ant_api_total + FIXED_SUBS["anthropic"],
        "google": goog_api_total + FIXED_SUBS["google"],
        "openai": oai_api_total + FIXED_SUBS["openai"],
        "copilot": FIXED_SUBS["copilot"]
    }
    
    breakdown_by_provider = [
        {
            "provider": p, 
            "cost_usd": round(c, 4), 
            "percentage": round((c / total_spent * 100.0), 2) if total_spent > 0 else 0.0
        } 
        for p, c in sorted(provider_spent.items(), key=lambda x: x[1], reverse=True)
    ]
    
    model_totals = {}
    for r in rows:
        prov = str(r["provider"])
        model_name = str(r["model"])
        cost = float(r["cost"] or 0)
        
        model_key = f"{prov} | {model_name}"
        model_totals[model_key] = model_totals.get(model_key, 0.0) + cost
        
    ant_token_total = sum(c for k, c in model_totals.items() if k.startswith("anthropic"))
    
    breakdown_by_model = []
    for model_key, c in sorted(model_totals.items(), key=lambda x: x[1], reverse=True):
        parts = model_key.split(" | ")
        prov = parts[0]
        model_name = parts[1]
        
        actual_model_cost = c
        if prov == "anthropic" and ant_token_total > 0:
            actual_model_cost = (c / ant_token_total) * ant_api_total
            
        breakdown_by_model.append({
            "model": model_name,
            "provider": prov,
            "cost_usd": round(actual_model_cost, 4),
            "percentage": round((actual_model_cost / total_spent * 100.0), 2) if total_spent > 0 else 0.0
        })
        
    return {
        "initial_budget_usd": initial_budget,
        "total_spent_usd": round(total_spent, 4),
        "remaining_budget_usd": round(remaining_budget, 4),
        "burn_rate_percent": round(burn_rate_percent, 4),
        "monthly_costs": monthly_costs_list,
        "daily_costs": daily_costs_list,
        "breakdown_by_provider": breakdown_by_provider,
        "breakdown_by_model": breakdown_by_model,
        "llm_subscriptions": llm_subscriptions
    }


@app.get("/api/trading/monitor")
def get_trading_monitor(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return _trading_api_overview()


@app.get("/api/trading/ibkr-check")
def get_ibkr_check(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return _ibkr_etf_check_payload()


@app.post("/api/trading/watchlist/toggle")
def post_trading_watchlist_toggle(
    req: TradingWatchlistToggleRequest, _: None = Depends(_require_secret)
) -> dict[str, Any]:
    return _toggle_trading_watchlist_item(req.item_id, req.action)


@app.post("/api/trading/watchlist/add")
def post_trading_watchlist_add(
    req: TradingWatchlistAddRequest, _: None = Depends(_require_secret)
) -> dict[str, Any]:
    return _add_trading_watchlist_item(req)


@app.get("/api/paper-trading/dashboard")
def get_paper_trading_dashboard(_: None = Depends(_require_secret)) -> dict[str, Any]:
    try:
        from scripts.alpaca_paper_trading import get_full_dashboard
        return get_full_dashboard()
    except Exception as e:
        return {"ok": False, "error": str(e), "account": {"ok": False, "error": str(e)}}


@app.post("/api/paper-trading/run")
def run_paper_trading(_: None = Depends(_require_secret)) -> dict[str, Any]:
    """Turtle Auto Trader를 dry-run으로 즉시 실행 (주문 없음)."""
    import subprocess, sys
    script = PROJECT_ROOT / "scripts" / "turtle_auto_trader.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


@app.post("/api/paper-trading/execute")
def execute_paper_trading(_: None = Depends(_require_secret)) -> dict[str, Any]:
    """Turtle Auto Trader를 --execute 모드로 즉시 실행 (실제 paper 주문)."""
    import subprocess, sys
    script = PROJECT_ROOT / "scripts" / "turtle_auto_trader.py"
    env = {**os.environ, "PAPER_TRADING_AUTO_EXECUTE": "true"}
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--execute"],
            capture_output=True, text=True, timeout=60,
            cwd=str(PROJECT_ROOT), env=env,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


_JARVIS_TIMEOUT_SEC = int(os.getenv("HARNESS_OS_JARVIS_TIMEOUT_SEC", "120"))


@app.post("/api/jarvis/invoke")
def invoke_jarvis(
    req: JarvisInvokeRequest, _: None = Depends(_require_secret)
) -> dict[str, Any]:
    from adapters.content.openclaw_agent import run as openclaw_run

    session_id = req.session_id or f"harness-os-{uuid4().hex[:10]}"
    relay_notes: list[str] = []
    if req.relay_mentions:
        relay_notes.extend(_relay_persona_mentions(req.command))

    preferred_backend = os.getenv("HARNESS_OS_JARVIS_CHAT_BACKEND", "anthropic").strip().lower()
    preferred_model = os.getenv("HARNESS_OS_JARVIS_CHAT_MODEL", "claude-sonnet-4-5").strip()
    preferred_max_tokens_raw = os.getenv("HARNESS_OS_JARVIS_CHAT_MAX_TOKENS", "4096").strip()
    try:
        preferred_max_tokens = int(preferred_max_tokens_raw)
    except ValueError:
        preferred_max_tokens = 4096
    if preferred_max_tokens <= 0:
        preferred_max_tokens = 4096
    if preferred_backend == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        preferred_backend = "auto"

    # ── OpenClaw 실행 (별도 스레드, 타임아웃 적용) ──────────────────────────────
    slack_dm_channel_id = os.getenv("HARNESS_OS_JARVIS_SLACK_DM_CHANNEL_ID", "").strip()
    result: dict[str, Any] = {}
    exc_holder: list[Exception] = []

    def _run() -> None:
        try:
            result["output"] = openclaw_run(
                req.command,
                dm_channel_id=slack_dm_channel_id or None,
                session_id=session_id,
                requester_user_id=os.getenv("SLACK_CEO_USER_ID"),
                chat_backend=preferred_backend,
                chat_model=preferred_model,
                chat_max_tokens=preferred_max_tokens,
            )
        except Exception as e:
            exc_holder.append(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=_JARVIS_TIMEOUT_SEC)

    if exc_holder:
        raise exc_holder[0]

    output = result.get(
        "output",
        "처리 시간이 길어지고 있습니다. 복잡한 분석은 백그라운드에서 계속 진행 중입니다. "
        "잠시 후 다시 질문하시거나, 더 짧은 요청으로 나눠서 시도해보세요.",
    )

    # ── Slack Q&A relay ──────────────────────────────────────────────────────────
    # 전략:
    #   1. @persona mention이 있으면 → 해당 팀 채널에 Q&A 전체 포스팅
    #   2. mention 없으면 → exec-president-decisions 채널에 포스팅 (fallback)
    #   3. HARNESS_OS_JARVIS_SLACK_DM_CHANNEL_ID 설정 시 추가 DM 릴레이
    if req.relay_to_slack:
        from agents.registry import find_mentioned_personas

        mentioned = [
            p for p in find_mentioned_personas(req.command) if p.handle != "jarvis"
        ]
        deduped_mentioned: list = []
        _seen_handles: set[str] = set()
        for _p in mentioned:
            if _p.handle not in _seen_handles:
                _seen_handles.add(_p.handle)
                deduped_mentioned.append(_p)

        if deduped_mentioned:
            # mention된 각 persona의 팀 채널에 Q&A 포스팅
            for persona in deduped_mentioned:
                if not persona.channel_env:
                    continue
                ch = os.getenv(persona.channel_env, "").strip()
                if not ch:
                    relay_notes.append(f"Slack relay 건너뜀: {persona.channel_env} 미설정")
                    continue
                err = _post_qa_to_slack(ch, req.command, output, persona_name=persona.name)
                if err:
                    relay_notes.append(f"#{persona.handle} 채널 relay 실패: {err}")
                else:
                    relay_notes.append(f"#{persona.handle} 채널 relay 완료")
        else:
            # mention 없음 → exec-president-decisions 채널로 fallback
            exec_ch = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "").strip()
            if exec_ch:
                err = _post_qa_to_slack(exec_ch, req.command, output, persona_name=None)
                if err:
                    relay_notes.append(f"exec 채널 relay 실패: {err}")
                else:
                    relay_notes.append("exec-president-decisions relay 완료")

        # 추가 DM relay (선택적, 별도 env로 제어)
        if slack_dm_channel_id:
            err = _post_qa_to_slack(slack_dm_channel_id, req.command, output, persona_name=None)
            if err:
                relay_notes.append(f"DM relay 실패: {err}")

    return {
        "session_id": session_id,
        "command": req.command,
        "output": output,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "relay_notes": relay_notes,
    }


@app.get("/api/costs/token-usage")
def get_token_usage(_: None = Depends(_require_secret)) -> list[dict[str, Any]]:
    # DB 조회
    try:
        rows = _execute_query(
            """
            SELECT 
                DATE(created_at) as day,
                model,
                SUM(input_tokens + output_tokens) as tokens
            FROM api_cost_log
            WHERE created_at >= '2026-05-01'
            GROUP BY DATE(created_at), model
            ORDER BY day ASC
            """
        )
    except Exception as e:
        print(f"Error querying api_cost_log: {e}")
        rows = []
    
    db_usage = {}
    for r in rows:
        d_str = str(r["day"])
        model = str(r["model"])
        tokens = int(r["tokens"] or 0)
        if tokens <= 0:
            continue
        if d_str not in db_usage:
            db_usage[d_str] = {}
        db_usage[d_str][model] = db_usage[d_str].get(model, 0) + tokens
        
    today_str = datetime.now().date().isoformat()
    all_days = set(db_usage.keys()) | {today_str}
    result = []
    
    for d in sorted(all_days):
        models_data = {}
        if d in db_usage:
            models_data.update(db_usage[d])
            
        total = sum(models_data.values())
        result.append({
            "day": d,
            "models": models_data,
            "total": total
        })
        
    return result


class ActionRequiredToggleRequest(BaseModel):
    id: str


@app.post("/api/action-required/toggle")
def toggle_ar_status(
    req: ActionRequiredToggleRequest, _: None = Depends(_require_secret)
) -> dict[str, Any]:
    path = PROJECT_ROOT / "docs/operations/ACTION_REQUIRED_REGISTRY.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Registry file not found")
        
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read registry: {e}")
        
    items = data.get("items", [])
    found = False
    new_status = "open"
    for item in items:
        if item.get("id") == req.id:
            current_status = str(item.get("status", "")).lower()
            new_status = "hold" if current_status == "open" else "open"
            item["status"] = new_status
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail=f"Action Required item {req.id} not found")
        
    try:
        data["generated_at"] = datetime.now().isoformat()
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update registry: {e}")

    return {"status": "ok", "id": req.id, "new_status": new_status}


# ── Pipeline Control API ─────────────────────────────────────────

@app.post("/api/pipeline/run")
def run_pipeline_job(body: PipelineRunRequest, _: None = Depends(_require_secret)) -> dict[str, Any]:
    if body.source not in _SOURCE_MAP:
        raise HTTPException(400, f"Unknown source: {body.source}. Valid: {list(_SOURCE_MAP)}")

    with _JOB_LOCK:
        running = [j for j in _PIPELINE_JOBS.values() if j["status"] == "running" and j["source"] == body.source]
    if running:
        raise HTTPException(409, f"'{body.source}' 작업이 이미 실행 중입니다 (job_id={running[0]['id']})")

    python = _PROJECT_ROOT / ".venv" / "bin" / "python"

    if body.source == "filter":
        script = _PROJECT_ROOT / "scripts" / "run_investment_signal_refiner.py"
        cmd = [str(python), str(script)]
        if body.dry_run:
            cmd += ["--dry-run"]
    else:
        script = _PROJECT_ROOT / "scripts" / "run_edu_deep_research.py"
        src_str = _SOURCE_MAP[body.source] or "scholar"
        cmd = [str(python), str(script), "--sources", src_str]
        if body.dry_run:
            cmd += ["--dry-run"]
        if body.topic:
            cmd += ["--extra-query", body.topic]
        cmd += ["--max-rss-items", str(body.max_rss_items)]
        cmd += ["--scholar-mode", body.scholar_mode]

    job_id = str(uuid4())[:8]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(_PROJECT_ROOT),
            env=os.environ.copy(),
            start_new_session=True,  # 자식 프로세스(yt-dlp 등)까지 같은 process group으로 묶어 killpg로 일괄 종료
        )
    except Exception as exc:
        raise HTTPException(500, f"프로세스 시작 실패: {exc}")

    with _JOB_LOCK:
        _PIPELINE_JOBS[job_id] = {
            "id": job_id,
            "source": body.source,
            "label": {"scholar": "Semantic Scholar", "arxiv": "arXiv", "youtube": "YouTube",
                      "rss": "RSS", "all": "전체 수집", "filter": "투자 신호 정제"}.get(body.source, body.source),
            "started_at": datetime.utcnow().isoformat() + "Z",
            "status": "running",
            "pid": proc.pid,
            "dry_run": body.dry_run,
            "finished_at": None,
            "exit_code": None,
        }
        _PIPELINE_LOGS[job_id] = [f"[시작] pid={proc.pid} cmd={' '.join(cmd[-3:])}"]
        # 오래된 job 제거
        if len(_PIPELINE_JOBS) > _MAX_JOB_HISTORY:
            oldest = sorted(
                (k for k, v in _PIPELINE_JOBS.items() if v["status"] != "running"),
                key=lambda k: _PIPELINE_JOBS[k].get("started_at", "")
            )
            for k in oldest[:len(_PIPELINE_JOBS) - _MAX_JOB_HISTORY]:
                _PIPELINE_JOBS.pop(k, None)
                _PIPELINE_LOGS.pop(k, None)

    threading.Thread(target=_tail_process, args=(job_id, proc), daemon=True).start()
    return {"job_id": job_id, "pid": proc.pid, "source": body.source}


@app.post("/api/pipeline/stop/{job_id}")
def stop_pipeline_job(job_id: str, _: None = Depends(_require_secret)) -> dict[str, Any]:
    with _JOB_LOCK:
        job = _PIPELINE_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "running":
        raise HTTPException(400, "Job is not running")
    pid = job["pid"]
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, _signal.SIGTERM)  # 스크립트 + yt-dlp 등 자식 프로세스 전체 종료
    except ProcessLookupError:
        pass  # 이미 종료됨
    except PermissionError:
        # fallback: process group 접근 불가 시 단일 pid만 종료
        try:
            os.kill(pid, _signal.SIGTERM)
        except ProcessLookupError:
            pass
    with _JOB_LOCK:
        _PIPELINE_JOBS[job_id]["status"] = "stopped"
        _PIPELINE_JOBS[job_id]["finished_at"] = datetime.utcnow().isoformat() + "Z"
        _PIPELINE_LOGS.setdefault(job_id, []).append("[중지] 사용자가 작업을 중단했습니다.")
    return {"ok": True}


@app.get("/api/pipeline/status")
def get_pipeline_status(_: None = Depends(_require_secret)) -> dict[str, Any]:
    with _JOB_LOCK:
        jobs = []
        for job in sorted(_PIPELINE_JOBS.values(), key=lambda j: j.get("started_at", ""), reverse=True)[:20]:
            job_id = job["id"]
            logs = _PIPELINE_LOGS.get(job_id, [])
            jobs.append({**job, "log_tail": logs[-80:], "log_total": len(logs)})
    return {"jobs": jobs}


@app.get("/api/pipeline/signals")
def get_pipeline_signals(
    source: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _: None = Depends(_require_secret),
) -> dict[str, Any]:
    where = ["domain = 'edu_consulting'"]
    params: list[Any] = []
    if source:
        where.append("source ILIKE %s")
        params.append(f"%{source}%")
    if status:
        where.append("status = %s")
        params.append(status)
    if q:
        where.append("(raw_data->>'title' ILIKE %s OR raw_data->>'abstract' ILIKE %s)")
        params.append(f"%{q}%")
        params.append(f"%{q}%")

    wc = " AND ".join(where)
    count_r = _execute_query(f"SELECT count(*) FROM raw_signals WHERE {wc}", tuple(params))
    total = int(count_r[0]["count"]) if count_r else 0

    rows = _execute_query(
        f"SELECT id, source, status, ingested_at, "
        f"raw_data->>'title' as title, "
        f"raw_data->>'url' as url, "
        f"raw_data->>'query' as query "
        f"FROM raw_signals WHERE {wc} "
        f"ORDER BY ingested_at DESC LIMIT %s OFFSET %s",
        tuple(params) + (limit, offset),
    )
    return {"total": total, "limit": limit, "offset": offset, "items": [dict(r) for r in rows]}


@app.get("/api/pipeline/source-stats")
def pipeline_source_stats(_: None = Depends(_require_secret)) -> dict[str, Any]:
    rows = _execute_query(
        "SELECT source, count(*) as cnt, max(ingested_at) as last_at "
        "FROM raw_signals WHERE domain = 'edu_consulting' "
        "GROUP BY source"
    )
    stats: dict[str, Any] = {}
    for r in (rows or []):
        stats[r["source"]] = {
            "count": int(r["cnt"]),
            "last_at": str(r["last_at"]) if r["last_at"] else None,
        }
    return {"stats": stats}


@app.get("/api/pipeline/queries")
def get_pipeline_queries(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return {"queries": _load_custom_queries()}


class QueryAddRequest(BaseModel):
    text: str
    targets: list[str] = ["scholar", "arxiv"]


@app.post("/api/pipeline/queries")
def add_pipeline_query(req: QueryAddRequest, _: None = Depends(_require_secret)) -> dict[str, Any]:
    if not req.text.strip():
        raise HTTPException(400, "Query text cannot be empty")
    queries = _load_custom_queries()
    queries.append({"text": req.text.strip(), "targets": req.targets, "added_at": datetime.utcnow().isoformat() + "Z"})
    _save_custom_queries(queries)
    return {"ok": True, "total": len(queries)}


@app.delete("/api/pipeline/queries/{idx}")
def delete_pipeline_query(idx: int, _: None = Depends(_require_secret)) -> dict[str, Any]:
    queries = _load_custom_queries()
    if idx < 0 or idx >= len(queries):
        raise HTTPException(404, "Query index out of range")
    queries.pop(idx)
    _save_custom_queries(queries)
    return {"ok": True, "total": len(queries)}


# ── Price Drop Monitor ───────────────────────────────────────────────────────

@app.on_event("startup")
def _start_price_drop_monitor() -> None:
    try:
        from scripts.price_drop_monitor import start_monitor
        start_monitor()
    except Exception:
        pass


class DropAlertAckRequest(BaseModel):
    alert_id: str = Field(min_length=1, max_length=200)


@app.get("/api/paper-trading/drop-alerts")
def get_drop_alerts(_: None = Depends(_require_secret)) -> dict[str, Any]:
    try:
        from scripts.price_drop_monitor import get_recent_alerts
        return {"ok": True, "alerts": get_recent_alerts(20)}
    except Exception as e:
        return {"ok": False, "alerts": [], "error": str(e)}


@app.post("/api/paper-trading/drop-alerts/ack")
def ack_drop_alert(req: DropAlertAckRequest, _: None = Depends(_require_secret)) -> dict[str, Any]:
    try:
        from scripts.price_drop_monitor import ack_alert
        found = ack_alert(req.alert_id)
        return {"ok": found}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 원격 배포 API ─────────────────────────────────────────────────────────────
# MBP에서 curl 한 줄로 Mac Mini 배포 완료.
# HARNESS_DEPLOY_TOKEN을 Mac Mini ~/.harness/passwords.json 옆 .env에 설정.

_DEPLOY_TOKEN = os.getenv("HARNESS_DEPLOY_TOKEN", "").strip()
_DEPLOY_LOG = _HARNESS_DATA_DIR / "deploy.log"
_deploy_status: dict[str, Any] = {"running": False, "last_result": None}


def _run_deploy() -> None:
    global _deploy_status
    _deploy_status["running"] = True
    _HARNESS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")
    log_lines: list[str] = [f"[{started_at}] 배포 시작"]

    def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=300)
        out = (r.stdout + r.stderr).strip()
        log_lines.append(f"$ {' '.join(cmd)}\n{out}")
        return r.returncode, out

    try:
        run(["git", "pull"], cwd=str(PROJECT_ROOT))
        run(["npm", "install", "--prefer-offline"], cwd=str(PROJECT_ROOT / "harness-os" / "frontend"))
        rc, out = run(["npm", "run", "build"], cwd=str(PROJECT_ROOT / "harness-os" / "frontend"))
        success = rc == 0
        log_lines.append(f"빌드 {'성공' if success else '실패'}")
        _deploy_status["last_result"] = {
            "ok": success,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "output": "\n".join(log_lines[-5:]),
        }
    except Exception as e:
        _deploy_status["last_result"] = {"ok": False, "error": str(e)}
    finally:
        _deploy_status["running"] = False
        try:
            _DEPLOY_LOG.write_text("\n---\n".join(log_lines))
        except Exception:
            pass
    # 배포 성공 시 백엔드 자체 재시동 (LaunchAgent가 자동 재시작)
    if _deploy_status["last_result"] and _deploy_status["last_result"].get("ok"):
        import signal
        os.kill(os.getpid(), signal.SIGTERM)


@app.post("/api/admin/deploy")
def admin_deploy(x_deploy_token: str = Header(default="")):
    if not _DEPLOY_TOKEN:
        raise HTTPException(status_code=503, detail="HARNESS_DEPLOY_TOKEN 미설정")
    if x_deploy_token != _DEPLOY_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid deploy token")
    if _deploy_status["running"]:
        return {"ok": False, "message": "이미 배포 중입니다", "status": _deploy_status}
    threading.Thread(target=_run_deploy, daemon=True).start()
    return {"ok": True, "message": "배포 시작됨. 30~60초 후 자동 재시동됩니다."}


@app.get("/api/admin/deploy/status")
def admin_deploy_status(x_deploy_token: str = Header(default="")):
    if not _DEPLOY_TOKEN or x_deploy_token != _DEPLOY_TOKEN:
        raise HTTPException(status_code=403)
    return _deploy_status


# ── OpenClaw 관제 API ─────────────────────────────────────────────────────────

_OPENCLAW_BIN = os.getenv("HARNESS_OPENCLAW_BIN", "/opt/homebrew/bin/openclaw")
_OPENCLAW_GATEWAY_PORT = int(os.getenv("HARNESS_OPENCLAW_GATEWAY_PORT", "18789"))
_OPENCLAW_LAUNCHAGENT_LABEL = os.getenv("HARNESS_OPENCLAW_LAUNCHAGENT", "ai.openclaw.gateway")


def _openclaw_gateway_reachable() -> tuple[bool, int | None]:
    """OpenClaw 게이트웨이 HTTP ping. (alive, latency_ms)"""
    url = f"http://127.0.0.1:{_OPENCLAW_GATEWAY_PORT}/"
    try:
        t0 = time.time()
        r = httpx.get(url, timeout=3.0, follow_redirects=False)
        ms = int((time.time() - t0) * 1000)
        return r.status_code < 500, ms
    except Exception:
        return False, None


def _openclaw_pid() -> int | None:
    try:
        out = subprocess.check_output(["pgrep", "-f", "openclaw.*gateway"], text=True).strip()
        pids = [int(x) for x in out.split() if x.strip().isdigit()]
        return pids[0] if pids else None
    except Exception:
        return None


def _openclaw_service_status() -> dict[str, Any]:
    pid = _openclaw_pid()
    reachable, latency_ms = _openclaw_gateway_reachable()
    binary_exists = Path(_OPENCLAW_BIN).exists()
    launchagent_path = Path.home() / "Library" / "LaunchAgents" / f"{_OPENCLAW_LAUNCHAGENT_LABEL}.plist"
    launchagent_installed = launchagent_path.exists()
    return {
        "running": pid is not None,
        "gateway_reachable": reachable,
        "pid": pid,
        "latency_ms": latency_ms,
        "gateway_url": f"http://127.0.0.1:{_OPENCLAW_GATEWAY_PORT}",
        "binary_exists": binary_exists,
        "binary_path": _OPENCLAW_BIN,
        "launchagent_installed": launchagent_installed,
        "launchagent_label": _OPENCLAW_LAUNCHAGENT_LABEL,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/api/system/openclaw/status")
def openclaw_status(_: None = Depends(_require_secret)) -> dict[str, Any]:
    status = _openclaw_service_status()
    status["ok"] = status["running"] and status["gateway_reachable"]
    return status


@app.post("/api/system/openclaw/restart")
def openclaw_restart(_: None = Depends(_require_secret)) -> dict[str, Any]:
    """LaunchAgent 기반 재시동. launchctl kickstart -k 사용."""
    try:
        uid = os.getuid()
        label = _OPENCLAW_LAUNCHAGENT_LABEL
        result = subprocess.run(
            ["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            time.sleep(2)
            status = _openclaw_service_status()
            return {
                "ok": True,
                "message": "재시동 명령 전달 완료",
                "stdout": result.stdout.strip(),
                "status": status,
            }
        # launchctl 실패 시 binary 직접 재시동 시도
        kill_result = subprocess.run(["pkill", "-f", "openclaw.*gateway"], capture_output=True)
        time.sleep(1)
        start_result = subprocess.run(
            [_OPENCLAW_BIN, "gateway", "--port", str(_OPENCLAW_GATEWAY_PORT)],
            start_new_session=True, capture_output=True, timeout=3,
        )
        time.sleep(2)
        status = _openclaw_service_status()
        return {
            "ok": status["running"],
            "message": "launchctl 실패 → 직접 재시동 시도",
            "stderr": result.stderr.strip(),
            "status": status,
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "status": _openclaw_service_status()}


# ── SPA Static File Serving (프로덕션 배포용) ────────────────────────────────
# Vite 빌드 결과물을 FastAPI에서 직접 서빙.
# /api/* 경로는 위의 라우트들이 우선 처리하므로 충돌 없음.

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse as _FileResponse

_FRONTEND_DIST = PROJECT_ROOT / "harness-os" / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    # /assets, /manifest.webmanifest 등 정적 파일 직접 서빙
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="static-assets")

    @app.get("/favicon.ico", include_in_schema=False)
    def _favicon():
        f = _FRONTEND_DIST / "favicon.ico"
        return _FileResponse(str(f)) if f.exists() else _FileResponse(str(_FRONTEND_DIST / "index.html"))

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def _manifest():
        f = _FRONTEND_DIST / "manifest.webmanifest"
        return _FileResponse(str(f)) if f.exists() else _FileResponse(str(_FRONTEND_DIST / "index.html"))

    # SPA catch-all: /api/* 제외한 모든 경로 → index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_fallback(full_path: str):
        candidate = _FRONTEND_DIST / full_path
        if candidate.exists() and candidate.is_file():
            return _FileResponse(str(candidate))
        return _FileResponse(str(_FRONTEND_DIST / "index.html"))
