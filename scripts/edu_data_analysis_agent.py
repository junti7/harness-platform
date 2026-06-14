#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import Json, execute_values

from core.database import get_connection
from scripts.refresh_edu_evidence_bank import infer_segment, infer_source_kind, is_low_quality_evidence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

DEFAULT_RESEARCH_DIRS = [
    PROJECT_ROOT / "data" / "edu_research" / "2026-05-25",
    PROJECT_ROOT / "data" / "edu_research" / "2026-06-04",
]
DEFAULT_ANCHORS_PATH = PROJECT_ROOT / "data" / "edu_research" / "evidence_anchors.json"
DEFAULT_TRANSCRIPTS_DIR = PROJECT_ROOT / "data" / "edu_youtube_transcripts"

VALID_PROVENANCE = {"collected", "curated", "generated"}
VALID_RIGHTS_CLASS = {"public", "fair_excerpt", "internal_only", "unknown"}
VALID_REUSE_SCOPE = {"customer_facing", "internal"}
VALID_SOURCE_KIND = {"community_voice", "research_policy", "media_case", "general_reference"}
TEXT_COMPATIBLE_TYPES = {"text", "character varying", "character", "varchar", "char"}


@dataclass
class KnowledgeItem:
    natural_key: str
    source: str
    source_id: str
    source_url: str
    source_kind: str
    provenance: str
    rights_class: str
    reuse_scope: str
    excerpt_max_chars: int
    verbatim_allowed: bool
    segment: str | None
    item_type: str | None
    title: str | None
    body: str
    cite: str | None
    lang: str
    quality_score: float
    keywords: list[str]
    emb_model: str
    emb_dim: int
    collected_at: str
    source_ref: str | None = None


@dataclass
class DlqRecord:
    tier: int
    item_type: str
    error_message: str
    raw_data: dict[str, Any]
    reason_code: str
    source_name: str
    correlation_id: str


@dataclass
class RunStats:
    correlation_id: str
    run_id: int | None = None
    input_count: int = 0
    success_count: int = 0
    skipped_count: int = 0
    dlq_count: int = 0
    adapter_failures: int = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_embedding_signature() -> dict[str, Any]:
    from core.embeddings import embedding_backend_signature

    signature = embedding_backend_signature(resolve_runtime=True)
    if not signature.get("model") or not signature.get("dim"):
        raise RuntimeError("embedding_signature_unavailable")
    return signature


def _normalize_ws(text: Any) -> str:
    if text is None:
        raw = ""
    elif isinstance(text, (list, tuple, set)):
        raw = " ".join(_normalize_ws(part) for part in text)
    else:
        raw = str(text)
    return re.sub(r"\s+", " ", raw).strip()


