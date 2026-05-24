"""
Maily subscriber metrics adapter.

Current implementation is intentionally provider-safe:
- preferred source: JSON metrics file path (`MAILY_METRICS_PATH`)
- fallback source: environment variables (`MAILY_*`)

This keeps the platform integrated into Harness without guessing an
undocumented live API contract. When a stable Maily API is confirmed,
the fetch path can be extended behind the same function contract.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.logger import HarnessLogger

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

_INT_FIELDS = (
    "free_subscribers",
    "paid_subscribers",
    "paid_revenue_krw",
    "opens",
    "clicks",
    "replies",
    "shares",
    "unsubscribe_count",
    "post_count",
    "draft_count",
)

_CSV_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "free_subscribers": (
        "free_subscribers",
        "free subscribers",
        "무료 구독자",
        "무료구독자",
        "subscribers",
        "total subscribers",
        "총 구독자",
    ),
    "paid_subscribers": ("paid_subscribers", "paid subscribers", "유료 구독자", "유료구독자"),
    "paid_revenue_krw": ("paid_revenue_krw", "paid revenue", "revenue", "매출", "유료 매출"),
    "opens": ("opens", "open", "open count", "오픈", "열람"),
    "clicks": ("clicks", "click", "click count", "클릭"),
    "replies": ("replies", "reply", "답장"),
    "shares": ("shares", "share", "공유"),
    "unsubscribe_count": ("unsubscribe_count", "unsubscribes", "unsubscribe", "구독취소", "해지"),
    "post_count": ("post_count", "posts", "발행 수", "발행수"),
    "draft_count": ("draft_count", "drafts", "초안 수", "초안수"),
}


def _to_int(value: Any, default: int | None = 0) -> int | None:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return int(value)
    return int(str(value).replace(",", "").strip())


def _base_metrics() -> dict[str, Any]:
    return {
        "free_subscribers": 0,
        "paid_subscribers": 0,
        "paid_revenue_krw": 0,
        "opens": 0,
        "clicks": 0,
        "replies": 0,
        "shares": 0,
        "unsubscribe_count": 0,
        "post_count": None,
        "draft_count": None,
        "notes": "",
        "source": "env",
    }


def _normalize_key(value: str) -> str:
    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def _read_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(fh, dialect=dialect)
        return [dict(row) for row in reader]


def _match_column(columns: list[str], canonical_key: str) -> str | None:
    normalized_columns = {_normalize_key(column): column for column in columns}
    for alias in _CSV_FIELD_ALIASES.get(canonical_key, (canonical_key,)):
        matched = normalized_columns.get(_normalize_key(alias))
        if matched:
            return matched
    return None


def _latest_csv_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    date_candidates = ("snapshot_date", "date", "날짜", "created_at", "updated_at")
    date_column = None
    columns = list(rows[0].keys())
    for candidate in date_candidates:
        date_column = _match_column(columns, candidate)
        if date_column:
            break
    if not date_column:
        return rows[-1]
    return max(rows, key=lambda row: str(row.get(date_column) or ""))


def _load_metrics_file(path_value: str, logger: HarnessLogger | None = None) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (Path(__file__).resolve().parents[2] / path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if logger:
        logger.info(f"Maily metrics file loaded: {path}")
    metrics = _base_metrics()
    metrics["source"] = "file"
    metrics["notes"] = str(payload.get("notes", "") or "")
    for field in _INT_FIELDS:
        if field in payload:
            metrics[field] = _to_int(payload.get(field), metrics.get(field))
    return metrics


def _load_metrics_csv(path_value: str, logger: HarnessLogger | None = None) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (Path(__file__).resolve().parents[2] / path).resolve()
    rows = _read_rows(path)
    row = _latest_csv_row(rows)
    metrics = _base_metrics()
    metrics["source"] = "csv"
    metrics["notes"] = f"csv:{path.name}"
    if logger:
        logger.info(f"Maily metrics CSV loaded: {path} rows={len(rows)}")
    if not row:
        return metrics
    columns = list(row.keys())
    for field in _INT_FIELDS:
        column = _match_column(columns, field)
        if column:
            metrics[field] = _to_int(row.get(column), metrics.get(field))
    return metrics


def _load_metrics_env() -> dict[str, Any]:
    metrics = _base_metrics()
    env_map = {
        "free_subscribers": "MAILY_FREE_SUBSCRIBERS",
        "paid_subscribers": "MAILY_PAID_SUBSCRIBERS",
        "paid_revenue_krw": "MAILY_PAID_REVENUE_KRW",
        "opens": "MAILY_OPENS",
        "clicks": "MAILY_CLICKS",
        "replies": "MAILY_REPLIES",
        "shares": "MAILY_SHARES",
        "unsubscribe_count": "MAILY_UNSUBSCRIBE_COUNT",
        "post_count": "MAILY_POST_COUNT",
        "draft_count": "MAILY_DRAFT_COUNT",
    }
    for key, env_key in env_map.items():
        raw = os.getenv(env_key)
        if raw is not None and raw != "":
            metrics[key] = _to_int(raw, metrics.get(key))
    metrics["notes"] = os.getenv("MAILY_METRICS_NOTES", "").strip()
    return metrics


def fetch_subscriber_metrics(logger: HarnessLogger | None = None) -> dict[str, Any]:
    csv_path_value = os.getenv("MAILY_METRICS_CSV_PATH", "").strip()
    if csv_path_value:
        try:
            return _load_metrics_csv(csv_path_value, logger=logger)
        except Exception as exc:
            if logger:
                logger.warning(f"Maily metrics CSV load failed: {exc}; falling back")

    path_value = os.getenv("MAILY_METRICS_PATH", "").strip()
    if path_value:
        try:
            return _load_metrics_file(path_value, logger=logger)
        except Exception as exc:
            if logger:
                logger.warning(f"Maily metrics file load failed: {exc}; falling back to env values")

    metrics = _load_metrics_env()
    if logger:
        logger.info(
            "Maily metrics resolved"
            f" free={metrics['free_subscribers']} paid={metrics['paid_subscribers']}"
            f" source={metrics['source']}"
        )
    return metrics
