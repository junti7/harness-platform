from __future__ import annotations

import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

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


def _require_secret(x_harness_secret: str | None = Header(default=None)) -> None:
    expected = os.getenv("HARNESS_OS_SECRET_KEY", "").strip()
    if not expected:
        return
    if x_harness_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid dashboard secret")


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
    rows = _execute_query(
        """
        SELECT COALESCE(SUM(cost_usd), 0) AS total
        FROM research_reports
        WHERE DATE(created_at) = CURRENT_DATE
        """
    )
    return float(rows[0]["total"]) if rows else 0.0


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


def _read_ar_registry() -> dict[str, Any]:
    path = PROJECT_ROOT / "docs/operations/ACTION_REQUIRED_REGISTRY.json"
    if not path.exists():
        return {"open": 0, "closed": 0, "items": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    open_count = sum(1 for item in items if str(item.get("status", "")).lower() == "open")
    return {"open": open_count, "closed": max(0, len(items) - open_count), "items": items}


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
    from scripts.ibkr_cp_client import IbkrCpClient, safe_check_connectivity
    from scripts.ibkr_onboarding import compute_status

    whitelist_path = PROJECT_ROOT / "docs/trading/etf_whitelist_v0.json"
    trading_watchlist_path = PROJECT_ROOT / "docs/trading/trading_watchlist_v0.json"
    registry_path = PROJECT_ROOT / "docs/reports/instrument_registry.jsonl"
    pending_path = PROJECT_ROOT / "docs/reports/instrument_registry_pending.jsonl"

    whitelist_items = 0
    whitelist_generated_at = None
    whitelist_payload = _load_json_file(whitelist_path)
    if whitelist_payload:
        whitelist_items = len(whitelist_payload.get("items") or [])
        whitelist_generated_at = whitelist_payload.get("generated_at")

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
    rows = _execute_query(
        """
        SELECT DATE(created_at) AS day, ROUND(COALESCE(SUM(cost_usd), 0)::numeric, 4) AS cost_usd
        FROM research_reports
        WHERE created_at >= NOW() - (%s || ' days')::interval
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at) ASC
        """,
        (days,),
    )
    return rows


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
    from scripts.openclaw_codex_bridge import status_snapshot

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
            "open": ar_registry["open"],
            "closed": ar_registry["closed"],
            "total": ar_registry["open"] + ar_registry["closed"],
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
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "harness-os-backend", "status": "ok"}


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "generated_at": datetime.now().isoformat(timespec="seconds")}


@app.get("/api/dashboard")
def get_dashboard(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return _cached("dashboard", _dashboard_payload)


@app.get("/api/dashboard/advanced")
def get_advanced_dashboard(_: None = Depends(_require_secret)) -> dict[str, Any]:
    return _cached("dashboard_advanced", _advanced_dashboard_payload)


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


_JARVIS_TIMEOUT_SEC = int(os.getenv("HARNESS_OS_JARVIS_TIMEOUT_SEC", "55"))


@app.post("/api/jarvis/invoke")
def invoke_jarvis(
    req: JarvisInvokeRequest, _: None = Depends(_require_secret)
) -> dict[str, Any]:
    from adapters.content.openclaw_agent import run as openclaw_run

    session_id = req.session_id or f"harness-os-{uuid4().hex[:10]}"
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

    result: dict[str, Any] = {}
    exc_holder: list[Exception] = []

    def _run() -> None:
        try:
            result["output"] = openclaw_run(
                req.command,
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
        "⏳ 처리 시간이 길어지고 있습니다. 복잡한 분석은 백그라운드에서 계속 진행 중입니다. "
        "잠시 후 다시 질문하시거나, 더 짧은 요청으로 나눠서 시도해보세요.",
    )
    return {
        "session_id": session_id,
        "command": req.command,
        "output": output,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