def _detect_lang(text: str) -> str:
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_datetime(value: Any, fallback: str) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat(timespec="seconds")
    raw = _normalize_ws(str(value))
    if not raw:
        return fallback
    for parser in (
        lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")),
        parsedate_to_datetime,
        lambda x: datetime.strptime(x, "%Y%m%d"),
        lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
        lambda x: datetime.strptime(x, "%Y"),
    ):
        try:
            dt = parser(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
        except Exception:
            continue
    return fallback


def _first_sentence(text: str, limit: int = 220) -> str:
    clean = _normalize_ws(text)
    if len(clean) <= limit:
        return clean
    cut = clean[:limit]
    for punct in (". ", "다. ", "요. ", "! ", "? "):
        idx = cut.find(punct)
        if idx > 40:
            return cut[: idx + 1].strip()
    return cut.strip()


def _keyword_tokens(*parts: str | None, cap: int = 12) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for part in parts:
        for token in re.findall(r"[A-Za-z0-9가-힣]{2,24}", _normalize_ws(part)):
            normalized = token.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            tokens.append(normalized)
            if len(tokens) >= cap:
                return tokens
    return tokens


def _fallback_source_url(source: str, source_id: str) -> str:
    return f"urn:harness:{source.lower()}:{source_id}"


def _clip_excerpt(text: str | None, cap: int) -> str | None:
    if text is None:
        return None
    clean = _normalize_ws(text)
    if cap <= 0 or len(clean) <= cap:
        return clean
    return clean[:cap].rstrip()


def _enforce_rights_window(body: str, cite: str | None, reuse_scope: str, excerpt_max_chars: int) -> tuple[str, str | None]:
    if reuse_scope != "customer_facing" or excerpt_max_chars <= 0:
        return body, cite
    return _clip_excerpt(body, excerpt_max_chars) or "", _clip_excerpt(cite, excerpt_max_chars)


def _normalize_sql_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _dlq_index_contract_ok(indexdef: str) -> bool:
    normalized = _normalize_sql_text(indexdef)
    required_snippets = [
        "create unique index",
        "on public.dead_letter_queue",
        "(pipeline_name, tier, external_key, reason_code, item_type)",
        "where (resolved = false)",
    ]
    return all(snippet in normalized for snippet in required_snippets)


def _customer_facing_view_contract_ok(viewdef: str) -> bool:
    normalized = _normalize_sql_text(viewdef)
    required_snippets = [
        "from public.edu_knowledge_items",
        "reuse_scope = 'customer_facing'",
        "provenance = any (array['collected'::text, 'curated'::text])",
        "rights_class = any (array['public'::text, 'fair_excerpt'::text])",
        "excerpt_max_chars > 0",
    ]
    return all(snippet in normalized for snippet in required_snippets)


def _rights_policy(adapter_name: str, provenance: str) -> tuple[str, str, int, bool]:
    if provenance == "curated":
        return "fair_excerpt", "customer_facing", 220, False
    if adapter_name in {"eric", "openalex", "semantic_scholar", "rss", "hackernews"}:
        return "fair_excerpt", "customer_facing", 220, False
    if adapter_name in {"reddit", "naver", "gplay", "youtube_transcript"}:
        return "internal_only", "internal", 0, False
    return "unknown", "internal", 0, False


def _quality_score(body: str, cite: str | None, source_kind: str, source_label: str, raw_data: dict[str, Any]) -> float:
    score = 55.0
    if len(body) >= 120:
        score += 15
    elif len(body) >= 60:
        score += 8
    if cite and len(cite) >= 60:
        score += 10
    if source_kind == "research_policy":
        score += 10
    if source_kind == "community_voice":
        score += 4
    if is_low_quality_evidence(cite or body, source_label, raw_data, raw_data.get("source")):
        score -= 35
    return max(0.0, min(100.0, round(score, 2)))


def _natural_key(source: str, source_id: str | None, body: str) -> str:
    if source_id:
        return _sha256(f"{source}|{source_id}")
    normalized = re.sub(r"[^a-z0-9가-힣]+", " ", body.lower())
    return _sha256(f"{source}|{normalized}")


def _record_body(title: str | None, *parts: str | None) -> str:
    body_parts = [_normalize_ws(title)] if title else []
    body_parts.extend(_normalize_ws(part) for part in parts if _normalize_ws(part))
    return _normalize_ws(" ".join(body_parts))


def _research_dirs() -> list[Path]:
    return [path for path in DEFAULT_RESEARCH_DIRS if path.exists()]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_file_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")


def _adapter_name(path: Path) -> str | None:
    mapping = {
        "rss_collected.json": "rss",
        "eric_collected.json": "eric",
        "hackernews_collected.json": "hackernews",
        "openalex_collected.json": "openalex",
        "openalex_edu_focused.json": "openalex",
        "semantic_scholar_collected.json": "semantic_scholar",
        "reddit_collected.json": "reddit",
        "gplay_reviews.json": "gplay",
        "naver_collected.json": "naver",
    }
    if path.name in mapping:
        return mapping[path.name]
    if path.suffix == ".json" and not path.name.endswith(".json3") and re.fullmatch(r"\d{8}_[A-Za-z0-9_-]+\.json", path.name):
        return "youtube_transcript"
    return None


def _build_anchor_items(path: Path, signature: dict[str, Any], correlation_id: str) -> tuple[list[KnowledgeItem], list[DlqRecord]]:
    items: list[KnowledgeItem] = []
    dlq: list[DlqRecord] = []
    fallback_ts = _safe_file_timestamp(path)
    try:
        payload = _load_json(path)
        rows = payload.get("items", [])
    except Exception as exc:
        return [], [DlqRecord(1, "anchor", str(exc), {"path": str(path)}, "parse_error", path.name, correlation_id)]
    for row in rows:
        try:
            cite = _normalize_ws(row.get("cite"))
            source_id = str(row.get("id") or "")
            source = "EvidenceAnchor"
            source_url = _fallback_source_url(source, source_id or _sha256(cite))
            body, cite = _enforce_rights_window(cite, cite, "customer_facing", min(max(len(cite), 1), 220))
            item = KnowledgeItem(
                source_ref=source_id or None,
                natural_key=_natural_key(source, source_id, body),
                source=source,
                source_id=source_id or _sha256(cite)[:16],
                source_url=source_url,
                source_kind="general_reference",
                provenance="curated",
                rights_class="fair_excerpt",
                reuse_scope="customer_facing",
                excerpt_max_chars=min(max(len(cite), 1), 220),
                verbatim_allowed=False,
                segment=row.get("segment"),
                item_type=row.get("type"),
                title=row.get("type"),
                body=body,
                cite=_first_sentence(cite),
                lang=_detect_lang(body),
                quality_score=85.0,
                keywords=_keyword_tokens(row.get("type"), row.get("source"), cite),
                emb_model=str(signature["model"]),
                emb_dim=int(signature["dim"]),
                collected_at=fallback_ts,
            )
            items.append(item)
        except Exception as exc:
            dlq.append(
                DlqRecord(
                    tier=1,
                    item_type="anchor",
                    error_message=str(exc),
                    raw_data=row if isinstance(row, dict) else {"row": row},
                    reason_code="normalize_error",
                    source_name=path.name,
                    correlation_id=correlation_id,
                )
            )
    return items, dlq


def _normalize_row(adapter_name: str, row: dict[str, Any], path: Path, signature: dict[str, Any]) -> KnowledgeItem:
    source_label = _normalize_ws(row.get("source") or adapter_name)
    title = _normalize_ws(row.get("title") or row.get("app") or row.get("type"))
    source_id = _normalize_ws(
        str(
            row.get("video_id")
            or row.get("url")
            or row.get("link")
            or row.get("doi")
            or row.get("id")
            or f"{title[:48]}-{_sha256(json.dumps(row, ensure_ascii=False, sort_keys=True))[:12]}"
        )
    )

    if adapter_name == "rss":
        body = _record_body(title, row.get("summary"), row.get("tags"))
        cite = _first_sentence(row.get("summary") or title)
        source_url = _normalize_ws(row.get("link"))
        collected_at = _parse_datetime(row.get("published"), _safe_file_timestamp(path))
        item_type = "rss_article"
    elif adapter_name == "eric":
        body = _record_body(title, row.get("description"), row.get("author"), row.get("query"))
        cite = _first_sentence(row.get("description") or title)
        source_url = _normalize_ws(row.get("url"))
        collected_at = _parse_datetime(row.get("year"), _safe_file_timestamp(path))
        item_type = "research_abstract"
    elif adapter_name == "hackernews":
        body = _record_body(title, f"points={row.get('points')}", f"comments={row.get('comments')}", row.get("query"))
        cite = _first_sentence(title)
        source_url = _normalize_ws(row.get("url"))
        collected_at = _parse_datetime(row.get("created_at"), _safe_file_timestamp(path))
        item_type = "community_link"
    elif adapter_name == "openalex":
        body = _record_body(title, f"cited_by={row.get('cited_by')}", row.get("query"))
        cite = _first_sentence(title)
        source_url = _normalize_ws(row.get("doi"))
        collected_at = _parse_datetime(row.get("year"), _safe_file_timestamp(path))
        item_type = "research_paper"
    elif adapter_name == "semantic_scholar":
        body = _record_body(title, ", ".join(row.get("authors") or []), f"citations={row.get('citations')}", row.get("query"))
        cite = _first_sentence(title)
        source_url = _normalize_ws(row.get("pdf_url") or row.get("doi"))
        collected_at = _parse_datetime(row.get("year"), _safe_file_timestamp(path))
        item_type = "research_paper"
    elif adapter_name == "reddit":
        body = _record_body(title, row.get("selftext"), f"subreddit={row.get('subreddit')}", row.get("query"))
        cite = _first_sentence(row.get("selftext") or title)
        source_url = _normalize_ws(row.get("url"))
        collected_at = _parse_datetime(row.get("created_utc"), _safe_file_timestamp(path))
        item_type = "community_post"
    elif adapter_name == "gplay":
        body = _record_body(title or row.get("app"), row.get("content"), f"rating={row.get('rating')}")
        cite = _first_sentence(row.get("content") or title or row.get("app"))
        source_url = _normalize_ws(row.get("url"))
        collected_at = _parse_datetime(row.get("at"), _safe_file_timestamp(path))
        item_type = "app_review"
    elif adapter_name == "naver":
        body = _record_body(title, row.get("description"), row.get("query"), row.get("cafe_or_blog"))
        cite = _first_sentence(row.get("description") or title)
        source_url = _normalize_ws(row.get("link"))
        collected_at = _parse_datetime(row.get("postdate"), _safe_file_timestamp(path))
        item_type = "community_post"
    elif adapter_name == "youtube_transcript":
        body = _record_body(title, row.get("transcript"), row.get("channel"))
        cite = _first_sentence(row.get("transcript") or title)
        source_url = _normalize_ws(row.get("url"))
        collected_at = _parse_datetime(row.get("collected_at") or row.get("upload_date"), _safe_file_timestamp(path))
        item_type = "video_transcript"
    else:
        raise ValueError(f"unsupported_adapter:{adapter_name}")

    body = _normalize_ws(body)
    source_kind = infer_source_kind(source_label, row, row.get("source"))
    segment = row.get("segment") or infer_segment(row, row.get("source"))
    provenance = "collected"
    rights_class, reuse_scope, excerpt_max_chars, verbatim_allowed = _rights_policy(adapter_name, provenance)
    source_url = source_url or _fallback_source_url(source_label, source_id)
    if source_kind not in VALID_SOURCE_KIND:
        source_kind = "general_reference"
    body, cite = _enforce_rights_window(body, cite, reuse_scope, excerpt_max_chars)

    return KnowledgeItem(
        source_ref=None,
        natural_key=_natural_key(source_label, source_id, body),
        source=source_label,
        source_id=source_id,
        source_url=source_url,
        source_kind=source_kind,
        provenance=provenance,
        rights_class=rights_class,
        reuse_scope=reuse_scope,
        excerpt_max_chars=excerpt_max_chars,
        verbatim_allowed=verbatim_allowed,
        segment=segment,
        item_type=item_type,
        title=title or None,
        body=body,
        cite=cite or None,
        lang=_detect_lang(body),
        quality_score=_quality_score(body, cite, source_kind, source_label, row),
        keywords=_keyword_tokens(title, body, row.get("query")),
        emb_model=str(signature["model"]),
        emb_dim=int(signature["dim"]),
        collected_at=collected_at,
    )


def _collect_file_items(path: Path, signature: dict[str, Any], correlation_id: str) -> tuple[list[KnowledgeItem], list[DlqRecord], int]:
    adapter_name = _adapter_name(path)
    if adapter_name is None:
        return [], [], 0

    try:
        payload = _load_json(path)
        rows = payload if isinstance(payload, list) else [payload]
    except Exception as exc:
        return [], [DlqRecord(1, adapter_name, str(exc), {"path": str(path)}, "parse_error", path.name, correlation_id)], 1

    items: list[KnowledgeItem] = []
    dlq: list[DlqRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            dlq.append(
                DlqRecord(1, adapter_name, "row_not_object", {"row": row, "path": str(path)}, "row_not_object", path.name, correlation_id)
            )
            continue
        try:
            items.append(_normalize_row(adapter_name, row, path, signature))
        except Exception as exc:
            dlq.append(
                DlqRecord(1, adapter_name, str(exc), row, "normalize_error", path.name, correlation_id)
            )
    return items, dlq, len(rows)


def build_knowledge_dataframe(
    research_dirs: list[Path] | None = None,
    transcripts_dir: Path | None = None,
    anchors_path: Path | None = None,
    correlation_id: str | None = None,
) -> tuple[pd.DataFrame, list[DlqRecord], RunStats]:
    signature = get_embedding_signature()
    run = RunStats(correlation_id=correlation_id or uuid.uuid4().hex[:12])
    items: list[KnowledgeItem] = []
    dlq: list[DlqRecord] = []

    anchor_path = anchors_path or DEFAULT_ANCHORS_PATH
    if anchor_path.exists():
        anchor_items, anchor_dlq = _build_anchor_items(anchor_path, signature, run.correlation_id)
        items.extend(anchor_items)
        dlq.extend(anchor_dlq)
        run.input_count += len(anchor_items) + len(anchor_dlq)

    for directory in research_dirs or _research_dirs():
        for path in sorted(directory.glob("*.json")):
            file_items, file_dlq, row_count = _collect_file_items(path, signature, run.correlation_id)
            items.extend(file_items)
            dlq.extend(file_dlq)
            run.input_count += row_count
            if file_dlq and not file_items and any(entry.reason_code == "parse_error" for entry in file_dlq):
                run.adapter_failures += 1

    transcript_root = transcripts_dir or DEFAULT_TRANSCRIPTS_DIR
    if transcript_root.exists():
        for path in sorted(transcript_root.glob("*.json")):
            file_items, file_dlq, row_count = _collect_file_items(path, signature, run.correlation_id)
            items.extend(file_items)
            dlq.extend(file_dlq)
            run.input_count += row_count
            if file_dlq and not file_items and any(entry.reason_code == "parse_error" for entry in file_dlq):
                run.adapter_failures += 1

    frame = pd.DataFrame(asdict(item) for item in items)
    if frame.empty:
        run.dlq_count = len(dlq)
        return frame, dlq, run

    before = len(frame)
    frame = frame.drop_duplicates(subset=["natural_key"], keep="first").reset_index(drop=True)
    run.skipped_count = before - len(frame)
    valid_frame, validation_dlq = validate_knowledge_dataframe(frame, signature, run.correlation_id)
    dlq.extend(validation_dlq)
    run.success_count = len(valid_frame)
    run.dlq_count = len(dlq)
    return valid_frame, dlq, run


def validate_knowledge_dataframe(
    frame: pd.DataFrame,
    signature: dict[str, Any],
    correlation_id: str,
) -> tuple[pd.DataFrame, list[DlqRecord]]:
    valid_rows: list[dict[str, Any]] = []
    dlq: list[DlqRecord] = []
    for row in frame.to_dict(orient="records"):
        reasons: list[str] = []
        if not _normalize_ws(row.get("source")):
            reasons.append("missing_source")
        if not _normalize_ws(row.get("source_url")):
            reasons.append("missing_source_url")
        if not _normalize_ws(row.get("collected_at")):
            reasons.append("missing_collected_at")
        if row.get("provenance") not in VALID_PROVENANCE:
            reasons.append("invalid_provenance")
        if row.get("rights_class") not in VALID_RIGHTS_CLASS:
            reasons.append("invalid_rights_class")
        if row.get("reuse_scope") not in VALID_REUSE_SCOPE:
            reasons.append("invalid_reuse_scope")
        if row.get("source_kind") not in VALID_SOURCE_KIND:
            reasons.append("invalid_source_kind")
        if len(_normalize_ws(row.get("body"))) < 20:
            reasons.append("body_too_short")
        if row.get("reuse_scope") == "customer_facing" and int(row.get("excerpt_max_chars") or 0) > 0:
            cap = int(row.get("excerpt_max_chars") or 0)
            if len(_normalize_ws(row.get("body"))) > cap:
                reasons.append("excerpt_cap_exceeded")
        if row.get("emb_dim") != signature["dim"] or row.get("emb_model") != signature["model"]:
            reasons.append("embedding_signature_mismatch")
        if reasons:
            dlq.append(
                DlqRecord(
                    tier=1,
                    item_type=row.get("item_type") or "knowledge_item",
                    error_message=", ".join(reasons),
                    raw_data=row,
                    reason_code=reasons[0],
                    source_name=row.get("source") or "unknown",
                    correlation_id=correlation_id,
                )
            )
            continue
        valid_rows.append(row)
    return pd.DataFrame(valid_rows), dlq


def _preflight(conn: Any) -> None:
    required_tables = {"edu_knowledge_items", "dead_letter_queue", "pipeline_runs"}
    required_views = {"edu_knowledge_items_customer_facing"}
    required_columns = {
        "dead_letter_queue": {
            "id",
            "tier",
            "pipeline_name",
            "item_id",
            "item_type",
            "error_message",
            "raw_data",
            "reason_code",
            "correlation_id",
            "source_name",
            "external_key",
            "first_seen_correlation_id",
            "last_seen_correlation_id",
            "occurrence_count",
            "last_seen_at",
            "created_at",
            "resolved",
        },
        "pipeline_runs": {
            "correlation_id",
            "pipeline_name",
            "status",
            "error",
            "started_at",
            "finished_at",
            "input_count",
            "success_count",
            "skipped_count",
            "dlq_count",
            "adapter_failures",
        },
        "edu_knowledge_items": {
            "natural_key",
            "source",
            "source_ref",
            "source_id",
            "source_url",
            "source_kind",
            "provenance",
            "rights_class",
            "reuse_scope",
            "excerpt_max_chars",
            "verbatim_allowed",
            "segment",
            "item_type",
            "title",
            "body",
            "cite",
            "lang",
            "quality_score",
            "keywords",
            "emb_model",
            "emb_dim",
            "collected_at",
            "updated_at",
        },
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            """
        )
        rows = cur.fetchall()
    tables: dict[str, set[str]] = {}
    for table_name, column_name in rows:
        tables.setdefault(table_name, set()).add(column_name)
    missing_tables = sorted(required_tables - set(tables))
    if missing_tables:
        raise RuntimeError(f"schema_preflight_missing_tables:{','.join(missing_tables)}")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT viewname, definition
            FROM pg_views
            WHERE schemaname = 'public'
            """
        )
        view_rows = cur.fetchall()
    views = {view_name: definition for view_name, definition in view_rows}
    missing_views = sorted(required_views - set(views))
    if missing_views:
        raise RuntimeError(f"schema_preflight_missing_views:{','.join(missing_views)}")
    missing_columns: list[str] = []
    for table_name, columns in required_columns.items():
        table_cols = tables.get(table_name, set())
        missing = columns - table_cols
        for column in sorted(missing):
            missing_columns.append(f"{table_name}.{column}")
    if missing_columns:
        raise RuntimeError(f"schema_preflight_missing_columns:{','.join(missing_columns)}")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'edu_knowledge_items'
              AND indexdef ILIKE '%%UNIQUE%%(natural_key%%'
            LIMIT 1
            """
        )
        unique_index = cur.fetchone()
    if not unique_index:
        raise RuntimeError("schema_preflight_missing_unique_index:edu_knowledge_items.natural_key")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'dead_letter_queue'
              AND indexname = 'idx_dlq_unresolved_reuse'
            LIMIT 1
            """
        )
        dlq_unique_index = cur.fetchone()
    if not dlq_unique_index:
        raise RuntimeError("schema_preflight_missing_unique_index:dead_letter_queue.idx_dlq_unresolved_reuse")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'dead_letter_queue'
              AND indexname = 'idx_dlq_unresolved_reuse'
            LIMIT 1
            """
        )
        dlq_indexdef_row = cur.fetchone()
    dlq_indexdef = (dlq_indexdef_row[0] if dlq_indexdef_row else "") or ""
    if not _dlq_index_contract_ok(dlq_indexdef):
        raise RuntimeError("schema_preflight_invalid_indexdef:dead_letter_queue.idx_dlq_unresolved_reuse")
    if not _customer_facing_view_contract_ok(views["edu_knowledge_items_customer_facing"]):
        raise RuntimeError("schema_preflight_invalid_viewdef:edu_knowledge_items_customer_facing")


def _preflight_bootstrap(conn: Any) -> None:
    required_columns = {
        "pipeline_runs": {
            "id",
            "correlation_id",
            "pipeline_name",
            "status",
            "error",
            "started_at",
            "finished_at",
            "input_count",
            "success_count",
            "skipped_count",
            "dlq_count",
            "adapter_failures",
        },
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'pipeline_runs'
            """
        )
        rows = cur.fetchall()
    if not rows:
        raise RuntimeError("schema_preflight_missing_tables:pipeline_runs")
    table_cols = {column_name for _table_name, column_name, _data_type in rows}
    missing = sorted(required_columns["pipeline_runs"] - table_cols)
    if missing:
        raise RuntimeError(f"schema_preflight_missing_columns:{','.join(f'pipeline_runs.{col}' for col in missing)}")
    column_types = {column_name: data_type for _table_name, column_name, data_type in rows}
    correlation_id_type = _normalize_sql_text(column_types.get("correlation_id", ""))
    if correlation_id_type not in TEXT_COMPATIBLE_TYPES:
        raise RuntimeError(
            f"schema_preflight_invalid_column_type:pipeline_runs.correlation_id:{column_types.get('correlation_id', 'unknown')}"
        )


