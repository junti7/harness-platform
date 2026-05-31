from __future__ import annotations

import json
from collections import defaultdict
from typing import Any


ACTIVE_SOURCE_TYPES = {"rss", "rss_search"}
ACTIVE_COLLECTION_MODES = {"rss_pull", "rss_search", "community_api"}


def parse_rate_limit_policy(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def merge_catalog_rows_with_defaults(db_rows: list[dict[str, Any]], default_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for src in default_rows:
        name = str(src.get("name") or src.get("source_name") or "").strip()
        if not name:
            continue
        merged[name] = {
            "source_name": name,
            "base_url": src.get("url") or src.get("base_url") or "",
            "source_type": src.get("source_type") or "rss",
            "enabled": bool(src.get("enabled", True)),
            "expected_signal_type": src.get("expected_signal_type") or "",
            "reliability_score": float(src.get("reliability_score") or 0),
            "rate_limit_policy": src.get("rate_limit_policy") or {
                "stale_minutes": int(src.get("stale_minutes", 0) or 0),
                "channel": src.get("channel") or "",
                "collection_mode": src.get("collection_mode") or "",
                "activation_policy": src.get("activation_policy") or "",
                "requires_login": bool(src.get("requires_login", False)),
                "preferred_worker": src.get("preferred_worker") or "",
                "notes": src.get("notes") or "",
            },
        }

    for row in db_rows:
        name = str(row.get("source_name") or "").strip()
        if not name:
            continue
        existing = merged.get(name, {})
        merged[name] = {
            **existing,
            **row,
            "rate_limit_policy": parse_rate_limit_policy(
                row.get("rate_limit_policy") or existing.get("rate_limit_policy")
            ),
        }

    return sorted(
        merged.values(),
        key=lambda item: (
            not bool(item.get("enabled", True)),
            str(item.get("rate_limit_policy", {}).get("channel") or item.get("source_type") or ""),
            str(item.get("source_name") or ""),
        ),
    )


def source_channel(source_row: dict[str, Any]) -> str:
    policy = parse_rate_limit_policy(source_row.get("rate_limit_policy"))
    return str(policy.get("channel") or source_row.get("source_type") or "rss").strip().lower()


def source_collection_mode(source_row: dict[str, Any]) -> str:
    policy = parse_rate_limit_policy(source_row.get("rate_limit_policy"))
    mode = str(policy.get("collection_mode") or "").strip().lower()
    if mode:
        return mode
    source_type = str(source_row.get("source_type") or "rss").strip().lower()
    if source_type in ACTIVE_SOURCE_TYPES:
        return "rss_pull"
    return source_type


def source_preferred_worker(source_row: dict[str, Any]) -> str:
    policy = parse_rate_limit_policy(source_row.get("rate_limit_policy"))
    return str(policy.get("preferred_worker") or "mini").strip().lower()


def source_notes(source_row: dict[str, Any]) -> str:
    policy = parse_rate_limit_policy(source_row.get("rate_limit_policy"))
    return str(policy.get("notes") or "").strip()


def source_requires_login(source_row: dict[str, Any]) -> bool:
    policy = parse_rate_limit_policy(source_row.get("rate_limit_policy"))
    return bool(policy.get("requires_login", False))


def source_status(source_row: dict[str, Any]) -> str:
    policy = parse_rate_limit_policy(source_row.get("rate_limit_policy"))
    activation_policy = str(policy.get("activation_policy") or "").strip().lower()
    enabled = bool(source_row.get("enabled", True))
    requires_login = bool(policy.get("requires_login", False))
    source_type = str(source_row.get("source_type") or "").strip().lower()
    mode = source_collection_mode(source_row)

    if enabled and (source_type in ACTIVE_SOURCE_TYPES or mode in ACTIVE_COLLECTION_MODES) and mode in ACTIVE_COLLECTION_MODES:
        return "active"
    if requires_login or activation_policy in {"restricted", "approval_required", "login_required"}:
        return "restricted"
    if activation_policy in {"discovery", "manual_review"} or mode in {"browser_search", "manual", "community_api"}:
        return "standby"
    if enabled:
        return "active"
    return "standby"


def build_channel_coverage(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "channel": "",
            "label": "",
            "total_sources": 0,
            "active_sources": 0,
            "standby_sources": 0,
            "restricted_sources": 0,
            "preferred_worker": "",
            "notes": [],
        }
    )

    for row in source_rows:
        channel = source_channel(row) or "other"
        entry = grouped[channel]
        entry["channel"] = channel
        entry["label"] = channel.upper() if len(channel) <= 4 else channel.title()
        entry["total_sources"] += 1
        status = source_status(row)
        if status == "active":
            entry["active_sources"] += 1
        elif status == "restricted":
            entry["restricted_sources"] += 1
        else:
            entry["standby_sources"] += 1

        preferred_worker = source_preferred_worker(row)
        if preferred_worker and not entry["preferred_worker"]:
            entry["preferred_worker"] = preferred_worker

        note = source_notes(row)
        if note and note not in entry["notes"] and len(entry["notes"]) < 2:
            entry["notes"].append(note)

    return sorted(
        grouped.values(),
        key=lambda item: (
            -int(item["active_sources"]),
            -int(item["total_sources"]),
            str(item["channel"]),
        ),
    )
