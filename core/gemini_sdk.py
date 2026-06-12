from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _normalize_gemini_env() -> None:
    google_key = (os.getenv("GOOGLE_API_KEY") or "").strip()
    gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if google_key:
        os.environ["GOOGLE_API_KEY"] = google_key
        os.environ.pop("GEMINI_API_KEY", None)
        return
    if gemini_key:
        os.environ["GOOGLE_API_KEY"] = gemini_key
        os.environ.pop("GEMINI_API_KEY", None)


def gemini_api_key() -> str:
    _normalize_gemini_env()
    return (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or ""
    ).strip()


def gemini_model_name(default: str = "gemini-2.5-flash") -> str:
    return (os.getenv("GEMINI_MODEL") or default).strip()


def build_client(timeout_seconds: float | None = None) -> genai.Client:
    kwargs: dict[str, Any] = {"api_key": gemini_api_key()}
    return genai.Client(**kwargs)


def _local_fallback_enabled() -> bool:
    return os.getenv("GEMINI_LOCAL_FALLBACK_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


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


def _local_fallback_model() -> str:
    return (
        os.getenv("GEMINI_LOCAL_FALLBACK_MODEL")
        or os.getenv("OLLAMA_CHAT_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or "gemma4:latest"
    ).strip()


def _generate_text_via_ollama(
    prompt: str,
    *,
    system_instruction: str | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
) -> tuple[str, dict[str, int]]:
    model = _local_fallback_model()
    user_prompt = prompt
    if response_mime_type == "application/json":
        user_prompt = f"{prompt}\n\n반드시 유효한 JSON만 응답하세요."
    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": user_prompt})

    last_exc: Exception | None = None
    for host in _ollama_hosts():
        if not _probe_ollama(host):
            continue
        try:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": float(os.getenv("OLLAMA_FALLBACK_TEMPERATURE", "0.1")),
                    "top_p": float(os.getenv("OLLAMA_FALLBACK_TOP_P", "0.9")),
                    "num_ctx": int(os.getenv("OLLAMA_FALLBACK_NUM_CTX", "8192")),
                },
            }
            if max_output_tokens:
                payload["options"]["num_predict"] = int(max_output_tokens)
            if response_mime_type == "application/json":
                payload["format"] = "json"
            response = httpx.post(f"{host}/api/chat", json=payload, timeout=60)
            response.raise_for_status()
            text = (((response.json() or {}).get("message") or {}).get("content") or "").strip()
            if text:
                return text, {"prompt_token_count": 0, "candidates_token_count": 0}
            raise RuntimeError("empty_ollama_response")
        except Exception as exc:
            last_exc = exc
            continue
    raise RuntimeError(f"ollama_fallback_unavailable: {last_exc}")


def generate_text(
    prompt: str,
    *,
    model: str | None = None,
    system_instruction: str | None = None,
    timeout_seconds: float | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
    thinking_budget: int | None = None,
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, int]]:
    config: dict[str, Any] = {}
    if max_output_tokens:
        config["max_output_tokens"] = max_output_tokens
    if response_mime_type:
        config["response_mime_type"] = response_mime_type
    if system_instruction:
        config["system_instruction"] = system_instruction
    if thinking_budget is not None:
        # gemini-2.5는 thinking이 기본 ON이라 max_output_tokens 예산을 사고에 소진해
        # 구조화 출력을 절단할 수 있다. budget=0이면 thinking 비활성(2.5-flash 지원).
        try:
            from google.genai import types as _genai_types

            config["thinking_config"] = _genai_types.ThinkingConfig(thinking_budget=thinking_budget)
        except Exception:
            config["thinking_config"] = {"thinking_budget": thinking_budget}
    try:
        client = build_client(timeout_seconds=timeout_seconds)
        response = client.models.generate_content(
            model=model or gemini_model_name(),
            contents=prompt,
            config=config or None,
        )
        if meta is not None:
            try:
                finish_reason = None
                if response.candidates and len(response.candidates) > 0:
                    finish_reason = response.candidates[0].finish_reason
                meta["finish_reason"] = str(finish_reason) if finish_reason else "UNKNOWN"
                meta["is_truncated"] = finish_reason is not None and "MAX_TOKENS" in str(finish_reason).upper()
                meta["provider"] = "google"
                meta["model"] = model or gemini_model_name()
            except Exception as e:
                meta["is_truncated"] = False
                meta["error"] = str(e)

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        candidate_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        text = (getattr(response, "text", None) or "").strip()
        return text, {
            "prompt_token_count": prompt_tokens,
            "candidates_token_count": candidate_tokens,
        }
    except Exception as exc:
        if not _local_fallback_enabled():
            raise
        text, usage = _generate_text_via_ollama(
            prompt,
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
        )
        if meta is not None:
            meta["provider"] = "ollama"
            meta["model"] = _local_fallback_model()
            meta["fallback_reason"] = type(exc).__name__
            meta["is_truncated"] = False
        return text, usage
