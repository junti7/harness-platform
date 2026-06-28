#!/usr/bin/env python3
"""교육 상담 RAG 인덱스 빌더 (증분).

Deep Research로 정제된 edu_consulting refined_outputs 전체 + 에버그린 앵커를
현재 활성 임베딩 백엔드(Google 또는 Ollama)로 임베딩해 의향기반 검색용
인덱스(evidence_index.json)를 만든다.

핵심: **증분(incremental)**. 매일 새로 정제된 항목만 임베딩해 인덱스에 append 하므로,
파이프라인이 돌수록 RAG 코퍼스가 계속 두꺼워진다(품질이 날로 탄탄해짐).

  python scripts/build_edu_evidence_index.py            # 증분(신규만 임베딩)
  python scripts/build_edu_evidence_index.py --rebuild  # 전체 재임베딩
  python scripts/build_edu_evidence_index.py --stats     # 현재 인덱스 통계만

run_pipeline.py 말미에서 증분 모드로 자동 호출된다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(PROJECT_ROOT / ".env", override=False)

from core.database import execute_query  # noqa: E402
from core.logger import HarnessLogger  # noqa: E402
from core.embeddings import embed_documents, embedding_backend_signature  # noqa: E402
from scripts.refresh_edu_evidence_bank import (  # noqa: E402
    _load_anchors,
    _cites_from_raw_data,
    _source_label,
    infer_segment,
    infer_source_kind,
    extract_source_url,
    is_low_quality_evidence,
    EDU_DIR,
)

INDEX_PATH = EDU_DIR / "evidence_index.json"


def _fetch_all_refined(max_refined: int | None = None) -> list[dict]:
    """edu_consulting 정제분 전체를 cite 코퍼스 항목으로 변환 (window·cap 없음)."""
    if max_refined == 0:
        return []
    rows = execute_query(
        """
        SELECT ro.id, ro.final_body, ro.created_at, rs.source, rs.raw_data
        FROM refined_outputs ro
        JOIN filtered_signals fs ON fs.id = ro.filtered_signal_id
        JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE COALESCE(fs.domain, 'physical_ai') = 'edu_consulting'
        ORDER BY ro.created_at DESC
        """ + ("LIMIT %s" if max_refined and max_refined > 0 else "") + """
        """,
        (max_refined,) if max_refined and max_refined > 0 else None,
        fetch=True,
    ) or []
    items: list[dict] = []
    seen_prefix: set[str] = set()  # 첫머리 16자 기준 전역 중복 제거(다양성 보존)
    for r in rows:
        body = r["final_body"]
        try:
            body = json.loads(body) if isinstance(body, str) else (body or {})
        except Exception:
            continue
        if body.get("is_relevant") is False:
            continue
        created = r["created_at"]
        src = _source_label(r["source"], r["raw_data"])
        source_kind = infer_source_kind(src, r["raw_data"], r["source"])
        # Customer-facing citations must come from source-owned raw text, not
        # from Tier 3 LLM synthesis in refined_outputs.final_body.
        for n, cite in enumerate(_cites_from_raw_data(r["raw_data"])):
            if is_low_quality_evidence(cite, src, r["raw_data"], r["source"]):
                continue
            prefix = cite[:16]
            if prefix in seen_prefix:
                continue  # 전역 중복(다른 항목과도) 제거
            seen_prefix.add(prefix)
            source_url = extract_source_url(r["raw_data"])
            items.append({
                "id": f"fresh-{r['id']}-{n}",
                "type": "최신 동향",
                "segment": infer_segment(r["raw_data"], r["source"]),
                "provenance": "pipeline",
                "cite": cite,
                "source": src,
                "source_name": r["source"],
                "source_url": source_url,
                "source_ref": source_url or f"refined_output:{r['id']}",
                "source_kind": source_kind,
                "refined_output_id": r["id"],
                "collected_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
            })
    return items


def _corpus(max_refined: int | None = None) -> list[dict]:
    """앵커 + 전체 정제분을 합친 코퍼스 (id 기준 dedup, 앵커 우선)."""
    anchors = [{
        "id": a["id"], "type": a.get("type", "근거"), "segment": a.get("segment", "both"),
        "provenance": "anchor", "cite": a["cite"], "source": a.get("source", ""),
        "source_name": a.get("source_name", ""),
        "source_url": a.get("source_url") or a.get("url") or a.get("link") or "",
        "source_ref": a.get("source_ref") or a.get("source_url") or a.get("url") or "",
        "source_kind": a.get("source_kind") or infer_source_kind(a.get("source", "")),
    } for a in _load_anchors() if a.get("cite")]
    by_id = {a["id"]: a for a in anchors}
    for it in _fetch_all_refined(max_refined=max_refined):
        by_id.setdefault(it["id"], it)
    return list(by_id.values())


def _load_index() -> dict:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        sig = embedding_backend_signature(resolve_runtime=True)
        return {"provider": sig["provider"], "model": sig["model"], "dim": sig["dim"], "items": []}


def build(rebuild: bool = False, max_refined: int | None = None) -> dict:
    log = HarnessLogger(tier=3, correlation_id="edu-index")
    corpus = _corpus(max_refined=max_refined)
    log.info(f"코퍼스 {len(corpus)}건 (앵커+전체 정제분)")
    sig = embedding_backend_signature(resolve_runtime=True)

    index = {"provider": sig["provider"], "model": sig["model"], "dim": sig["dim"], "items": []} if rebuild else _load_index()
    # 모델/차원이 바뀌었으면 전체 재빌드
    if (
        index.get("provider") != sig["provider"]
        or index.get("model") != sig["model"]
        or index.get("dim") != sig["dim"]
    ):
        log.info(
            "임베딩 백엔드 변경 — 전체 재빌드 "
            f"({index.get('provider')}/{index.get('model')} -> {sig['provider']}/{sig['model']})"
        )
        index = {"provider": sig["provider"], "model": sig["model"], "dim": sig["dim"], "items": []}

    existing = {it["id"]: it for it in index.get("items", [])}
    corpus_ids = {c["id"] for c in corpus}
    # 코퍼스에서 사라진 항목은 인덱스에서도 제거 (정합 유지)
    existing = {cid: it for cid, it in existing.items() if cid in corpus_ids}

    # 기존 임베딩은 유지하되, source_kind/segment/source 같은 메타는 최신 corpus로 backfill한다.
    corpus_by_id = {c["id"]: c for c in corpus}
    for cid, item in list(existing.items()):
        meta = corpus_by_id.get(cid)
        if not meta:
            continue
        for key in ("type", "segment", "provenance", "cite", "source", "source_name", "source_url", "source_ref", "source_kind", "refined_output_id", "collected_at"):
            if meta.get(key):
                item[key] = meta[key]

    new_items = [c for c in corpus if c["id"] not in existing]
    log.info(f"기존 {len(existing)}건 / 신규 임베딩 대상 {len(new_items)}건")

    if new_items:
        embs = embed_documents([c["cite"] for c in new_items])
        for c, emb in zip(new_items, embs):
            existing[c["id"]] = {**c, "emb": [round(x, 6) for x in emb]}
        log.info(f"신규 {len(new_items)}건 임베딩 완료")

    index["items"] = list(existing.values())
    index["provider"] = sig["provider"]
    index["model"] = sig["model"]
    index["dim"] = sig["dim"]
    index["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index["count"] = len(index["items"])
    return index


def main() -> int:
    ap = argparse.ArgumentParser(description="교육 RAG 인덱스 빌더(증분)")
    ap.add_argument("--rebuild", action="store_true", help="전체 재임베딩")
    ap.add_argument("--stats", action="store_true", help="현재 인덱스 통계만 출력")
    ap.add_argument("--max-refined", type=int, default=None, help="정제분 최대 반영 수(0이면 앵커만)")
    args = ap.parse_args()

    if args.stats:
        idx = _load_index()
        print(
            f"provider={idx.get('provider')} model={idx.get('model')} dim={idx.get('dim')} "
            f"count={idx.get('count', len(idx.get('items', [])))} built_at={idx.get('built_at')}"
        )
        return 0

    index = build(rebuild=args.rebuild, max_refined=args.max_refined)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"인덱스 저장: {INDEX_PATH} (총 {index['count']}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