def _record_pipeline_start(run: RunStats, status: str = "running") -> int:
    conn = get_connection()
    try:
        available = _pipeline_run_columns(conn)
        columns = ["correlation_id"]
        values: list[Any] = [run.correlation_id]
        placeholders = ["%s"]
        if "pipeline_name" in available:
            columns.append("pipeline_name")
            values.append("edu_data_analysis_agent")
            placeholders.append("%s")
        if "status" in available:
            columns.append("status")
            values.append(status)
            placeholders.append("%s")
        if "started_at" in available:
            columns.append("started_at")
            placeholders.append("NOW()")
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO pipeline_runs ({", ".join(columns)})
                VALUES ({", ".join(placeholders)})
                RETURNING id
                """,
                values,
            )
            run_id = cur.fetchone()[0]
        conn.commit()
        return int(run_id)
    finally:
        conn.close()


def _pipeline_run_columns(conn: Any) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'pipeline_runs'
            """
        )
        return {row[0] for row in cur.fetchall()}


def _update_pipeline_status(run: RunStats, status: str, error: str | None = None) -> None:
    if run.run_id is None:
        raise RuntimeError("pipeline_run_id_missing")
    conn = get_connection()
    try:
        available = _pipeline_run_columns(conn)
        assignments: list[sql.Composed] = []
        params: list[Any] = []
        if "status" in available:
            assignments.append(sql.SQL("status = %s"))
            params.append(status)
        if "error" in available:
            assignments.append(sql.SQL("error = %s"))
            params.append(error)
        if not assignments:
            raise RuntimeError("pipeline_runs_missing_update_columns")
        query = sql.SQL("UPDATE pipeline_runs SET {} WHERE id = %s").format(sql.SQL(", ").join(assignments))
        params.append(run.run_id)
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
    finally:
        conn.close()


