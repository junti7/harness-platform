import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = Path("runtime/openclaw_route_audit.jsonl")
DEFAULT_OUTPUT_DIR = Path("docs/reviews/openclaw_route_audit")
_TOP_RISK_RE = re.compile(r"(top\s*risk|리스크|병목)", re.IGNORECASE)
_MAIL_RE = re.compile(r"(메일|gmail)", re.IGNORECASE)
_STATUS_RE = re.compile(r"(status|상태|현황|health|헬스|ops|파이프라인\s*어때)", re.IGNORECASE)


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


def _route_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if (record.get("kind") or "route") == "route"]


def _response_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("kind") == "response_metric"]


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


def _bucket_for_message(message: str) -> str | None:
    if _TOP_RISK_RE.search(message):
        return "top_risk"
    if _MAIL_RE.search(message):
        return "mail"
    if _STATUS_RE.search(message):
        return "status"
    return None


def _slice_by_change_date(records: list[dict[str, Any]], change_date: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not change_date:
        return records, []
    before: list[dict[str, Any]] = []
    after: list[dict[str, Any]] = []
    for record in records:
        ts = str(record.get("ts") or "")
        record_date = ts[:10] if len(ts) >= 10 else ""
        if record_date and record_date < change_date:
            before.append(record)
        elif record_date and record_date >= change_date:
            after.append(record)
    return before, after


def _record_date(record: dict[str, Any]) -> date | None:
    ts = str(record.get("ts") or "")
    if len(ts) < 10:
        return None
    try:
        return datetime.fromisoformat(ts[:19]).date()
    except ValueError:
        return None


def _window_average_response_chars(
    records: list[dict[str, Any]],
    *,
    end_date: date,
    days: int,
) -> float | None:
    start_date = end_date - timedelta(days=days - 1)
    values: list[int] = []
    for record in records:
        record_date = _record_date(record)
        if record_date is None or record.get("response_chars") is None:
            continue
        if start_date <= record_date <= end_date:
            values.append(int(record["response_chars"]))
    if not values:
        return None
    return sum(values) / len(values)


def _weekly_response_delta(records: list[dict[str, Any]], window_days: int = 7) -> tuple[float | None, float | None, float | None]:
    response_records = _response_records(records)
    dated_records = [record for record in response_records if _record_date(record) is not None]
    if not dated_records:
        return None, None, None

    latest_date = max(_record_date(record) for record in dated_records if _record_date(record) is not None)
    if latest_date is None:
        return None, None, None
    current_avg = _window_average_response_chars(response_records, end_date=latest_date, days=window_days)
    previous_end_date = latest_date - timedelta(days=window_days)
    previous_avg = _window_average_response_chars(response_records, end_date=previous_end_date, days=window_days)
    delta = None if current_avg is None or previous_avg is None else current_avg - previous_avg
    return current_avg, previous_avg, delta


def _route_class(route: str) -> str:
    if route.startswith("deterministic_"):
        return "deterministic"
    if route == "local_chat":
        return "local"
    if route == "economy_chat":
        return "economy"
    if route in {"premium_chat", "premium_tool_agent"}:
        return "premium"
    return "other"


def _target_query_lines(records: list[dict[str, Any]], change_date: str | None = None) -> list[str]:
    buckets = {
        "top_risk": "top risk / risk",
        "mail": "mail / gmail",
        "status": "status / ops",
    }
    before, after = _slice_by_change_date(records, change_date)
    lines: list[str] = []
    for bucket_key, label in buckets.items():
        matched = [r for r in records if _bucket_for_message(str(r.get("message") or "")) == bucket_key]
        if not matched:
            continue
        route_counts = Counter(str(r.get("route") or "unknown") for r in matched)
        class_counts = Counter(_route_class(str(r.get("route") or "")) for r in matched)
        premium = class_counts.get("premium", 0)
        lines.append(f"### {label}")
        lines.append(f"- total: {len(matched)}")
        lines.append(f"- deterministic/local/economy/premium: {class_counts.get('deterministic', 0)}/{class_counts.get('local', 0)}/{class_counts.get('economy', 0)}/{premium}")
        if len(matched):
            avoided = 1 - (premium / len(matched))
            lines.append(f"- premium_avoided_rate: {avoided:.1%}")
        if change_date:
            bucket_before = [r for r in before if _bucket_for_message(str(r.get('message') or '')) == bucket_key]
            bucket_after = [r for r in after if _bucket_for_message(str(r.get('message') or '')) == bucket_key]
            if bucket_before or bucket_after:
                before_premium = sum(1 for r in bucket_before if _route_class(str(r.get("route") or "")) == "premium")
                after_premium = sum(1 for r in bucket_after if _route_class(str(r.get("route") or "")) == "premium")
                lines.append(f"- before_{change_date}: total={len(bucket_before)}, premium={before_premium}")
                lines.append(f"- on_after_{change_date}: total={len(bucket_after)}, premium={after_premium}")
        lines.extend(f"- route::{route} = {count}" for route, count in route_counts.most_common())
        lines.append("")
    return lines or ["- no target query matches"]


def _response_length_lines(records: list[dict[str, Any]], change_date: str | None = None) -> list[str]:
    response_records = _response_records(records)
    if not response_records:
        return ["- no response length metrics yet"]

    route_avg: dict[str, float] = {}
    grouped: dict[str, list[int]] = defaultdict(list)
    for record in response_records:
        if record.get("response_chars") is None:
            continue
        grouped[str(record.get("route") or "unknown")].append(int(record["response_chars"]))
    for route, values in grouped.items():
        route_avg[route] = sum(values) / len(values)

    lines = [f"- overall_avg_response_chars: {sum(int(r.get('response_chars') or 0) for r in response_records) / len(response_records):.1f}"]
    lines.extend(f"- route::{route} avg_chars={avg:.1f}" for route, avg in sorted(route_avg.items(), key=lambda item: (-item[1], item[0]))[:10])
    current_week_avg, previous_week_avg, weekly_delta = _weekly_response_delta(response_records)
    if current_week_avg is not None:
        lines.append(f"- trailing_7d_avg_chars: {current_week_avg:.1f}")
    if previous_week_avg is not None:
        lines.append(f"- previous_7d_avg_chars: {previous_week_avg:.1f}")
    if weekly_delta is not None:
        lines.append(f"- trailing_7d_delta_chars: {weekly_delta:+.1f}")

    if change_date:
        before, after = _slice_by_change_date(response_records, change_date)
        if before:
            lines.append(f"- before_{change_date}_avg_chars: {sum(int(r.get('response_chars') or 0) for r in before) / len(before):.1f}")
        if after:
            lines.append(f"- on_after_{change_date}_avg_chars: {sum(int(r.get('response_chars') or 0) for r in after) / len(after):.1f}")
    return lines


def _build_slack_summary(records: list[dict[str, Any]], change_date: str | None = None) -> str:
    route_records = _route_records(records)
    response_records = _response_records(records)
    route_class_counts = Counter(_route_class(str(record.get("route") or "")) for record in route_records)
    total = len(route_records)
    premium = route_class_counts.get("premium", 0)
    deterministic = route_class_counts.get("deterministic", 0)
    local = route_class_counts.get("local", 0)
    economy = route_class_counts.get("economy", 0)

    top_risk_records = [r for r in route_records if _bucket_for_message(str(r.get("message") or "")) == "top_risk"]
    mail_records = [r for r in route_records if _bucket_for_message(str(r.get("message") or "")) == "mail"]
    top_risk_after_premium = 0
    mail_after_premium = 0
    avg_chars = None
    current_week_avg, previous_week_avg, weekly_delta = _weekly_response_delta(response_records)
    if change_date:
        _, after = _slice_by_change_date(route_records, change_date)
        top_risk_after_premium = sum(
            1 for r in after
            if _bucket_for_message(str(r.get("message") or "")) == "top_risk"
            and _route_class(str(r.get("route") or "")) == "premium"
        )
        mail_after_premium = sum(
            1 for r in after
            if _bucket_for_message(str(r.get("message") or "")) == "mail"
            and _route_class(str(r.get("route") or "")) == "premium"
        )
    if response_records:
        avg_chars = sum(int(r.get("response_chars") or 0) for r in response_records) / len(response_records)

    return "\n".join(
        [
            "OpenClaw route audit",
            f"- records: {total}",
            f"- route mix: deterministic {deterministic} / local {local} / economy {economy} / premium {premium}",
            f"- premium share: {(premium / total):.1%}" if total else "- premium share: 0.0%",
            f"- avg response chars: {avg_chars:.1f}" if avg_chars is not None else "- avg response chars: n/a",
            (
                f"- avg response chars WoW: {current_week_avg:.1f} ({weekly_delta:+.1f} vs prev {previous_week_avg:.1f})"
                if current_week_avg is not None and previous_week_avg is not None and weekly_delta is not None
                else "- avg response chars WoW: n/a"
            ),
            (
                f"- top risk after {change_date}: premium {top_risk_after_premium}/{sum(1 for r in route_records if (str(r.get('ts') or '')[:10] >= change_date) and _bucket_for_message(str(r.get('message') or '')) == 'top_risk')}"
                if change_date else f"- top risk queries: {len(top_risk_records)}"
            ),
            (
                f"- mail after {change_date}: premium {mail_after_premium}/{sum(1 for r in route_records if (str(r.get('ts') or '')[:10] >= change_date) and _bucket_for_message(str(r.get('message') or '')) == 'mail')}"
                if change_date else f"- mail queries: {len(mail_records)}"
            ),
            "- note: top risk/mail/status are being pushed toward deterministic or cheap paths first",
        ]
    )


def build_summary(
    records: list[dict[str, Any]],
    generated_for: str | None = None,
    label: str = "route-audit",
    change_date: str | None = None,
) -> str:
    route_records = _route_records(records)
    route_counts = Counter(record.get("route") or "unknown" for record in route_records)
    risk_counts = Counter(record.get("risk_level") or "unknown" for record in route_records)
    blocked_counts = Counter(record.get("route") or "unknown" for record in route_records if record.get("blocked"))
    model_counts = Counter(record.get("model") or "none" for record in route_records)
    flag_counts = Counter(flag for record in route_records for flag in (record.get("flags") or []))
    route_class_counts = Counter(_route_class(str(record.get("route") or "")) for record in route_records)

    total = len(route_records)
    blocked_total = sum(1 for record in route_records if record.get("blocked"))
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
        "## Route Classes",
        "",
        *_counter_lines(route_class_counts),
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
        "## Response Length",
        "",
        *_response_length_lines(records, change_date=change_date),
        "",
        "## Target Query Routing",
        "",
        *_target_query_lines(route_records, change_date=change_date),
        "",
        "## Risk Flags",
        "",
        *_counter_lines(flag_counts),
        "",
        "## Recent Blocked Examples",
        "",
        *_blocked_examples(route_records),
        "",
        "## Failure Memory Candidates",
        "",
        *_failure_memory_candidates(route_records),
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
    parser.add_argument("--change-date", default="2026-05-31")
    parser.add_argument("--to-slack", action="store_true")
    parser.add_argument("--route", default="exec_president_decisions")
    parser.add_argument("--to-notion", action="store_true")
    args = parser.parse_args()

    records = _load_records(args.audit_path, limit=args.limit)
    summary = build_summary(records, generated_for=args.date, label=args.archive_label, change_date=args.change_date)
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

    if args.to_slack:
        sys.path.insert(0, str(PROJECT_ROOT))
        from adapters.content.slack_router import send_slack_route

        send_slack_route(args.route, {"text": _build_slack_summary(records, change_date=args.change_date)})
        result["slack_route"] = args.route

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
