#!/usr/bin/env python3
"""
Local evidence-based Google Cloud spend analysis.

Purpose:
- Estimate YouTube Data API v3 usage from local collector logs
- Compare with local Gemini token usage from api_cost_log
- Emit a markdown report even when GCP Billing Export is unavailable
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

try:
    import psycopg2
except ImportError:
    psycopg2 = None


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

LOG_PATH = ROOT / "logs" / "2026-ai-seamless-gather.log"
DEFAULT_DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/harness_dev")
PSQL_BIN = shutil.which("psql") or "/opt/homebrew/bin/psql"

RUN_START_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .*교육 DEEP RESEARCH 수집 시작")
CHANNEL_RE = re.compile(r"YouTube API: ")
QUERY_RE = re.compile(r"YouTube API 검색: ")
QUOTA_RE = re.compile(r"Quota exceeded for quota metric 'Search Queries'")
API_NEW_RE = re.compile(r"API 신규: (?P<count>\d+)개")

YOUTUBE_CHANNEL_LOOKUP_UNITS = 1
YOUTUBE_SEARCH_UNITS = 100


@dataclass
class RunStats:
    timestamp: str
    channel_calls: int = 0
    query_calls: int = 0
    quota_exceeded: bool = False
    api_new_items: int = 0

    @property
    def estimated_units(self) -> int:
        channel_units = self.channel_calls * (YOUTUBE_CHANNEL_LOOKUP_UNITS + YOUTUBE_SEARCH_UNITS)
        query_units = self.query_calls * YOUTUBE_SEARCH_UNITS
        return channel_units + query_units


def parse_runs(log_path: Path, day: str) -> list[RunStats]:
    if not log_path.exists():
        return []

    runs: list[RunStats] = []
    current: RunStats | None = None

    for raw_line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw_line.startswith(day):
            continue
        start_match = RUN_START_RE.search(raw_line)
        if start_match:
            current = RunStats(timestamp=start_match.group("ts"))
            runs.append(current)
            continue
        if current is None:
            continue
        if CHANNEL_RE.search(raw_line):
            current.channel_calls += 1
        if QUERY_RE.search(raw_line):
            current.query_calls += 1
        if QUOTA_RE.search(raw_line):
            current.quota_exceeded = True
        if "YouTube 수집 병합 완료" in raw_line:
            new_match = API_NEW_RE.search(raw_line)
            if new_match:
                current.api_new_items = int(new_match.group("count"))

    return runs


def fetch_gemini_usage(day: str, db_url: str) -> dict[str, float | int | str]:
    if psycopg2 is None:
        return {"available": "no", "reason": "psycopg2 unavailable"}
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COALESCE(COUNT(*), 0),
                COALESCE(SUM(input_tokens), 0),
                COALESCE(SUM(output_tokens), 0)
            FROM api_cost_log
            WHERE DATE(created_at) = %s
              AND provider = 'google'
            """,
            (day,),
        )
        calls, input_tokens, output_tokens = cur.fetchone()
        return {
            "available": "yes",
            "calls": int(calls or 0),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
        }
    except Exception as exc:
        fallback = fetch_gemini_usage_via_psql(day)
        if fallback.get("available") == "yes":
            return fallback
        return {"available": "no", "reason": str(exc)}
    finally:
        if "conn" in locals():
            conn.close()


def fetch_gemini_usage_via_psql(day: str) -> dict[str, float | int | str]:
    sql = (
        f"SELECT COALESCE(COUNT(*),0), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0) "
        f"FROM api_cost_log WHERE DATE(created_at)=DATE '{day}' AND provider='google';"
    )
    try:
        result = subprocess.run(
            [PSQL_BIN, "harness_dev", "-t", "-A", "-F", "|", "-c", sql],
            check=True,
            capture_output=True,
            text=True,
        )
        line = next((row.strip() for row in result.stdout.splitlines() if row.strip()), "")
        if not line:
            return {"available": "yes", "calls": 0, "input_tokens": 0, "output_tokens": 0}
        calls, input_tokens, output_tokens = [int(part or 0) for part in line.split("|")]
        return {
            "available": "yes",
            "calls": calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    except Exception as exc:
        return {"available": "no", "reason": f"psql fallback failed: {exc}"}


def build_report(day: str, runs: list[RunStats], gemini_usage: dict[str, float | int | str]) -> str:
    total_channel_calls = sum(run.channel_calls for run in runs)
    total_query_calls = sum(run.query_calls for run in runs)
    total_units = sum(run.estimated_units for run in runs)
    quota_runs = sum(1 for run in runs if run.quota_exceeded)
    total_api_new_items = sum(run.api_new_items for run in runs)

    lines = [
        f"# Google Cloud Spend Analysis - {day}",
        "",
        "## Verdict",
    ]
    if total_units > 0:
        lines.append(
            f"- 가장 유력한 원인: `YouTube Data API v3` 사용. 추정 quota units={total_units}, quota exceeded runs={quota_runs}."
        )
    else:
        lines.append("- YouTube Data API 사용 흔적이 로컬 로그에서 확인되지 않았습니다.")

    if gemini_usage.get("available") == "yes":
        lines.append(
            "- Gemini 사용은 보조 요인 수준."
            f" calls={gemini_usage['calls']}, input_tokens={gemini_usage['input_tokens']},"
            f" output_tokens={gemini_usage['output_tokens']}."
        )
    else:
        lines.append(f"- Gemini 원천 로그 확인 불가: {gemini_usage.get('reason', 'unknown')}.")

    lines.extend(
        [
            "",
            "## YouTube Evidence",
            f"- runs={len(runs)}",
            f"- channel_calls={total_channel_calls}",
            f"- search_queries={total_query_calls}",
            f"- estimated_units={total_units}",
            f"- api_new_items={total_api_new_items}",
            f"- quota_exceeded_runs={quota_runs}",
            "",
            "## Per Run",
        ]
    )

    if not runs:
        lines.append("- no runs found")
    else:
        for run in runs:
            lines.append(
                f"- {run.timestamp} | channels={run.channel_calls} | queries={run.query_calls} "
                f"| units~={run.estimated_units} | api_new={run.api_new_items} "
                f"| quota_exceeded={'yes' if run.quota_exceeded else 'no'}"
            )

    lines.extend(
        [
            "",
            "## Billing Export Status",
            "- 로컬 환경에서는 GCP Billing Export / BigQuery SKU 데이터를 직접 조회하지 못했습니다.",
            "- 따라서 이 리포트는 코드/로그/DB 기반의 강한 정황 분석입니다.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze likely Google Cloud spend drivers from local evidence.")
    parser.add_argument("--day", required=True, help="Target day in YYYY-MM-DD")
    parser.add_argument("--log-path", default=str(LOG_PATH), help="Collector log path")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="Database URL for api_cost_log lookup")
    parser.add_argument("--write-report", action="store_true", help="Write markdown report to docs/reviews")
    args = parser.parse_args()

    runs = parse_runs(Path(args.log_path), args.day)
    gemini_usage = fetch_gemini_usage(args.day, args.db_url)
    report = build_report(args.day, runs, gemini_usage)
    print(report)

    if args.write_report:
        report_dir = ROOT / "docs" / "reviews" / "google_cloud_spend"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"google_cloud_spend_{args.day}.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"[written] {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