def _record_pipeline_finish(run: RunStats, status: str, error: str | None = None) -> None:
    conn = get_connection()
    try:
        if run.run_id is None:
            raise RuntimeError("pipeline_run_id_missing")
        available = _pipeline_run_columns(conn)
        assignments: list[sql.Composed] = []
        params: list[Any] = []
        if "finished_at" in available:
            assignments.append(sql.SQL("finished_at = NOW()"))
        if "pipeline_name" in available:
            assignments.append(sql.SQL("pipeline_name = %s"))
            params.append("edu_data_analysis_agent")
        if "status" in available:
            assignments.append(sql.SQL("status = %s"))
            params.append(status)
        if "error" in available:
            assignments.append(sql.SQL("error = %s"))
            params.append(error)
        if "input_count" in available:
            assignments.append(sql.SQL("input_count = %s"))
            params.append(run.input_count)
        if "success_count" in available:
            assignments.append(sql.SQL("success_count = %s"))
            params.append(run.success_count)
        if "skipped_count" in available:
            assignments.append(sql.SQL("skipped_count = %s"))
            params.append(run.skipped_count)
        if "dlq_count" in available:
            assignments.append(sql.SQL("dlq_count = %s"))
            params.append(run.dlq_count)
        if "adapter_failures" in available:
            assignments.append(sql.SQL("adapter_failures = %s"))
            params.append(run.adapter_failures)
        if not assignments:
            raise RuntimeError("pipeline_runs_missing_finish_columns")
        query = sql.SQL("UPDATE pipeline_runs SET {} WHERE id = %s").format(sql.SQL(", ").join(assignments))
        params.append(run.run_id)
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
    finally:
        conn.close()


