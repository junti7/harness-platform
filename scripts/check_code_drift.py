#!/usr/bin/env python3
"""코드 드리프트 가드 — 라이브 작업트리가 SoT(origin/main)와 어긋나는지 감지.

이번(2026-06-09) 사고의 재발 방지용. 두 가지 실패 모드를 모두 잡는다.
  (A) 프로덕션에 커밋되지 않은 코드 편집 (git에 안 보이고 유실 위험)
  (B) 개발 머신에서 commit 했지만 push 안 한 코드 (프로덕션에 도달 못 함)

원리: "지금 이 머신의 작업트리"를 origin/main과 직접 비교한다.
critical 코드 경로에서 차이가 1줄이라도 나면 drift로 본다.
런타임 생성물(universe.json, *.jsonl, reports/reviews 등)은 제외해 오탐을 막는다.

사용:
  PYTHONPATH=. .venv/bin/python scripts/check_code_drift.py            # 사람이 읽는 리포트
  PYTHONPATH=. .venv/bin/python scripts/check_code_drift.py --slack    # drift 시 Slack 경보
  PYTHONPATH=. .venv/bin/python scripts/check_code_drift.py --quiet     # drift 없으면 무음

종료 코드: drift 있으면 1, 없으면 0 (cron/launchd에서 분기 가능).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

# SoT와 반드시 일치해야 하는 critical 코드 경로
CRITICAL_PATHS = [
    "core/",
    "adapters/",
    "scripts/",
    "configs/",
    "harness-os/backend/",
    "harness-os/frontend/src/",
    "run_pipeline.py",
    "CLAUDE.md",
    "docs/product/PLATFORM.md",
]

# 런타임에 재생성되는 산출물 — drift 판정에서 제외 (만성 오탐 방지)
EXCLUDE_SUFFIXES = (
    ".log",
    ".jsonl",
    ".pyc",
)
EXCLUDE_SUBSTRINGS = (
    "docs/trading/universe.json",
    "docs/trading/trading_diary",
    "data/edu_research/",
    "docs/reports/",
    "docs/reviews/",
    "__pycache__/",
    "/dist/",
    "node_modules/",
    "evidence_bank.json",
    "evidence_index.json",
    "paper_trading",
    "ibkr_monitor_cache",
    "ibkr_tws_positions",
)

REMOTE = "origin"
BRANCH = "main"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def _is_excluded(path: str) -> bool:
    if path.endswith(EXCLUDE_SUFFIXES):
        return True
    return any(s in path for s in EXCLUDE_SUBSTRINGS)


def _filter(paths: list[str]) -> list[str]:
    out = []
    for p in paths:
        p = p.strip()
        if not p or _is_excluded(p):
            continue
        if any(p == cp or p.startswith(cp) for cp in CRITICAL_PATHS):
            out.append(p)
    return out


def detect_drift() -> dict:
    subprocess.run(["git", "fetch", REMOTE, "-q"], check=False)
    ref = f"{REMOTE}/{BRANCH}"

    # 작업트리 vs origin/main: 수정/추가/삭제된 추적 파일
    tracked = _git("diff", "--name-only", ref).splitlines()
    # critical 경로의 untracked(커밋 안 된 새 코드)
    untracked = _git(
        "ls-files", "--others", "--exclude-standard", "--", *CRITICAL_PATHS
    ).splitlines()

    drift_tracked = _filter(tracked)
    drift_untracked = _filter(untracked)

    host = _git("rev-parse", "--show-toplevel") or os.getcwd()
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "repo": host,
        "ref": ref,
        "head": _git("rev-parse", "--short", "HEAD"),
        "origin_head": _git("rev-parse", "--short", ref),
        "ahead_behind": _git("rev-list", "--left-right", "--count", f"HEAD...{ref}"),
        "drift_tracked": drift_tracked,
        "drift_untracked": drift_untracked,
        "has_drift": bool(drift_tracked or drift_untracked),
    }


def _post_slack(text: str) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("[slack] SLACK_WEBHOOK_URL 미설정 — 경보 생략", file=sys.stderr)
        return
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:  # noqa: BLE001
        print(f"[slack] 전송 실패: {e}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slack", action="store_true", help="drift 시 Slack 경보")
    ap.add_argument("--quiet", action="store_true", help="drift 없으면 무음")
    args = ap.parse_args()

    r = detect_drift()

    if not r["has_drift"]:
        if not args.quiet:
            print(f"✅ 코드 드리프트 없음 — 작업트리 ≡ {r['ref']} (HEAD {r['head']})")
        return 0

    lines = [
        "🚨 코드 드리프트 감지 — 라이브 코드가 SoT(origin/main)와 어긋남",
        f"  repo: {r['repo']}",
        f"  HEAD {r['head']} vs {r['ref']} {r['origin_head']} (ahead/behind: {r['ahead_behind']})",
    ]
    if r["drift_tracked"]:
        lines.append(f"  ⚠️ 미반영/미커밋 수정 추적파일 {len(r['drift_tracked'])}:")
        lines += [f"      - {p}" for p in r["drift_tracked"][:30]]
    if r["drift_untracked"]:
        lines.append(f"  ⚠️ 커밋 안 된 새 코드(untracked) {len(r['drift_untracked'])}:")
        lines += [f"      - {p}" for p in r["drift_untracked"][:30]]
    lines.append("  조치: 의도된 변경이면 commit+push, 아니면 `git checkout origin/main -- <path>`로 정합.")
    report = "\n".join(lines)
    print(report)

    if args.slack:
        _post_slack(report)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
