"""교육 상담 RAG용 임베딩 유틸.

- Google Gemini 임베딩을 기본으로 쓰되, 설정 시 Ollama 로컬 임베딩으로 전환/비상 유지 가능.
- 문서(코퍼스)는 RETRIEVAL_DOCUMENT, 질의는 RETRIEVAL_QUERY로 분리해 검색 정합도 유지.
- 인덱스와 질의가 다른 백엔드로 섞이지 않도록 provider/model/dim 시그니처를 노출한다.
"""
from __future__ import annotations

import math
import os
import time
from collections.abc import Callable, Iterable
from typing import Any

import httpx
from google.genai import types

from core.gemini_sdk import build_client, gemini_api_key

_BATCH = 64
_GOOGLE_EMBED_MODEL = os.getenv("GOOGLE_EMBED_MODEL", "gemini-embedding-001").strip()
_GOOGLE_EMBED_DIM = int(os.getenv("GOOGLE_EMBED_DIM", "768"))
_OLLAMA_EMBED_MODEL = (
    os.getenv("OLLAMA_EMBED_MODEL")
    or os.getenv("LOCAL_EMBED_MODEL")
    or "nomic-embed-text"
).strip()
_OLLAMA_EMBED_DIM = int(os.getenv("OLLAMA_EMBED_DIM", "768"))


def _provider_mode() -> str:
    mode = os.getenv("EMBEDDING_PROVIDER_MODE", "google").strip().lower()
    return mode if mode in {"google", "ollama", "auto"} else "google"


def _ollama_hosts() -> list[str]:
    hosts: list[str] = []
    for candidate in [
        os.getenv("OLLAMA_REMOTE_HOST", "").strip(),
        os.getenv("OLLAMA_HOST", "http://localhost:11434").strip(),
    ]:
        if candidate and candidate not in hosts:
            hosts.append(candidate)
    return hosts


def _probe_ollama(host: str) -> bool:
    try:
        resp = httpx.get(f"{host}/api/tags", timeout=2.5)
        return resp.status_code == 200
    except Exception:
        return False


def _google_available() -> bool:
    return bool(gemini_api_key())


def embedding_backend_signature(resolve_runtime: bool = False) -> dict[str, Any]:
    mode = _provider_mode()
    if not resolve_runtime:
        if mode == "ollama":
            return {"provider": "ollama", "model": _OLLAMA_EMBED_MODEL, "dim": _OLLAMA_EMBED_DIM}
        return {"provider": "google", "model": _GOOGLE_EMBED_MODEL, "dim": _GOOGLE_EMBED_DIM}
    if mode == "ollama":
        return {"provider": "ollama", "model": _OLLAMA_EMBED_MODEL, "dim": _OLLAMA_EMBED_DIM}
    if mode == "auto":
        if _google_available():
            return {"provider": "google", "model": _GOOGLE_EMBED_MODEL, "dim": _GOOGLE_EMBED_DIM}
        return {"provider": "ollama", "model": _OLLAMA_EMBED_MODEL, "dim": _OLLAMA_EMBED_DIM}
    return {"provider": "google", "model": _GOOGLE_EMBED_MODEL, "dim": _GOOGLE_EMBED_DIM}


_SIG = embedding_backend_signature(resolve_runtime=False)
EMBED_MODEL = str(_SIG["model"])
EMBED_DIM = int(_SIG["dim"])


def _log_embed_cost(chunk: list[str], model: str, provider: str) -> None:
    """임베딩 토큰(입력 전용)을 추정해 api_cost_log에 기록 — 비용 가시성 확보."""
    try:
        from adapters.content.refiner import log_api_cost

        est_tokens = sum(len(t) for t in chunk) // 4  # 대략 4자=1토큰
        log_api_cost(model, est_tokens, 0, provider=provider)
    except Exception:
        pass


def _embed_google(texts: list[str], task_type: str, dim: int) -> list[list[float]]:
    client = build_client()
    cfg = types.EmbedContentConfig(output_dimensionality=dim, task_type=task_type)
    resp = client.models.embed_content(model=_GOOGLE_EMBED_MODEL, contents=texts, config=cfg)
    _log_embed_cost(texts, _GOOGLE_EMBED_MODEL, "google")
    return [list(e.values) for e in resp.embeddings]