def _write_dlq(conn: Any, entries: list[DlqRecord]) -> None:
    if not entries:
        return
    with conn.cursor() as cur:
        for entry in entries:
            external_key = str(
                entry.raw_data.get("natural_key")
                or entry.raw_data.get("source_id")
                or entry.raw_data.get("source_url")
                or entry.raw_data.get("path")
                or _sha256(json.dumps(entry.raw_data, ensure_ascii=False, sort_keys=True))
            )
            cur.execute(
                """
                INSERT INTO dead_letter_queue (
                    tier, pipeline_name, item_id, item_type, error_message, raw_data, reason_code, correlation_id,
                    source_name, external_key, first_seen_correlation_id, last_seen_correlation_id,
                    occurrence_count, last_seen_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (pipeline_name, tier, external_key, reason_code, item_type) WHERE resolved = FALSE DO UPDATE
                    SET error_message = EXCLUDED.error_message,
                        raw_data = EXCLUDED.raw_data,
                        correlation_id = EXCLUDED.correlation_id,
                        source_name = EXCLUDED.source_name,
                        last_seen_correlation_id = EXCLUDED.last_seen_correlation_id,
                        occurrence_count = dead_letter_queue.occurrence_count + 1,
                        last_seen_at = NOW()
                """,
                (
                    entry.tier,
                    "edu_data_analysis_agent",
                    None,
                    entry.item_type,
                    entry.error_message,
                    Json(entry.raw_data),
                    entry.reason_code,
                    entry.correlation_id,
                    entry.source_name,
                    external_key,
                    entry.correlation_id,
                    entry.correlation_id,
                    1,
                ),
            )


