#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs" / "education"
REPORT_DIR = ROOT / "docs" / "reviews" / "edu_coach_simulations"
POLICY_PATH = CONFIG_DIR / "edu_coach_policy_registry.json"
SCENARIO_PATH = CONFIG_DIR / "edu_coach_scenarios.json"
GOLD_SET_PATH = REPORT_DIR / "gold_set_seed_2026-06-27.jsonl"


@dataclass(frozen=True)
class ScenarioCase:
    case_id: str
    twin_id: str
    intent_labels: list[str]
    concept_title: str
    concept_body: str
    question: str
    expected_good_answer: str
    known_bad_answers: list[str]


def _load_backend_main() -> Any:
    module_name = "harness_backend_main_for_edu_coach_simulation"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = ROOT / "harness-os" / "backend" / "main.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if spec.loader is None:
        raise RuntimeError(f"cannot load backend module: {path}")
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_policy_registry(path: Path = POLICY_PATH) -> dict[str, Any]:
    registry = _read_json(path)
    if not isinstance(registry.get("failure_taxonomy"), dict):
        raise ValueError("policy registry missing failure_taxonomy")
    if not isinstance(registry.get("policies"), list):
        raise ValueError("policy registry missing policies")
    return registry


def load_scenarios(path: Path = SCENARIO_PATH) -> list[ScenarioCase]:
    payload = _read_json(path)
    cases = []
    for item in payload.get("cases", []):
        cases.append(
            ScenarioCase(
                case_id=str(item["case_id"]),
                twin_id=str(item["twin_id"]),
                intent_labels=[str(label) for label in item.get("intent_labels", [])],
                concept_title=str(item.get("concept_title") or ""),
                concept_body=str(item.get("concept_body") or ""),
                question=str(item["question"]),
                expected_good_answer=str(item.get("expected_good_answer") or ""),
                known_bad_answers=[str(answer) for answer in item.get("known_bad_answers", [])],
            )
        )
    if not cases:
        raise ValueError("scenario registry has no cases")
    return cases


def load_gold_set(path: Path = GOLD_SET_PATH) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line_no"] = line_no
        rows.append(row)
    if not rows:
        raise ValueError("gold set has no rows")
    return rows


def _severity_for(issue: str, registry: dict[str, Any]) -> str:
    entry = registry.get("failure_taxonomy", {}).get(issue)
    if isinstance(entry, dict):
        severity = str(entry.get("severity") or "").strip()
        if severity in {"critical", "major", "minor"}:
            return severity
    return "major"


def _verdict_for(issues: list[str], registry: dict[str, Any]) -> str:
    if any(_severity_for(issue, registry) == "critical" for issue in issues):
        return "block"
    if issues:
        return "needs_work"
    return "clear"


def _policy_by_intent(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policies: dict[str, dict[str, Any]] = {}
    for policy in registry.get("policies", []):
        if isinstance(policy, dict) and policy.get("intent_class"):
            policies[str(policy["intent_class"])] = policy
    return policies


def _policy_contract_issues(answer: str, intents: list[str], registry: dict[str, Any]) -> list[str]:
    answer_text = str(answer or "")
    policies = _policy_by_intent(registry)
    issues: list[str] = []
    for intent in intents:
        policy = policies.get(intent)
        if not policy:
            continue
        must_not = policy.get("must_not_include_any")
        if isinstance(must_not, dict):
            for requirement, terms in must_not.items():
                if isinstance(terms, list) and any(str(term) and str(term) in answer_text for term in terms):
                    issues.append(f"policy_forbidden_{requirement}")
    return issues


def evaluate_answer(
    *,
    backend: Any,
    registry: dict[str, Any],
    question: str,
    answer: str,
    concept_body: str,
    intent_labels: list[str],
) -> dict[str, Any]:
    red_team_issues = backend._edu_vp_safety_coach_red_team(
        question=question,
        answer=answer,
        concept_body=concept_body,
    )
    contract_issues = _policy_contract_issues(answer, intent_labels, registry)
    issues: list[str] = []
    for issue in [*red_team_issues, *contract_issues]:
        if issue not in issues:
            issues.append(issue)
    return {
        "verdict": _verdict_for(issues, registry),
        "issues": issues,
        "issue_severity": {issue: _severity_for(issue, registry) for issue in issues},
    }


def _current_fallback_candidate(backend: Any, case: ScenarioCase) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": f"{case.case_id}:current_fallback",
            "candidate_source": "current_fallback",
            "expected_label": "pass",
            "answer": backend._edu_vp_safety_coach_fallback(case.concept_title, case.question),
        }
    ]


def _scenario_gold_candidates(case: ScenarioCase) -> list[dict[str, Any]]:
    candidates = [
        {
            "candidate_id": f"{case.case_id}:expected_good",
            "candidate_source": "scenario_expected_good",
            "expected_label": "pass",
            "answer": case.expected_good_answer,
        }
    ]
    for idx, answer in enumerate(case.known_bad_answers, start=1):
        candidates.append(
            {
                "candidate_id": f"{case.case_id}:known_bad_{idx}",
                "candidate_source": "scenario_known_bad",
                "expected_label": "fail",
                "answer": answer,
            }
        )
    return candidates


