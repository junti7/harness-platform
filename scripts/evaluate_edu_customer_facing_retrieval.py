#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.score_edu_grounded_simulations import DEFAULT_INPUT, SimulationCase, parse_simulation_markdown

TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")
STOPWORDS = {
    "이번", "기준", "지금", "정말", "그냥", "조금", "아주", "같이", "먼저", "이유", "내용", "자료",
    "연구", "기사", "서비스", "고객", "오늘", "내일", "정리", "설명", "사용", "대한", "에서", "으로",
    "하는", "하고", "하면", "같은", "있는", "있는지", "입니다", "있습니다", "합니다", "하세요", "있어요",
}


def _load_backend_main():
    module_name = "harness_backend_main_eval"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = ROOT / "harness-os" / "backend" / "main.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _keywords(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if token.lower() not in STOPWORDS
    }


def _segment_for_case(case: SimulationCase) -> str:
    title = case.title.lower()
    return "worker" if "직장인" in title else "parent"


def _query_for_case(case: SimulationCase, max_turns: int = 4) -> str:
    customer_turns = [turn.text for turn in case.turns if turn.speaker == "고객"]
    return " ".join(customer_turns[:max_turns]).strip()


def _item_signature(item: dict[str, Any]) -> set[str]:
    return _keywords(" ".join(str(item.get(key) or "") for key in ("title", "source", "cite", "body", "excerpt")))


def _match_ratio(expected: dict[str, Any], actual: dict[str, Any]) -> float:
    left = _item_signature(expected)
    right = _item_signature(actual)
    if not left or not right:
        return 0.0
    inter = len(left & right)
    denom = max(1, len(left))
    return inter / denom


def _expected_items(case: SimulationCase) -> list[dict[str, Any]]:
    return [
        {
            "title": item.title,
            "source": item.source_label,
            "excerpt": item.excerpt,
        }
        for item in case.evidence_items
    ]


def evaluate_case(case: SimulationCase, backend_module: Any, k: int, db_ready: bool) -> dict[str, Any]:
    query = _query_for_case(case)
    segment = _segment_for_case(case)
    bundle = backend_module._edu_db_customer_facing_bundle(query, segment=segment, k=k)
    if not bundle:
        return {
            "title": case.title,
            "query": query,
            "segment": segment,
            "ok": False,
            "error": "db_customer_facing_bundle_unavailable" if db_ready else "database_url_missing",
        }
    actual_items = bundle.get("items") or []
    expected = _expected_items(case)
    matched_expected = 0
    best_matches: list[dict[str, Any]] = []
    source_hits = 0
    title_hits = 0

    for item in expected:
        best_score = 0.0
        best_idx = None
        for idx, actual in enumerate(actual_items):
            score = _match_ratio(item, actual)
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_score >= 0.2:
            matched_expected += 1
        if best_idx is not None:
            actual = actual_items[best_idx]
            source_hit = item["source"].lower() in str(actual.get("source") or "").lower()
            title_overlap = bool(_keywords(item["title"]) & _keywords(str(actual.get("title") or actual.get("cite") or "")))
            source_hits += 1 if source_hit else 0
            title_hits += 1 if title_overlap else 0
            best_matches.append(
                {
                    "expected_title": item["title"],
                    "expected_source": item["source"],
                    "best_score": round(best_score, 3),
                    "actual_source": actual.get("source"),
                    "actual_title": actual.get("title") or actual.get("cite"),
                    "source_hit": source_hit,
                    "title_overlap": title_overlap,
                }
            )

    expected_hit_ratio = matched_expected / max(1, len(expected))
    source_alignment = source_hits / max(1, len(expected))
    title_alignment = title_hits / max(1, len(expected))
    total_score = round(expected_hit_ratio * 60 + source_alignment * 20 + title_alignment * 20, 2)
    verdict = "clear" if total_score >= 70 else "needs_work" if total_score >= 45 else "weak"
    return {
        "title": case.title,
        "query": query,
        "segment": segment,
        "ok": True,
        "score": total_score,
        "verdict": verdict,
        "metrics": {
            "expected_item_count": len(expected),
            "retrieved_item_count": len(actual_items),
            "expected_hit_ratio": round(expected_hit_ratio, 3),
            "source_alignment": round(source_alignment, 3),
            "title_alignment": round(title_alignment, 3),
        },
        "matches": best_matches,
    }


def evaluate_cases(cases: list[SimulationCase], k: int = 4) -> dict[str, Any]:
    backend_module = _load_backend_main()
    db_ready = bool(os.getenv("DATABASE_URL", "").strip())
    results = [evaluate_case(case, backend_module, k=k, db_ready=db_ready) for case in cases]
    good = [item for item in results if item.get("ok")]
    scores = [item["score"] for item in good]
    return {
        "summary": {
            "case_count": len(results),
            "database_url_present": db_ready,
            "ok_count": len(good),
            "error_count": len(results) - len(good),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "clear_count": sum(1 for item in good if item["verdict"] == "clear"),
            "needs_work_count": sum(1 for item in good if item["verdict"] == "needs_work"),
            "weak_count": sum(1 for item in good if item["verdict"] == "weak"),
        },
        "results": results,
    }


def render_markdown(report: dict[str, Any], source_path: Path) -> str:
    summary = report["summary"]
    lines = [
        "# Edu Customer-Facing Retrieval Evaluation",
        "",
        f"- source: `{source_path}`",
        f"- case_count: `{summary['case_count']}`",
        f"- database_url_present: `{summary['database_url_present']}`",
        f"- ok_count: `{summary['ok_count']}`",
        f"- error_count: `{summary['error_count']}`",
        f"- average_score: `{summary['average_score']}`",
        f"- clear_count: `{summary['clear_count']}`",
        f"- needs_work_count: `{summary['needs_work_count']}`",
        f"- weak_count: `{summary['weak_count']}`",
        "",
    ]
    for item in report["results"]:
        lines.append(f"## {item['title']}")
        lines.append("")
        if not item.get("ok"):
            lines.append(f"- error: `{item['error']}`")
            lines.append("")
            continue
        lines.extend(
            [
                f"- score: `{item['score']}`",
                f"- verdict: `{item['verdict']}`",
                f"- query: `{item['query']}`",
                f"- expected_hit_ratio: `{item['metrics']['expected_hit_ratio']}`",
                f"- source_alignment: `{item['metrics']['source_alignment']}`",
                f"- title_alignment: `{item['metrics']['title_alignment']}`",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate live customer-facing retrieval against simulation bundles.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    markdown = args.input.read_text(encoding="utf-8")
    cases = parse_simulation_markdown(markdown)
    report = evaluate_cases(cases, k=args.k)
    if args.json_out:
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.write_text(render_markdown(report, args.input), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
