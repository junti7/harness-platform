#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from edu_coach_simulation_runner import (
    REPORT_DIR,
    _display_path,
    _gold_set_candidates,
    _load_backend_main,
    evaluate_answer,
    load_gold_set,
    load_policy_registry,
)


def _normalize_gold(label: str) -> str:
    value = str(label or "").strip()
    if value == "pass":
        return "clear"
    if value in {"needs_work", "block"}:
        return value
    return "unknown"


def _weighted_agreement(gold: str, predicted: str) -> float:
    if gold == predicted:
        return 1.0
    if {gold, predicted} <= {"needs_work", "block"}:
        return 0.5
    return 0.0


def _cohen_kappa(confusion: dict[tuple[str, str], int], labels: list[str]) -> float:
    total = sum(confusion.values())
    if total <= 0:
        return 0.0
    observed = sum(confusion.get((label, label), 0) for label in labels) / total
    gold_counts = Counter()
    predicted_counts = Counter()
    for (gold, predicted), count in confusion.items():
        gold_counts[gold] += count
        predicted_counts[predicted] += count
    expected = sum((gold_counts[label] / total) * (predicted_counts[label] / total) for label in labels)
    if expected >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def run_calibration(*, report_dir: Path = REPORT_DIR, llm_judge_enabled: bool = False) -> dict[str, Any]:
    backend = _load_backend_main()
    registry = load_policy_registry()
    rows = _gold_set_candidates(load_gold_set())
    records: list[dict[str, Any]] = []
    labels = ["clear", "needs_work", "block"]
    confusion: dict[tuple[str, str], int] = Counter()
    exact_matches = 0
    weighted_sum = 0.0
    false_negatives: list[dict[str, Any]] = []
    false_positives: list[dict[str, Any]] = []
    by_intent: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        gold = _normalize_gold(str(row.get("expected_label") or ""))
        result = evaluate_answer(
            backend=backend,
            registry=registry,
            question=str(row.get("question") or ""),
            answer=str(row.get("answer") or ""),
            concept_body=str(row.get("concept_body") or ""),
            intent_labels=[str(label) for label in row.get("intent_labels", [])],
            llm_judge_enabled=llm_judge_enabled,
        )
        predicted = str(result.get("verdict") or "unknown")
        confusion[(gold, predicted)] += 1
        exact = gold == predicted
        exact_matches += 1 if exact else 0
        weighted = _weighted_agreement(gold, predicted)
        weighted_sum += weighted
        record = {
            "id": row.get("candidate_id"),
            "case_id": row.get("case_id"),
            "gold": gold,
            "predicted": predicted,
            "exact_match": exact,
            "weighted_agreement": weighted,
            "intent_labels": row.get("intent_labels") or [],
            "issues": result.get("issues") or [],
            "issue_severity": result.get("issue_severity") or {},
        }
        records.append(record)
        if gold in {"needs_work", "block"} and predicted == "clear":
            false_negatives.append(record)
        if gold == "clear" and predicted != "clear":
            false_positives.append(record)
        for intent in record["intent_labels"]:
            by_intent[str(intent)][f"{gold}->{predicted}"] += 1

    total = len(records)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = report_dir / f"judge_calibration_{run_id}.jsonl"
    output_json = report_dir / f"judge_calibration_{run_id}.json"
    output_md = report_dir / f"judge_calibration_{run_id}.md"

    with output_jsonl.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    exact_accuracy = exact_matches / max(1, total)
    weighted_accuracy = weighted_sum / max(1, total)
    kappa = _cohen_kappa(confusion, labels)
    critical_false_negative_count = sum(1 for item in false_negatives if item["gold"] == "block")
    summary = {
        "ok": True,
        "run_id": run_id,
        "llm_judge_enabled": llm_judge_enabled,
        "record_count": total,
        "exact_accuracy": round(exact_accuracy, 4),
        "weighted_accuracy": round(weighted_accuracy, 4),
        "cohen_kappa": round(kappa, 4),
        "critical_false_negative_count": critical_false_negative_count,
        "false_negative_count": len(false_negatives),
        "false_positive_count": len(false_positives),
        "pass_criteria": {
            "cohen_kappa_min": 0.70,
            "critical_false_negative_count": 0,
            "false_negative_count": 0,
        },
        "pass": kappa >= 0.70 and critical_false_negative_count == 0 and len(false_negatives) == 0,
        "confusion_matrix": {f"{gold}->{predicted}": count for (gold, predicted), count in sorted(confusion.items())},
        "by_intent": {intent: dict(counts) for intent, counts in sorted(by_intent.items())},
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "records_path": _display_path(output_jsonl),
        "summary_path": _display_path(output_json),
        "report_path": _display_path(output_md),
    }
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(_render_report(summary), encoding="utf-8")
    return summary


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# EDU Coach Judge Calibration",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- llm_judge_enabled: `{summary['llm_judge_enabled']}`",
        f"- record_count: `{summary['record_count']}`",
        f"- exact_accuracy: `{summary['exact_accuracy']}`",
        f"- weighted_accuracy: `{summary['weighted_accuracy']}`",
        f"- cohen_kappa: `{summary['cohen_kappa']}`",
        f"- critical_false_negative_count: `{summary['critical_false_negative_count']}`",
        f"- false_negative_count: `{summary['false_negative_count']}`",
        f"- false_positive_count: `{summary['false_positive_count']}`",
        f"- pass: `{summary['pass']}`",
        "",
        "## Confusion Matrix",
        "",
    ]
    for key, value in summary.get("confusion_matrix", {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## False Negatives", ""])
    false_negatives = summary.get("false_negatives") or []
    if not false_negatives:
        lines.append("- none")
    else:
        for item in false_negatives:
            lines.append(f"- `{item['id']}` gold={item['gold']} predicted={item['predicted']} issues={item['issues']}")
    lines.extend(["", "## False Positives", ""])
    false_positives = summary.get("false_positives") or []
    if not false_positives:
        lines.append("- none")
    else:
        for item in false_positives:
            lines.append(f"- `{item['id']}` gold={item['gold']} predicted={item['predicted']} issues={item['issues']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure EDU coach judge agreement against gold-set labels.")
    parser.add_argument("--llm-judge", action="store_true", help="enable opt-in strict-schema LLM judge")
    args = parser.parse_args()
    summary = run_calibration(llm_judge_enabled=bool(args.llm_judge))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
