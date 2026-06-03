#!/usr/bin/env python3
"""교육 상담 RAG 인덱스 빌더 (증분).

Deep Research로 정제된 edu_consulting refined_outputs 전체 + 에버그린 앵커를
gemini-embedding-001로 임베딩해 의향기반 검색용 인덱스(evidence_index.json)를 만든다.

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
load_dotenv(PROJECT_ROOT / ".env", override=True)

from core.database import execute_query  # noqa: E402
from core.logger import HarnessLogger  # noqa: E402
from core.embeddings import embed_documents, EMBED_MODEL, EMBED_DIM  # noqa: E402
from scripts.refresh_edu_evidence_bank import (  # noqa: E402
    _load_anchors,
    _cite_from_refined,
    _source_label,
    EDU_DIR,
)

INDEX_PATH = EDU_DIR / "evidence_index.json"


def _fetch_all_refined() -> list[dict]:
    """edu_consulting 정제분 전체를 cite 코퍼스 항목으로 변환 (window·cap 없음)."""
    rows = execute_query(
        """
        SELECT ro.id, ro.final_body, ro.created_at, rs.source, rs.raw_data
        FROM refined_outputs ro
        JOIN filtered_signals fs ON fs.id = ro.filtered_signal_id
        JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE COALESCE(fs.domain, 'physical_ai') = 'edu_consulting'
        ORDER BY ro.created_at DESC
        """,
        fetch=True,
    ) or []
    items: list[dict] = []
    seen_cites: set[str] = set()
    for r in rows:
        body = r["final_body"]
        try:
            body = json.loads(body) if isinstance(body, str) else (body or {})
        except Exception:
            continue
        if body.get("is_relevant") is False:
            continue
        cite = _cite_from_refined(body)
        if not cite or cite in seen_cites:
            continue
        seen_cites.add(cite)
        created = r["created_at"]
        items.append({
            "id": f"fresh-{r['id']}",
            "type": "최신 동향",
            "segment": "parent",
            "provenance": "pipeline",
            "cite": cite,
            "source": _source_label(r["source"], r["raw_data"]),
            "collected_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
        })
    return items


def _corpus() -> list[dict]:
    """앵커 + 전체 정제분을 합친 코퍼스 (id 기준 dedup, 앵커 우선)."""
    anchors = [{
        "id": a["id"], "type": a.get("type", "근거"), "segment": a.get("segment", "both"),
        "provenance": "anchor", "cite": a["cite"], "source": a.get("source", ""),
    } for a in _load_anchors() if a.get("cite")]
    by_id = {a["id"]: a for a in anchors}
    for it in _fetch_all_refined():
        by_id.setdefault(it["id"], it)
    return list(by_id.values())


def _load_index() -> dict:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"model": EMBED_MODEL, "dim": EMBED_DIM, "items": []}


def build(rebuild: bool = False) -> dict:
    log = HarnessLogger(tier=3, correlation_id="edu-index")
    corpus = _corpus()
    log.info(f"코퍼스 {len(corpus)}건 (앵커+전체 정제분)")

    index = {"model": EMBED_MODEL, "dim": EMBED_DIM, "items": []} if rebuild else _load_index()
    # 모델/차원이 바뀌었으면 전체 재빌드
    if index.get("model") != EMBED_MODEL or index.get("dim") != EMBED_DIM:
        log.info("임베딩 모델/차원 변경 — 전체 재빌드")
        index = {"model": EMBED_MODEL, "dim": EMBED_DIM, "items": []}

    existing = {it["id"]: it for it in index.get("items", [])}
    corpus_ids = {c["id"] for c in corpus}
    # 코퍼스에서 사라진 항목은 인덱스에서도 제거 (정합 유지)
    existing = {cid: it for cid, it in existing.items() if cid in corpus_ids}

    new_items = [c for c in corpus if c["id"] not in existing]
    log.info(f"기존 {len(existing)}건 / 신규 임베딩 대상 {len(new_items)}건")

    if new_items:
        embs = embed_documents([c["cite"] for c in new_items])
        for c, emb in zip(new_items, embs):
            existing[c["id"]] = {**c, "emb": [round(x, 6) for x in emb]}
        log.info(f"신규 {len(new_items)}건 임베딩 완료")

    index["items"] = list(existing.values())
    index["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index["count"] = len(index["items"])
    return index


def main() -> int:
    ap = argparse.ArgumentParser(description="교육 RAG 인덱스 빌더(증분)")
    ap.add_argument("--rebuild", action="store_true", help="전체 재임베딩")
    ap.add_argument("--stats", action="store_true", help="현재 인덱스 통계만 출력")
    args = ap.parse_args()

    if args.stats:
        idx = _load_index()
        print(f"model={idx.get('model')} dim={idx.get('dim')} count={idx.get('count', len(idx.get('items', [])))} built_at={idx.get('built_at')}")
        return 0

    index = build(rebuild=args.rebuild)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"인덱스 저장: {INDEX_PATH} (총 {index['count']}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