def _upsert_knowledge_items(conn: Any, frame: pd.DataFrame) -> None:
    if frame.empty:
        return
    columns = [
        "source_ref",
        "natural_key",
        "source",
        "source_id",
        "source_url",
        "source_kind",
        "provenance",
        "rights_class",
        "reuse_scope",
        "excerpt_max_chars",
        "verbatim_allowed",
        "segment",
        "item_type",
        "title",
        "body",
        "cite",
        "lang",
        "quality_score",
        "keywords",
        "emb_model",
        "emb_dim",
        "collected_at",
    ]
    rows = []
    for row in frame.to_dict(orient="records"):
        rows.append(
            tuple(
                Json(row[col]) if col == "keywords" else row[col]
                for col in columns
            )
        )
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"""
            INSERT INTO edu_knowledge_items ({", ".join(columns)})
            VALUES %s
            ON CONFLICT (natural_key) DO UPDATE SET
                source_ref = EXCLUDED.source_ref,
                source = EXCLUDED.source,
                source_id = EXCLUDED.source_id,
                source_url = EXCLUDED.source_url,
                source_kind = EXCLUDED.source_kind,
                provenance = EXCLUDED.provenance,
                rights_class = EXCLUDED.rights_class,
                reuse_scope = EXCLUDED.reuse_scope,
                excerpt_max_chars = EXCLUDED.excerpt_max_chars,
                verbatim_allowed = EXCLUDED.verbatim_allowed,
                segment = EXCLUDED.segment,
                item_type = EXCLUDED.item_type,
                title = EXCLUDED.title,
                body = EXCLUDED.body,
                cite = EXCLUDED.cite,
                lang = EXCLUDED.lang,
                quality_score = EXCLUDED.quality_score,
                keywords = EXCLUDED.keywords,
                emb_model = EXCLUDED.emb_model,
                emb_dim = EXCLUDED.emb_dim,
                collected_at = EXCLUDED.collected_at,
                updated_at = NOW()
            """,
            rows,
        )


