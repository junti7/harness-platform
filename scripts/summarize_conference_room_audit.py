from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = Path("docs/reports/conference_room_stream.jsonl")
DEFAULT_OUTPUT_DIR = Path("docs/reviews/conference_room_audit")
_AUTHOR_RE = re.compile(r"^\*([^*]+)\*:")
_NOISE_PATTERNS = (
    "my apologies",
    "plan mode",
    "update_topic(",
    "reading additional input from stdin",
    "failed to refresh token",
    "i will write the content to the file",
    "안녕하세요",
    "감사합니다",
    "모든 팀의 발언을 잘 들었습니다",
    "다시 한번 감사",
)


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


def _extract_persona_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        text = record.get("text_markdown") or ""
        match = _AUTHOR_RE.match(text)
        if not match:
            continue
        author = match.group(1)
        lowered = text.lower()
        noise_flags = [pattern for pattern in _NOISE_PATTERNS if pattern in lowered]
        rows.append(
            {
                "author": author,
                "posted_at": record.get("posted_at") or "",
                "chars": len(text),
                "noise": bool(noise_flags),
                "noise_flags": noise_flags,
                "preview": text[:220].replace("\n", " "),
            }
        )
    return rows


def _counter_lines(counter: Counter, empty: str = "- none") -> list[str]:
    if not counter:
        return [empty]
    return [f"- {key}: {value}" for key, value in counter.most_common()]


def _row_date(row: dict[str, Any]) -> date | None:
    posted_at = str(row.get("posted_at") or "")
    if len(posted_at) < 10:
        return None
    try:
        return datetime.fromisoformat(posted_at[:19]).date()
    except ValueError:
        return None


def _window_average_chars(rows: list[dict[str, Any]], *, end_date: date, days: int) -> float | None:
    start_date = end_date - timedelta(days=days - 1)
    values: list[int] = []
    for row in rows:
        row_date = _row_date(row)
        if row_date is None:
            continue
        if start_date <= row_date <= end_date:
            values.append(int(row["chars"]))
    if not values:
        return None
    return sum(values) / len(values)


def _weekly_char_delta(rows: list[dict[str, Any]], window_days: int = 7) -> tuple[float | None, float | None, float | None]:
    dated_rows = [row for row in rows if _row_date(row) is not None]
    if not dated_rows:
        return None, None, None
    latest_date = max(_row_date(row) for row in dated_rows if _row_date(row) is not None)
    if latest_date is None:
        return None, None, None
    current_avg = _window_average_chars(dated_rows, end_date=latest_date, days=window_days)
    previous_end_date = latest_date - timedelta(days=window_days)
    previous_avg = _window_average_chars(dated_rows, end_date=previous_end_date, days=window_days)
    delta = None if current_avg is None or previous_avg is None else current_avg - previous_avg
    return current_avg, previous_avg, delta


def _top_persona_weekly_deltas(rows: list[dict[str, Any]], limit: int = 3) -> list[tuple[str, float | None, float | None, float | None, float]]:
    by_author: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_author[row["author"]].append(row)

    ranked = sorted(
        (
            (
                author,
                _weekly_char_delta(items)[0],
                _weekly_char_delta(items)[1],
                _weekly_char_delta(items)[2],
                mean(item["chars"] for item in items),
            )
            for author, items in by_author.items()
        ),
        key=lambda item: (-item[4], item[0]),
    )
    return ranked[:limit]


def _build_slack_summary(records: list[dict[str, Any]]) -> str:
    rows = _extract_persona_rows(records)
    by_author: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pattern_counter: Counter[str] = Counter()
    for row in rows:
        by_author[row["author"]].append(row)
        pattern_counter.update(row["noise_flags"])

    total = len(rows)
    noisy_total = sum(1 for row in rows if row["noise"])
    noisy_rate = (noisy_total / total) if total else 0.0
    current_week_avg, previous_week_avg, weekly_delta = _weekly_char_delta(rows)
    top_deltas = _top_persona_weekly_deltas(rows, limit=3)

    longest = sorted(
        (
            (author, mean(item["chars"] for item in items))
            for author, items in by_author.items()
        ),
        key=lambda item: (-item[1], item[0]),
    )[:3]

    lines = [
        "Conference room audit",
        f"- persona_messages: {total}",
        f"- noisy_messages: {noisy_total} ({noisy_rate:.1%})",
        (
            f"- avg chars WoW: {current_week_avg:.1f} ({weekly_delta:+.1f} vs prev {previous_week_avg:.1f})"
            if current_week_avg is not None and previous_week_avg is not None and weekly_delta is not None
            else "- avg chars WoW: n/a"
        ),
    ]
    if longest:
        lines.append(
            "- longest_avg: "
            + ", ".join(f"{author} {avg:.0f}" for author, avg in longest)
        )
    if top_deltas:
        lines.append(
            "- top3 WoW: "
            + ", ".join(
                (
                    f"{author} {current_avg:.0f} ({delta:+.0f})"
                    if current_avg is not None and delta is not None
                    else f"{author} n/a"
                )
                for author, current_avg, _previous_avg, delta, _overall_avg in top_deltas
            )
        )
    if pattern_counter:
        lines.append(
            "- top_noise: "
            + ", ".join(f"{pattern} {count}" for pattern, count in pattern_counter.most_common(3))
        )
    lines.append("- action: trim long personas and keep greetings/tool-noise suppressed")
    return "\n".join(lines)