def _gold_set_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for row in rows:
        candidates.append(
            {
                "case_id": str(row.get("case_id") or row.get("id") or ""),
                "candidate_id": str(row.get("id") or ""),
                "candidate_source": "gold_set_seed",
                "expected_label": str(row.get("label") or ""),
                "question": str(row.get("question") or ""),
                "answer": str(row.get("answer") or ""),
                "intent_labels": [str(label) for label in row.get("intent_labels", [])],
                "concept_title": "",
                "concept_body": "",
            }
        )
    return candidates


def run_simulation(
    *,
    candidate_source: str = "current-fallback",
    limit: int | None = None,
    report_dir: Path = REPORT_DIR,
) -> dict[str, Any]:
    backend = _load_backend_main()
    registry = load_policy_registry()
    scenarios = load_scenarios()
    report_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = report_dir / f"run_{run_id}_{candidate_source.replace('-', '_')}.jsonl"

    records: list[dict[str, Any]] = []
    if candidate_source == "gold-set":
        raw_candidates = _gold_set_candidates(load_gold_set())
        for item in raw_candidates[:limit]:
            result = evaluate_answer(
                backend=backend,
                registry=registry,
                question=item["question"],
                answer=item["answer"],
                concept_body=item.get("concept_body", ""),
                intent_labels=item.get("intent_labels", []),
            )
            records.append({**item, **result})
    else:
        for case in scenarios[:limit]:
            if candidate_source == "current-fallback":
                candidates = _current_fallback_candidate(backend, case)
            elif candidate_source == "scenario-gold":
                candidates = _scenario_gold_candidates(case)
            else:
                raise ValueError("candidate_source must be current-fallback, scenario-gold, or gold-set")
            for candidate in candidates:
                result = evaluate_answer(
                    backend=backend,
                    registry=registry,
                    question=case.question,
                    answer=candidate["answer"],
                    concept_body=case.concept_body,
                    intent_labels=case.intent_labels,
                )
                records.append(
                    {
                        "case_id": case.case_id,
                        "twin_id": case.twin_id,
                        "intent_labels": case.intent_labels,
                        "concept_title": case.concept_title,
                        "question": case.question,
                        **candidate,
                        **result,
                    }
                )

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    verdict_counts = Counter(record["verdict"] for record in records)
    issue_counts: Counter[str] = Counter()
    intent_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        for issue in record.get("issues", []):
            issue_counts[str(issue)] += 1
        for intent in record.get("intent_labels", []):
            intent_counts[str(intent)][record["verdict"]] += 1

    summary = {
        "ok": True,
        "run_id": run_id,
        "candidate_source": candidate_source,
        "record_count": len(records),
        "output_path": _display_path(output_path),
        "verdict_counts": dict(verdict_counts),
        "top_issues": issue_counts.most_common(20),
        "intent_verdict_counts": {intent: dict(counts) for intent, counts in sorted(intent_counts.items())},
    }
    latest_json = report_dir / "latest.json"
    latest_md = report_dir / "latest.md"
    latest_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest_md.write_text(_render_markdown_summary(summary), encoding="utf-8")
    summary["latest_json"] = _display_path(latest_json)
    summary["latest_md"] = _display_path(latest_md)
    return summary


def _render_markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# EDU Coach Simulation Latest",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- candidate_source: `{summary['candidate_source']}`",
        f"- record_count: `{summary['record_count']}`",
        f"- output: `{summary['output_path']}`",
        "",
        "## Verdict Counts",
        "",
    ]
    for verdict, count in sorted(summary.get("verdict_counts", {}).items()):
        lines.append(f"- `{verdict}`: {count}")
    lines.extend(["", "## Top Issues", ""])
    top_issues = summary.get("top_issues") or []
    if not top_issues:
        lines.append("- none")
    else:
        for issue, count in top_issues:
            lines.append(f"- `{issue}`: {count}")
    lines.extend(["", "## Intent Verdict Counts", ""])
    for intent, counts in sorted(summary.get("intent_verdict_counts", {}).items()):
        count_text = ", ".join(f"{verdict}={count}" for verdict, count in sorted(counts.items()))
        lines.append(f"- `{intent}`: {count_text}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic EDU AI coach answer-quality simulations.")
    parser.add_argument(
        "--candidate-source",
        choices=["current-fallback", "scenario-gold", "gold-set"],
        default="current-fallback",
        help="which answer candidates to score",
    )
    parser.add_argument("--limit", type=int, default=None, help="optional number of scenario/gold rows to run")
    args = parser.parse_args()
    summary = run_simulation(candidate_source=args.candidate_source, limit=args.limit)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
