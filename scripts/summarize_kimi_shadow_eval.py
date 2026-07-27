#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "runtime" / "kimi_shadow_eval.jsonl"


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return int(statistics.quantiles(values, n=20, method="inclusive")[18])


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    input_per_mtok = float(os.getenv("KIMI_COST_INPUT_PER_MTOK_USD", "3.0"))
    output_per_mtok = float(os.getenv("KIMI_COST_OUTPUT_PER_MTOK_USD", "15.0"))
    by_source: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "ok": 0, "json_total": 0, "json_valid": 0})
    latency_ms = []
    prompt_tokens = 0
    output_tokens = 0
    errors: Counter[str] = Counter()

    for record in records:
        source = str(record.get("source") or "unknown")
        by_source[source]["total"] += 1
        if record.get("ok"):
            by_source[source]["ok"] += 1
        if "json_valid" in record:
            by_source[source]["json_total"] += 1
            if record.get("json_valid"):
                by_source[source]["json_valid"] += 1
        if isinstance(record.get("latency_ms"), int):
            latency_ms.append(int(record["latency_ms"]))
        prompt_tokens += int(record.get("prompt_token_count") or 0)
        output_tokens += int(record.get("candidates_token_count") or 0)
        if not record.get("ok"):
            errors[str(record.get("error_type") or "unknown")] += 1

    estimated_cost = (prompt_tokens / 1_000_000 * input_per_mtok) + (output_tokens / 1_000_000 * output_per_mtok)
    source_summary = {}
    for source, payload in by_source.items():
        total = payload["total"]
        json_total = payload["json_total"]
        source_summary[source] = {
            **payload,
            "ok_rate": round(payload["ok"] / total, 4) if total else 0.0,
            "json_valid_rate": round(payload["json_valid"] / json_total, 4) if json_total else None,
        }

    return {
        "total": len(records),
        "ok": sum(1 for record in records if record.get("ok")),
        "ok_rate": round(sum(1 for record in records if record.get("ok")) / len(records), 4) if records else 0.0,
        "latency_ms_avg": int(sum(latency_ms) / len(latency_ms)) if latency_ms else None,
        "latency_ms_p95": _p95(latency_ms),
        "prompt_tokens": prompt_tokens,
        "candidates_tokens": output_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
        "by_source": source_summary,
        "errors": dict(errors.most_common()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Kimi K3 shadow evaluation JSONL.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    print(json.dumps(summarize(_load_records(args.input)), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