def build_summary(records: list[dict[str, Any]], generated_for: str | None = None, label: str = "conference-room") -> str:
    rows = _extract_persona_rows(records)
    generated_for = generated_for or date.today().isoformat()
    current_week_avg, previous_week_avg, weekly_delta = _weekly_char_delta(rows)
    top_deltas = _top_persona_weekly_deltas(rows, limit=3)

    by_author: dict[str, list[dict[str, Any]]] = defaultdict(list)
    noise_counter: Counter[str] = Counter()
    pattern_counter: Counter[str] = Counter()
    for row in rows:
        by_author[row["author"]].append(row)
        if row["noise"]:
            noise_counter[row["author"]] += 1
            pattern_counter.update(row["noise_flags"])

    total = len(rows)
    noisy_total = sum(1 for row in rows if row["noise"])
    noisy_rate = (noisy_total / total) if total else 0.0

    persona_lines: list[str] = []
    for author, items in sorted(by_author.items(), key=lambda kv: (-mean(r["chars"] for r in kv[1]), kv[0])):
        chars = [row["chars"] for row in items]
        persona_lines.append(
            f"- {author}: n={len(items)} | avg={mean(chars):.1f} | median={median(chars):.1f} | max={max(chars)} | noise={noise_counter[author]}"
        )

    delta_lines = [
        (
            f"- {author}: trailing_7d={current_avg:.1f} | previous_7d={previous_avg:.1f} | delta={delta:+.1f}"
            if current_avg is not None and previous_avg is not None and delta is not None
            else f"- {author}: trailing_7d={current_avg:.1f} | previous_7d=n/a | delta=n/a"
        )
        for author, current_avg, previous_avg, delta, _overall_avg in top_deltas
        if current_avg is not None
    ] or ["- none"]

    long_examples = [
        f"- {row['chars']} chars | {row['author']} | {row['posted_at']} | {row['preview']}"
        for row in sorted(rows, key=lambda item: item["chars"], reverse=True)[:10]
    ] or ["- none"]

    noisy_examples = [
        f"- {row['author']} | {row['posted_at']} | flags={','.join(row['noise_flags'])} | {row['preview']}"
        for row in [r for r in rows if r["noise"]][:10]
    ] or ["- none"]

    lines = [
        f"# Conference Room Audit Summary ({label}) - {generated_for}",
        "",
        "## Summary",
        "",
        f"- persona_messages_reviewed: {total}",
        f"- noisy_messages: {noisy_total}",
        f"- noisy_rate: {noisy_rate:.1%}",
        f"- trailing_7d_avg_chars: {current_week_avg:.1f}" if current_week_avg is not None else "- trailing_7d_avg_chars: n/a",
        f"- previous_7d_avg_chars: {previous_week_avg:.1f}" if previous_week_avg is not None else "- previous_7d_avg_chars: n/a",
        f"- trailing_7d_delta_chars: {weekly_delta:+.1f}" if weekly_delta is not None else "- trailing_7d_delta_chars: n/a",
        "",
        "## Persona Length Table",
        "",
        *(persona_lines or ["- none"]),
        "",
        "## Top Persona WoW",
        "",
        *delta_lines,
        "",
        "## Noise Patterns",
        "",
        *_counter_lines(pattern_counter),
        "",
        "## Longest Messages",
        "",
        *long_examples,
        "",
        "## Noisy Message Examples",
        "",
        *noisy_examples,
        "",
        "## Operator Note",
        "",
        "- Prioritize trimming personas whose median message length remains above 1,200 chars.",
        "- Treat `plan mode`, `update_topic`, CLI auth noise, and apology-prefixed retries as defects, not content.",
        "- Re-run after prompt or provider changes to confirm the median and max length actually dropped.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize conference room persona chatter into an operating memo.")
    parser.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output-name")
    parser.add_argument("--archive-label", default="conference-room")
    parser.add_argument("--to-slack", action="store_true")
    parser.add_argument("--route", default="exec_president_decisions")
    args = parser.parse_args()

    records = _load_records(args.audit_path, limit=args.limit)
    summary = build_summary(records, generated_for=args.date, label=args.archive_label)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_name or f"conference_room_audit_{args.date}.md"
    output_path = args.output_dir / output_name
    output_path.write_text(summary, encoding="utf-8")

    result = {
        "records_reviewed": len(records),
        "output_path": str(output_path),
    }

    if args.to_slack:
        import sys

        sys.path.insert(0, str(PROJECT_ROOT))
        from adapters.content.slack_router import send_slack_route

        send_slack_route(args.route, {"text": _build_slack_summary(records)})
        result["slack_route"] = args.route

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
