from __future__ import annotations

import os
from pathlib import Path
from typing import Any

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


def generate_text(
    prompt: str,
    *,
    model: str | None = None,
    system_instruction: str | None = None,
    timeout_seconds: float | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, int]]:
    client = build_client(timeout_seconds=timeout_seconds)
    config: dict[str, Any] = {}
    if max_output_tokens:
        config["max_output_tokens"] = max_output_tokens
    if response_mime_type:
        config["response_mime_type"] = response_mime_type
    if system_instruction:
        config["system_instruction"] = system_instruction
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
