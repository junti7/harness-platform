"""교육 상담 RAG용 임베딩 유틸 (gemini-embedding-001).

- 문서(코퍼스)는 task_type=RETRIEVAL_DOCUMENT, 질의는 RETRIEVAL_QUERY로 임베딩해
  검색 정합도를 높인다.
- output_dimensionality=768 (Matryoshka) — 품질을 크게 잃지 않으면서 인덱스를 가볍게.
- 외부 API 호출이므로 배치 + 재시도. 실패는 호출부가 graceful fallback 하도록 예외 전파.
"""
from __future__ import annotations

import math
import time
from typing import Iterable

from google.genai import types

from core.gemini_sdk import build_client

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
_BATCH = 64


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    client = build_client()
    cfg = types.EmbedContentConfig(output_dimensionality=EMBED_DIM, task_type=task_type)
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        chunk = texts[i : i + _BATCH]
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = client.models.embed_content(model=EMBED_MODEL, contents=chunk, config=cfg)
                out.extend([list(e.values) for e in resp.embeddings])
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))
        else:
            raise RuntimeError(f"임베딩 실패(batch {i}): {last_exc}")
    return out


def embed_documents(texts: list[str]) -> list[list[float]]:
    """코퍼스(근거 자료) 임베딩."""
    return _embed(list(texts), "RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    """고객 질의/대화 임베딩 (단건)."""
    return _embed([text], "RETRIEVAL_QUERY")[0]


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v)) or 1.0


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (_norm(a) * _norm(b))


def cosine_topk(query: list[float], corpus: Iterable[tuple[str, list[float]]], k: int) -> list[tuple[str, float]]:
    """corpus=[(id, vector)...] 중 query와 코사인 유사도 top-k (id, score) 반환."""
    qn = _norm(query)
    scored: list[tuple[str, float]] = []
    for cid, vec in corpus:
        if not vec:
            continue
        dot = sum(x * y for x, y in zip(query, vec))
        scored.append((cid, dot / (qn * _norm(vec))))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]
