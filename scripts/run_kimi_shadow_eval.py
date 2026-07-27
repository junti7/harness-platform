#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.kimi_shadow import run_kimi_shadow_eval  # noqa: E402


DEFAULT_PROMPTS = [
    {
        "id": "json_fact_extract",
        "response_mime_type": "application/json",
        "prompt": (
            "Return JSON only with keys costs, performance, market_size, key_players. "
            "Article: Robotics startup Factory Arm raised $42M in 2026, claims cycle time improved 18%, "
            "and sells to electronics manufacturers."
        ),
    },
    {
        "id": "korean_reader_summary",
        "prompt": (
            "다음 내용을 비전문가 대표가 30초 안에 판단할 수 있게 한국어로 요약하라. "
            "Kimi K3 is a 2.8T-parameter MoE model with long-context coding claims, but local deployment "
            "requires accelerator-scale infrastructure."
        ),
    },
    {
        "id": "code_review_note",
        "prompt": (
            "Review this change plan for risks: add a disabled-by-default shadow LLM evaluator that records "
            "hashes, latency, token counts, JSON validity, and never changes production output."
        ),
    },
]


def _load_prompts(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return DEFAULT_PROMPTS
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".json":
        payload = json.loads(text)
        if isinstance(payload, list):
            return payload
        return payload.get("prompts", [])
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _ollama_chat(host: str, model: str, prompt: str, timeout: float) -> tuple[str, int]:
    started = time.monotonic()
    response = httpx.post(
        f"{host.rstrip('/')}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    text = (((response.json() or {}).get("message") or {}).get("content") or "").strip()
    return text, int((time.monotonic() - started) * 1000)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic Kimi K3 shadow evaluation against local Ollama baseline.")
    parser.add_argument("--input", type=Path, help="JSON or JSONL prompts. Defaults to built-in synthetic prompts.")
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "kimi_shadow_eval.jsonl")
    parser.add_argument("--ollama-host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"))
    parser.add_argument("--ollama-timeout", type=float, default=float(os.getenv("OLLAMA_CHAT_TIMEOUT", "90")))
    args = parser.parse_args()

    prompts = _load_prompts(args.input)
    if not prompts:
        print("no prompts")
        return 1

    ok_count = 0
    for item in prompts:
        prompt = str(item.get("prompt") or "").strip()
        if not prompt:
            continue
        prompt_id = str(item.get("id") or f"prompt_{ok_count + 1}")
        baseline_text = ""
        baseline_latency_ms = None
        try:
            baseline_text, baseline_latency_ms = _ollama_chat(
                args.ollama_host,
                args.ollama_model,
                prompt,
                args.ollama_timeout,
            )
        except Exception as exc:
            baseline_text = f"baseline_error:{type(exc).__name__}:{str(exc)[:200]}"

        record = run_kimi_shadow_eval(
            source="synthetic_benchmark",
            prompt=prompt,
            baseline_provider="ollama",
            baseline_model=args.ollama_model,
            baseline_response=baseline_text,
            response_mime_type=item.get("response_mime_type"),
            metadata={"prompt_id": prompt_id, "baseline_latency_ms": baseline_latency_ms},
            output_path=args.output,
        )
        ok_count += 1 if record.get("ok") else 0
        print(json.dumps({"prompt_id": prompt_id, "kimi_ok": record.get("ok"), "latency_ms": record.get("latency_ms")}, ensure_ascii=False))

    print(json.dumps({"prompts": len(prompts), "kimi_ok": ok_count, "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
