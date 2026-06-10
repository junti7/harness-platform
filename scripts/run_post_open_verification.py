#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PYTHON = ROOT / ".venv" / "bin" / "python"
RESET_STATUS_PATH = ROOT / "docs" / "reports" / "paper_trading_reset_status.json"
REPORT_PATH = ROOT / "docs" / "reports" / "post_open_verification.json"
ALERT_STATE_PATH = ROOT / "runtime" / "post_open_verification_alert_state.json"
UNREADY_ALERT_THRESHOLD_SEC = int(os.getenv("POST_OPEN_UNREADY_ALERT_THRESHOLD_SEC", "1800"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from adapters.content.slack_router import send_slack_route


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_json(cmd: list[str]) -> dict:
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    payload: dict[str, object] = {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    text = completed.stdout.strip()
    if text:
        try:
            payload["json"] = json.loads(text)
        except json.JSONDecodeError:
            pass
    return payload


def summarize_cycle(result: dict) -> dict:
    text = str(result.get("stdout", "")).strip()
    if not text:
        return {"status": "empty", "returncode": result.get("returncode")}
    try:
        parsed = json.loads(text)
        return {
            "status": parsed.get("status"),
            "reason": parsed.get("reason"),
            "returncode": result.get("returncode"),
        }
    except json.JSONDecodeError:
        return {
            "status": "ok" if result.get("returncode") == 0 else "error",
            "returncode": result.get("returncode"),
            "tail": text.splitlines()[-5:],
        }


def load_alert_state() -> dict:
    if not ALERT_STATE_PATH.exists():
        return {}
    try:
        return json.loads(ALERT_STATE_PATH.read_text())
    except Exception:
        return {}


def save_alert_state(payload: dict) -> None:
    ALERT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def _post_incident(text: str) -> None:
    try:
        send_slack_route("ops_incidents", {"text": text})
    except Exception:
        pass


def update_incident_state(verdict: dict) -> dict:
    now = datetime.now(timezone.utc)
    state = load_alert_state()
    previous_ready = bool(state.get("ready_for_execute")) if state else False
    current_ready = bool(verdict.get("ready_for_execute"))

    if current_ready:
        if state.get("alerted_unready"):
            _post_incident(
                "*Trading Post-Open Recovery*\n"
                f"- checked_at: `{verdict.get('checked_at')}`\n"
                "- status: `ready_for_execute=true`\n"
                "- note: post-open verification recovered; execute remains manual until dry-run-only window completes."
            )
        new_state = {
            "checked_at": verdict.get("checked_at"),
            "ready_for_execute": True,
            "unready_since": None,
            "alerted_unready": False,
            "last_transition": now.isoformat(timespec="seconds"),
        }
        save_alert_state(new_state)
        return new_state

    unready_since = state.get("unready_since")
    if previous_ready or not unready_since:
        unready_since = verdict.get("checked_at") or now.isoformat(timespec="seconds")
    alerted_unready = bool(state.get("alerted_unready"))
    try:
        unready_dt = datetime.fromisoformat(str(unready_since))
        unready_duration_sec = max(0, int((now - unready_dt).total_seconds()))
    except Exception:
        unready_duration_sec = 0

    if unready_duration_sec >= UNREADY_ALERT_THRESHOLD_SEC and not alerted_unready:
        next_actions = verdict.get("next_action") or []
        alpaca_status = ((verdict.get("alpaca_dry_run") or {}) if isinstance(verdict.get("alpaca_dry_run"), dict) else {})
        ibkr_status = ((verdict.get("ibkr_dry_run") or {}) if isinstance(verdict.get("ibkr_dry_run"), dict) else {})
        _post_incident(
            "*Trading Post-Open Blocked*\n"
            f"- checked_at: `{verdict.get('checked_at')}`\n"
            f"- ready_for_execute: `false`\n"
            f"- unready_minutes: `{unready_duration_sec // 60}`\n"
            f"- alpaca_dry_run: `{alpaca_status.get('status', '대기')}`\n"
            f"- ibkr_dry_run: `{ibkr_status.get('status', '대기')}`\n"
            f"- next_action: `{'; '.join(str(x) for x in next_actions[:2]) or 'review post_open_verification.json'}`"
        )
        alerted_unready = True

    new_state = {
        "checked_at": verdict.get("checked_at"),
        "ready_for_execute": False,
        "unready_since": unready_since,
        "unready_duration_sec": unready_duration_sec,
        "alerted_unready": alerted_unready,
        "last_transition": state.get("last_transition") or now.isoformat(timespec="seconds"),
    }
    save_alert_state(new_state)
    return new_state


TRADER_LABELS = {
    "alpaca": "com.harness.turtle-auto-trader",
    "ibkr": "com.harness.ibkr-auto-trader",
}


def scheduler_status() -> dict:
    """두 자동매매 launchd 잡의 로드 여부를 실측. execute 자동 집행 활성 여부 판단용.

    probe_ok=False(launchctl 미응답)이면 로드 여부를 '미상'으로 처리해, 실패를 OFF로 오표시하지 않는다.
    """
    loaded: dict[str, bool] = {"alpaca": False, "ibkr": False}
    probe_ok = True
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
        labels = {line.split()[-1] for line in out.splitlines() if line.strip()}
        for broker, label in TRADER_LABELS.items():
            loaded[broker] = label in labels
    except Exception:
        probe_ok = False
    return {
        "probe_ok": probe_ok,
        "alpaca_loaded": loaded["alpaca"],
        "ibkr_loaded": loaded["ibkr"],
        "auto_execute_active": probe_ok and loaded["alpaca"] and loaded["ibkr"],
        "schedule": "평일(월~금) Alpaca 22:30 · IBKR 22:35 KST (13:30/13:35 UTC, 미국장 개장)",
    }


def main() -> int:
    runtime = run_json([str(PYTHON), "scripts/trading_runtime_guard.py"])
    flat_check = run_json([str(PYTHON), "scripts/check_paper_books_flat.py"])
    reset_status = {}
    if RESET_STATUS_PATH.exists():
        try:
            reset_status = json.loads(RESET_STATUS_PATH.read_text())
        except Exception as exc:  # pragma: no cover - defensive
            reset_status = {"read_error": str(exc)}

    flat = bool(reset_status.get("flat"))
    alpaca_cycle = None
    ibkr_cycle = None
    if flat:
        alpaca_cycle = run_json([str(PYTHON), "scripts/run_trading_cycle.py", "--broker", "alpaca"])
        ibkr_cycle = run_json([str(PYTHON), "scripts/run_trading_cycle.py", "--broker", "ibkr"])

    verdict = {
        "checked_at": now_iso(),
        "runtime_guard": runtime.get("json", {"returncode": runtime.get("returncode"), "stderr": runtime.get("stderr")}),
        "flat_check": flat_check.get("json", {"returncode": flat_check.get("returncode"), "stderr": flat_check.get("stderr")}),
        "reset_status": reset_status,
        "ready_for_execute": False,
        "next_action": [],
        "scheduler": scheduler_status(),
    }

    runtime_ok = bool(verdict["runtime_guard"].get("ok")) if isinstance(verdict["runtime_guard"], dict) else False
    flat_ok = bool(reset_status.get("flat"))

    if not runtime_ok:
        verdict["next_action"].append("trading_runtime_guard 이슈를 먼저 해소합니다.")
    if not flat_ok:
        verdict["next_action"].append("브로커 청산 주문 체결 여부를 재확인하고 flat 완료까지 execute를 계속 차단합니다.")

    if alpaca_cycle is not None and ibkr_cycle is not None:
        verdict["alpaca_dry_run"] = summarize_cycle(alpaca_cycle)
        verdict["ibkr_dry_run"] = summarize_cycle(ibkr_cycle)
        alpaca_ok = verdict["alpaca_dry_run"].get("returncode") == 0
        ibkr_ok = verdict["ibkr_dry_run"].get("returncode") == 0
        verdict["ready_for_execute"] = runtime_ok and flat_ok and alpaca_ok and ibkr_ok
        if not alpaca_ok:
            verdict["next_action"].append("Alpaca dry-run 실패 원인을 수정합니다.")
        if not ibkr_ok:
            verdict["next_action"].append("IBKR dry-run 실패 원인을 수정합니다.")
        if verdict["ready_for_execute"]:
            sched = verdict["scheduler"]
            if not sched.get("probe_ok"):
                verdict["next_action"].append(
                    "스케줄러 상태 확인 불가(launchctl 미응답) — 자동 execute 활성 여부를 수동 점검하세요."
                )
            elif sched.get("auto_execute_active"):
                verdict["next_action"].append(
                    f"자동 execute 활성 — {sched.get('schedule')}. 다음 거래일부터 자동 집행됩니다."
                )
            elif sched.get("alpaca_loaded") or sched.get("ibkr_loaded"):
                missing = "IBKR" if not sched.get("ibkr_loaded") else "Alpaca"
                verdict["next_action"].append(
                    f"자동 execute 부분 활성({missing} 스케줄러 미로드) — 해당 launchd 잡을 로드해야 양쪽 자동 집행됩니다."
                )
            else:
                verdict["next_action"].append(
                    "execute 재개 준비 완료. 자동 집행하려면 트레이더 launchd 잡(turtle-auto-trader/ibkr-auto-trader)을 로드하거나 대표 결정으로 재개합니다."
                )

    verdict["incident_state"] = update_incident_state(verdict)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(verdict, ensure_ascii=False, indent=2))
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["ready_for_execute"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
