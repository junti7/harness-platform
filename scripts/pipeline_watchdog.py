"""
Pipeline Watchdog — 파이프라인 이상 감지 시 CEO Slack 즉시 알림

감시 항목:
  1. 핵심 launchctl 서비스 크래시 (exit code ≠ 0)
  2. raw_signals 수집 정체 (24h 내 신규 0건)
  3. Tier 2 필터 정체 (filtered_signals 6h 내 신규 0건 + pending 100건 초과)
  4. Tier 3 정제 정체 (refined_outputs 48h 내 신규 0건)
  5. IBKR Gateway 연결 끊김 (포트 4002 미응답)
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import httpx
from core.database import execute_query

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL   = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")

CRITICAL_SERVICES = [
    "com.harness.pipeline",
    "com.harness.tier2-filter",
    "com.harness.tier2-filter-fast",
    "com.harness.harness-os-backend",
]

IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4002


# ── Slack 알림 ──────────────────────────────────────────────────────────────

def _send_alert(title: str, issues: list[str]) -> None:
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL:
        print("[WARN] Slack 미설정 — 알림 생략")
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(f"• {i}" for i in issues)
    text = f":rotating_light: *[파이프라인 이상 감지]* {title}\n{body}\n_검출 시각: {now}_"
    try:
        httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                     "Content-Type": "application/json"},
            json={"channel": SLACK_CHANNEL, "text": text,
                  "blocks": [{"type": "section",
                               "text": {"type": "mrkdwn", "text": text}}]},
            timeout=10,
        )
        print(f"[OK] Slack 알림 전송: {title}")
    except Exception as e:
        print(f"[ERROR] Slack 전송 실패: {e}")


# ── 감시 체크 ────────────────────────────────────────────────────────────────

def _check_services() -> list[str]:
    issues = []
    try:
        out = subprocess.run(
            ["launchctl", "list"], capture_output=True, text=True, timeout=10
        ).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            pid, exit_code, label = parts[0], parts[1], parts[2]
            if label not in CRITICAL_SERVICES:
                continue
            if pid == "-" and exit_code not in ("0", "-"):
                issues.append(f"서비스 크래시: `{label}` (exit={exit_code})")
    except Exception as e:
        issues.append(f"launchctl 조회 실패: {e}")
    return issues


def _check_db() -> list[str]:
    issues = []
    try:
        # Tier 1 수집 정체
        r = execute_query(
            "SELECT COUNT(*) AS cnt FROM raw_signals WHERE ingested_at > NOW() - INTERVAL '24 hours'",
            fetch=True,
        )
        if r and int(r[0]["cnt"]) == 0:
            issues.append("Tier 1 수집 24h 신규 0건 — 수집 파이프라인 정지 의심")

        # Tier 2 필터 정체
        r2 = execute_query(
            "SELECT COUNT(*) AS cnt FROM filtered_signals WHERE created_at > NOW() - INTERVAL '6 hours'",
            fetch=True,
        )
        pending = execute_query(
            "SELECT COUNT(*) AS cnt FROM raw_signals WHERE status = 'pending'",
            fetch=True,
        )
        fs_6h = int(r2[0]["cnt"]) if r2 else 0
        pend_cnt = int(pending[0]["cnt"]) if pending else 0
        if fs_6h == 0 and pend_cnt > 100:
            issues.append(f"Tier 2 필터 정체: pending {pend_cnt}건 / 6h 처리 0건")

        # Tier 3 정제 정체
        r3 = execute_query(
            "SELECT COUNT(*) AS cnt FROM refined_outputs WHERE created_at > NOW() - INTERVAL '48 hours'",
            fetch=True,
        )
        if r3 and int(r3[0]["cnt"]) == 0:
            issues.append("Tier 3 정제 48h 신규 0건 — 정제 파이프라인 정지 의심")


    except Exception as e:
        issues.append(f"DB 상태 조회 실패: {e}")
    return issues


# ── IBKR Gateway 체크 ────────────────────────────────────────────────────────

def _check_ibkr() -> list[str]:
    try:
        with socket.create_connection((IBKR_HOST, IBKR_PORT), timeout=5):
            print(f"[OK] IBKR Gateway {IBKR_HOST}:{IBKR_PORT} 연결 정상")
            return []
    except OSError:
        return [f"🚨 IBKR Gateway 연결 끊김 — {IBKR_HOST}:{IBKR_PORT} 미응답\n  → 수동 재로그인 필요 (Mac Mini 화면 공유 또는 VNC Viewer)"]


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Watchdog 실행")

    all_issues: list[str] = []
    all_issues.extend(_check_services())
    all_issues.extend(_check_db())
    all_issues.extend(_check_ibkr())

    if all_issues:
        print(f"[ALERT] 이상 {len(all_issues)}건 감지")
        for i in all_issues:
            print(f"  - {i}")
        _send_alert(f"이상 {len(all_issues)}건 감지", all_issues)
    else:
        print("[OK] 파이프라인 정상")


if __name__ == "__main__":
    if "--ibkr-only" in sys.argv:
        print(f"[{datetime.now(timezone.utc).isoformat()}] IBKR Watchdog 실행")
        issues = _check_ibkr()
        if issues:
            print(f"[ALERT] IBKR Gateway 연결 끊김")
            _send_alert("IBKR Gateway 연결 끊김", issues)
        else:
            print("[OK] IBKR Gateway 정상")
    else:
        main()