def _mark_pipeline_success_in_tx(conn: Any, run: RunStats) -> None:
    if run.run_id is None:
        raise RuntimeError("pipeline_run_id_missing")
    with conn.cursor() as cur:
       cur.execute(
            """
            UPDATE pipeline_runs
               SET finished_at = NOW(),
                   pipeline_name = %s,
                   status = %s,
                   error = NULL,
                   input_count = %s,
                   success_count = %s,
                   skipped_count = %s,
                   dlq_count = %s,
                   adapter_failures = %s
             WHERE id = %s
            """,
            (
                "edu_data_analysis_agent",
                "success",
                run.input_count,
                run.success_count,
                run.skipped_count,
                run.dlq_count,
                run.adapter_failures,
                run.run_id,
            ),
        )


def _run_db_persist(run: RunStats, frame: pd.DataFrame, dlq: list[DlqRecord]) -> None:
    conn = get_connection()
    try:
        _upsert_knowledge_items(conn, frame)
        _write_dlq(conn, dlq)
        _mark_pipeline_success_in_tx(conn, run)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_agent(
    research_dirs: list[Path] | None = None,
    transcripts_dir: Path | None = None,
    anchors_path: Path | None = None,
    dry_run: bool = False,
    correlation_id: str | None = None,
) -> tuple[RunStats, pd.DataFrame, list[DlqRecord]]:
    run = RunStats(correlation_id=correlation_id or uuid.uuid4().hex[:12])
    if dry_run:
        frame, dlq, built = build_knowledge_dataframe(
            research_dirs=research_dirs,
            transcripts_dir=transcripts_dir,
            anchors_path=anchors_path,
            correlation_id=run.correlation_id,
        )
        run.input_count = built.input_count
        run.success_count = built.success_count
        run.skipped_count = built.skipped_count
        run.dlq_count = built.dlq_count
        run.adapter_failures = built.adapter_failures
        return run, frame, dlq

    try:
        preflight_conn = get_connection()
        try:
            _preflight_bootstrap(preflight_conn)
        finally:
            preflight_conn.close()
        run.run_id = _record_pipeline_start(run, status="preflight")
        preflight_conn = get_connection()
        try:
            _preflight(preflight_conn)
        finally:
            preflight_conn.close()
        get_embedding_signature()
        _update_pipeline_status(run, "running")
        frame, dlq, built = build_knowledge_dataframe(
            research_dirs=research_dirs,
            transcripts_dir=transcripts_dir,
            anchors_path=anchors_path,
            correlation_id=run.correlation_id,
        )
        run.input_count = built.input_count
        run.success_count = built.success_count
        run.skipped_count = built.skipped_count
        run.dlq_count = built.dlq_count
        run.adapter_failures = built.adapter_failures
        _run_db_persist(run, frame, dlq)
        return run, frame, dlq
    except Exception as exc:
        try:
            if run.run_id is None:
                try:
                    run.run_id = _record_pipeline_start(run, status="failed")
                except Exception:
                    run.run_id = None
            _record_pipeline_finish(run, "failed", str(exc))
        except Exception as finish_exc:
            print(f"warning: pipeline_runs failed audit update failed: {finish_exc}", file=sys.stderr)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Edu Query Engine P1 Data Analysis Agent")
    parser.add_argument("--dry-run", action="store_true", help="DB 적재 없이 정규화/검증만 수행")
    parser.add_argument("--correlation-id", help="pipeline_runs/dead_letter_queue correlation_id")
    args = parser.parse_args()

    run, frame, dlq = run_agent(dry_run=args.dry_run, correlation_id=args.correlation_id)
    report = {
        "correlation_id": run.correlation_id,
        "input_count": run.input_count,
        "success_count": run.success_count,
        "skipped_count": run.skipped_count,
        "dlq_count": run.dlq_count,
        "adapter_failures": run.adapter_failures,
        "sample_natural_keys": frame["natural_key"].head(5).tolist() if not frame.empty else [],
        "sample_dlq_reason_codes": [entry.reason_code for entry in dlq[:5]],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