def _extract_ollama_embedding(payload: dict[str, Any], expected_count: int) -> list[list[float]]:
    if isinstance(payload.get("embeddings"), list) and payload["embeddings"]:
        rows = payload["embeddings"]
        if rows and isinstance(rows[0], list):
            return [list(map(float, row)) for row in rows]
    if isinstance(payload.get("embedding"), list):
        emb = list(map(float, payload["embedding"]))
        return [emb for _ in range(expected_count)]
    raise RuntimeError("ollama embedding payload missing vector")


def _embed_ollama(texts: list[str], dim: int) -> list[list[float]]:
    payload = {
        "model": _OLLAMA_EMBED_MODEL,
        "input": texts,
        "truncate": True,
        "options": {"num_ctx": int(os.getenv("OLLAMA_EMBED_NUM_CTX", "8192"))},
    }
    last_exc: Exception | None = None
    for host in _ollama_hosts():
        if not _probe_ollama(host):
            continue
        try:
            resp = httpx.post(f"{host}/api/embed", json=payload, timeout=60)
            resp.raise_for_status()
            vectors = _extract_ollama_embedding(resp.json() or {}, len(texts))
            if any(len(vec) != dim for vec in vectors):
                raise RuntimeError(f"ollama embedding dim mismatch expected={dim}")
            _log_embed_cost(texts, _OLLAMA_EMBED_MODEL, "ollama")
            return vectors
        except Exception as exc:
            last_exc = exc
            continue
    raise RuntimeError(f"ollama_embedding_unavailable: {last_exc}")


def _resolve_backend() -> tuple[dict[str, Any], Callable[[list[str], str], list[list[float]]]]:
    mode = _provider_mode()
    if mode == "ollama":
        sig = {"provider": "ollama", "model": _OLLAMA_EMBED_MODEL, "dim": _OLLAMA_EMBED_DIM}
        return sig, lambda texts, _task_type: _embed_ollama(texts, sig["dim"])
    if mode == "auto":
        if _google_available():
            sig = {"provider": "google", "model": _GOOGLE_EMBED_MODEL, "dim": _GOOGLE_EMBED_DIM}
            return sig, lambda texts, task_type: _embed_google(texts, task_type, sig["dim"])
        sig = {"provider": "ollama", "model": _OLLAMA_EMBED_MODEL, "dim": _OLLAMA_EMBED_DIM}
        return sig, lambda texts, _task_type: _embed_ollama(texts, sig["dim"])
    sig = {"provider": "google", "model": _GOOGLE_EMBED_MODEL, "dim": _GOOGLE_EMBED_DIM}
    return sig, lambda texts, task_type: _embed_google(texts, task_type, sig["dim"])


def _embed(texts: list[str], task_type: str, retries: int = 3) -> tuple[list[list[float]], dict[str, Any]]:
    sig, runner = _resolve_backend()
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        chunk = texts[i : i + _BATCH]
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                out.extend(runner(chunk, task_type))
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < retries - 1:
                    time.sleep(1.0 * (attempt + 1))
        else:
            raise RuntimeError(f"임베딩 실패(batch {i}, provider={sig['provider']}): {last_exc}")
    return out, sig


def embed_documents(texts: list[str]) -> list[list[float]]:
    """코퍼스(근거 자료) 임베딩 — 오프라인 빌드라 재시도 넉넉히."""
    vectors, _sig = _embed(list(texts), "RETRIEVAL_DOCUMENT", retries=3)
    return vectors


def embed_query(text: str) -> list[float]:
    """고객 질의/대화 임베딩 (단건) — 핫패스라 빠르게 실패해 랜덤 폴백으로 degrade."""
    vectors, _sig = _embed([text], "RETRIEVAL_QUERY", retries=1)
    return vectors[0]


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
        if not vec or len(vec) != qdim:
            continue
        dot = sum(x * y for x, y in zip(query, vec))
        scored.append((cid, dot / (qn * _norm(vec))))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]
