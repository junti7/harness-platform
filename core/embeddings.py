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


def _log_embed_cost(chunk: list[str]) -> None:
    """임베딩 토큰(입력 전용)을 추정해 api_cost_log에 기록 — 비용 가시성 확보."""
    try:
        from adapters.content.refiner import log_api_cost
        est_tokens = sum(len(t) for t in chunk) // 4  # 대략 4자=1토큰
        log_api_cost(EMBED_MODEL, est_tokens, 0, provider="google")
    except Exception:
        pass


def _embed(texts: list[str], task_type: str, retries: int = 3) -> list[list[float]]:
    client = build_client()
    cfg = types.EmbedContentConfig(output_dimensionality=EMBED_DIM, task_type=task_type)
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        chunk = texts[i : i + _BATCH]
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                resp = client.models.embed_content(model=EMBED_MODEL, contents=chunk, config=cfg)
                out.extend([list(e.values) for e in resp.embeddings])
                _log_embed_cost(chunk)  # 비용 추적 사각지대 제거(임베딩도 기록)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < retries - 1:
                    time.sleep(1.0 * (attempt + 1))
        else:
            raise RuntimeError(f"임베딩 실패(batch {i}): {last_exc}")
    return out


def embed_documents(texts: list[str]) -> list[list[float]]:
    """코퍼스(근거 자료) 임베딩 — 오프라인 빌드라 재시도 넉넉히."""
    return _embed(list(texts), "RETRIEVAL_DOCUMENT", retries=3)


def embed_query(text: str) -> list[float]:
    """고객 질의/대화 임베딩 (단건) — 핫패스라 빠르게 실패해 랜덤 폴백으로 degrade."""
    return _embed([text], "RETRIEVAL_QUERY", retries=1)[0]


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v)) or 1.0


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (_norm(a) * _norm(b))


def cosine_topk(query: list[float], corpus: Iterable[tuple[str, list[float]]], k: int) -> list[tuple[str, float]]:
    """corpus=[(id, vector)...] 중 query와 코사인 유사도 top-k (id, score) 반환.

    차원이 다른 벡터는 건너뛴다(zip 조용한 절단으로 잘못된 유사도 산출 방지).
    """
    qn = _norm(query)
    qdim = len(query)
    scored: list[tuple[str, float]] = []
    for cid, vec in corpus:
        if not vec or len(vec) != qdim:   # 차원 불일치 → 스킵 (인덱스 모델 변경 등)
            continue
        dot = sum(x * y for x, y in zip(query, vec))
        scored.append((cid, dot / (qn * _norm(vec))))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]
