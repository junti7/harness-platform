#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from edu_coach_simulation_runner import run_simulation


DEFAULT_MIN_CORPUS_RECORDS = 30264
DEFAULT_MIN_YOUTUBE_RECORDS = 1649


def _needs_work(summary: dict[str, Any]) -> int:
    verdict_counts = summary.get("verdict_counts")
    if not isinstance(verdict_counts, dict):
        return 0
    return int(verdict_counts.get("needs_work") or 0)


def _channel_count(summary: dict[str, Any], channel: str) -> int:
    channel_counts = summary.get("channel_counts")
    if not isinstance(channel_counts, dict):
        return 0
    return int(channel_counts.get(channel) or 0)


def check_regression(
    *,
    min_corpus_records: int = DEFAULT_MIN_CORPUS_RECORDS,
    min_youtube_records: int = DEFAULT_MIN_YOUTUBE_RECORDS,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    if report_dir is None:
        temp_context = tempfile.TemporaryDirectory(prefix="edu_coach_regression_")
        work_dir = Path(temp_context.name)
    else:
        temp_context = None
        work_dir = report_dir
        work_dir.mkdir(parents=True, exist_ok=True)
    try:
        adversarial = run_simulation(candidate_source="adversarial-current-fallback", report_dir=work_dir)
        corpus = run_simulation(candidate_source="corpus-current-fallback", report_dir=work_dir)
    finally:
        if temp_context is not None:
            temp_context.cleanup()

    failures: list[str] = []
    adversarial_needs_work = _needs_work(adversarial)
    corpus_needs_work = _needs_work(corpus)
    corpus_records = int(corpus.get("record_count") or 0)
    youtube_records = _channel_count(corpus, "YouTube")

    if adversarial_needs_work != 0:
        failures.append(f"adversarial_needs_work={adversarial_needs_work}")
    if corpus_needs_work != 0:
        failures.append(f"corpus_needs_work={corpus_needs_work}")
    if corpus_records < min_corpus_records:
        failures.append(f"corpus_records={corpus_records}<min={min_corpus_records}")
    if youtube_records < min_youtube_records:
        failures.append(f"youtube_records={youtube_records}<min={min_youtube_records}")

    return {
        "ok": not failures,
        "failures": failures,
        "adversarial": {
            "record_count": int(adversarial.get("record_count") or 0),
            "verdict_counts": adversarial.get("verdict_counts") or {},
            "top_issues": adversarial.get("top_issues") or [],
        },
        "corpus": {
            "record_count": corpus_records,
            "youtube_records": youtube_records,
            "verdict_counts": corpus.get("verdict_counts") or {},
            "top_issues": corpus.get("top_issues") or [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail if EDU safety-coach max corpus/adversarial regression tests degrade.")
    parser.add_argument("--min-corpus-records", type=int, default=DEFAULT_MIN_CORPUS_RECORDS)
    parser.add_argument("--min-youtube-records", type=int, default=DEFAULT_MIN_YOUTUBE_RECORDS)
    parser.add_argument("--report-dir", type=Path, default=None, help="optional report directory; default uses a temp dir")
    args = parser.parse_args()
    summary = check_regression(
        min_corpus_records=max(1, args.min_corpus_records),
        min_youtube_records=max(1, args.min_youtube_records),
        report_dir=args.report_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
