import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = Path("runtime/openclaw_route_audit.jsonl")
DEFAULT_OUTPUT_DIR = Path("docs/reviews/openclaw_route_audit")


def _load_records(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if limit:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _counter_lines(counter: Counter, empty: str = "- none") -> list[str]:
    if not counter:
        return [empty]
    return [f"- {key}: {value}" for key, value in counter.most_common()]


def _blocked_examples(records: list[dict[str, Any]], limit: int = 5) -> list[str]:
    examples = []
    for record in reversed(records):
        if not record.get("blocked"):
            continue
        message = (record.get("message") or "").replace("\n", " ")
        reason = (record.get("reason") or "").splitlines()[0]
        examples.append(
            f"- `{record.get('route')}` | risk={record.get('risk_level')} | message=`{message}` | reason={reason}"
        )
        if len(examples) >= limit:
            break
    return examples or ["- none"]


def _failure_memory_candidates(records: list[dict[str, Any]]) -> list[str]:
    grouped: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if not record.get("blocked"):
            continue
        route = record.get("route") or "unknown"
        flags = tuple(record.get("flags") or [])
        grouped[(route, flags)].append(record)

    candidates = []
    for (route, flags), items in sorted(grouped.items(), key=lambda kv: len(kv[1]), reverse=True):
        if len(items) < 2:
            continue
        sample = items[-1]
        terms = sample.get("context_sensitive_terms") or sample.get("current_high_terms") or []
        candidates.append(
            "\n".join(
                [
                    f"### Candidate: {route} / {', '.join(flags) or 'no_flags'}",
                    f"- count: {len(items)}",
                    f"- sample_input: {sample.get('message')}",
                    f"- observed_behavior: blocked by `{route}`",
                    "- expected_behavior: keep blocked unless a precise target, destination, and required gate are supplied",
                    "- root_cause: ambiguous or high-risk Slack instruction needs explicit preflight/human gate",
                    f"- trigger_terms: {terms}",
                ]
            )
        )
    return candidates or ["- No repeated blocked pattern reached the promotion threshold."]


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def build_summary(records: list[dict[str, Any]], generated_for: str | None = None, label: str = "route-audit") -> str:
    route_counts = Counter(record.get("route") or "unknown" for record in records)
    risk_counts = Counter(record.get("risk_level") or "unknown" for record in records)
    blocked_counts = Counter(record.get("route") or "unknown" for record in records if record.get("blocked"))
    model_counts = Counter(record.get("model") or "none" for record in records)
    flag_counts = Counter(flag for record in records for flag in (record.get("flags") or []))

    total = len(records)
    blocked_total = sum(1 for record in records if record.get("blocked"))
    blocked_rate = (blocked_total / total) if total else 0.0
    generated_for = generated_for or date.today().isoformat()

    lines = [
        f"# OpenClaw Route Audit Summary ({label}) - {generated_for}",
        "",
        "## Summary",
        "",
        f"- records_reviewed: {total}",
        f"- blocked_records: {blocked_total}",
        f"- blocked_rate: {blocked_rate:.1%}",
        "",
        "## Route Counts",
        "",
        *_counter_lines(route_counts),
        "",
        "## Risk Counts",
        "",
        *_counter_lines(risk_counts),
        "",
        "## Blocked Routes",
        "",
        *_counter_lines(blocked_counts),
        "",
        "## Model Usage",
        "",
        *_counter_lines(model_counts),
        "",
        "## Risk Flags",
        "",
        *_counter_lines(flag_counts),
        "",
        "## Recent Blocked Examples",
        "",
        *_blocked_examples(records),
        "",
        "## Failure Memory Candidates",
        "",
        *_failure_memory_candidates(records),
        "",
        "## Operator Note",
        "",
        "Do not automatically append these candidates to `docs/openclaw/OPENCLAW_FAILURE_MEMORY.md`.",
        "Promote only after human review, because rule-based tripwires are not proof of general correctness.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize OpenClaw route audit JSONL into an operating memo.")
    parser.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output-name")
    parser.add_argument("--archive-label", default="route-audit")
    parser.add_argument("--to-notion", action="store_true")
    args = parser.parse_args()

    records = _load_records(args.audit_path, limit=args.limit)
    summary = build_summary(records, generated_for=args.date, label=args.archive_label)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_name or f"openclaw_route_audit_{args.date}.md"
    output_path = args.output_dir / output_name
    output_path.write_text(summary, encoding="utf-8")

    result: dict[str, Any] = {
        "records_reviewed": len(records),
        "output_path": str(output_path),
        "notion_url": None,
    }

    if args.to_notion:
        sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.notion_archive_entry import create_archive_page

        page = create_archive_page(
            title=f"OpenClaw Route Audit Summary ({args.archive_label}) - {args.date}",
            body_markdown=summary,
            artifact_type="failure_case",
            teams=["Engineering", "QA"],
            project="OpenClaw Integration",
            project_status="active",
            outcome="hold",
            source_channel="automation",
            event_date=args.date,
            canonical_key=f"openclaw-{_slug(args.archive_label)}-{args.date}",
            summary=f"OpenClaw route audit summary ({args.archive_label}) for {args.date}.",
            lessons_learned="Review blocked route patterns before promoting any rule to failure memory.",
            failure_patterns=["openclaw-route-audit", "risk-intent-routing"],
            tags=["openclaw", "route-audit", args.archive_label, "failure-memory-candidate"],
        )
        result["notion_url"] = page.get("url")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
