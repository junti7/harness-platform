from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "runtime" / "kimi_shadow_eval.jsonl"


def kimi_shadow_enabled() -> bool:
    return os.getenv("KIMI_SHADOW_EVAL_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def kimi_configured() -> bool:
    return bool(os.getenv("KIMI_API_KEY", "").strip())


def _capture_text_enabled() -> bool:
    return os.getenv("KIMI_SHADOW_CAPTURE_TEXT", "false").strip().lower() in {"1", "true", "yes"}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _approx_tokens(value: str) -> int:
    return max(1, len(value) // 4) if value else 0


def _output_path() -> Path:
    return Path(os.getenv("KIMI_SHADOW_OUTPUT_PATH", str(DEFAULT_OUTPUT_PATH))).expanduser()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _metadata_safe(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, (list, tuple)):
            safe[key] = [str(item)[:120] for item in value[:10]]
        else:
            safe[key] = str(value)[:500]
    return safe


def call_kimi(
    prompt: str,
    *,
    system_instruction: str | None = None,
    model: str | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
    timeout_seconds: float | None = None,
) -> tuple[str, dict[str, int]]:
    api_key = os.getenv("KIMI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("kimi_api_key_missing")

    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    body: dict[str, Any] = {
        "model": model or os.getenv("KIMI_SHADOW_MODEL", "k3-256k").strip(),
        "messages": messages,
        "temperature": float(os.getenv("KIMI_SHADOW_TEMPERATURE", "0.1")),
        "max_tokens": int(max_output_tokens or os.getenv("KIMI_SHADOW_MAX_OUTPUT_TOKENS", "1024")),
        "reasoning_effort": os.getenv("KIMI_SHADOW_REASONING_EFFORT", "high").strip(),
    }
    if response_mime_type == "application/json":
        body["response_format"] = {"type": "json_object"}

    base_url = os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1").rstrip("/")
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=float(timeout_seconds or os.getenv("KIMI_SHADOW_TIMEOUT", "60")),
    )
    response.raise_for_status()
    payload = response.json() or {}
    choices = payload.get("choices") or []
    text = ""
    if choices:
        text = (((choices[0] or {}).get("message") or {}).get("content") or "").strip()

    usage = payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or _approx_tokens(prompt))
    completion_tokens = int(usage.get("completion_tokens") or _approx_tokens(text))
    return text, {
        "prompt_token_count": prompt_tokens,
        "candidates_token_count": completion_tokens,
    }


def run_kimi_shadow_eval(
    *,
    source: str,
    prompt: str,
    baseline_provider: str,
    baseline_model: str,
    baseline_response: str | None = None,
    system_instruction: str | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
    metadata: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    record: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "provider": "kimi",
        "model": os.getenv("KIMI_SHADOW_MODEL", "k3-256k").strip(),
        "baseline_provider": baseline_provider,
        "baseline_model": baseline_model,
        "prompt_hash": _sha256_text(prompt),
        "prompt_chars": len(prompt),
        "baseline_response_hash": _sha256_text(baseline_response or ""),
        "baseline_response_chars": len(baseline_response or ""),
        "metadata": _metadata_safe(metadata),
        "ok": False,
    }
    try:
        text, usage = call_kimi(
            prompt,
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
        )
        record.update(
            {
                "ok": True,
                "response_hash": _sha256_text(text),
                "response_chars": len(text),
                "latency_ms": int((time.monotonic() - started) * 1000),
                "prompt_token_count": usage["prompt_token_count"],
                "candidates_token_count": usage["candidates_token_count"],
            }
        )
        if response_mime_type == "application/json":
            try:
                json.loads(text)
                record["json_valid"] = True
            except json.JSONDecodeError:
                record["json_valid"] = False
        if _capture_text_enabled():
            record["prompt"] = prompt
            record["baseline_response"] = baseline_response or ""
            record["response"] = text
    except Exception as exc:
        record.update(
            {
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
        )

    _append_jsonl(output_path or _output_path(), record)
    return record


def submit_kimi_shadow_eval(
    *,
    source: str,
    prompt: str,
    baseline_provider: str,
    baseline_model: str,
    baseline_response: str | None = None,
    system_instruction: str | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    if not kimi_shadow_enabled() or not kimi_configured():
        return False

    thread = threading.Thread(
        target=run_kimi_shadow_eval,
        kwargs={
            "source": source,
            "prompt": prompt,
            "baseline_provider": baseline_provider,
            "baseline_model": baseline_model,
            "baseline_response": baseline_response,
            "system_instruction": system_instruction,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": response_mime_type,
            "metadata": metadata,
        },
        daemon=True,
    )
    thread.start()
    return True
