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

import fcntl
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import httpx
from core.database import execute_query
from scripts.alpaca_paper_trading import get_account_summary

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL   = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")
ALLOWED_IBKR_WATCHDOG_HOSTS = {
    host.strip()
    for host in os.getenv(
        "ALLOWED_IBKR_WATCHDOG_HOSTS",
        "bagjuntaeui-Macmini.local,bagjuntaeui-Macmini",
    ).split(",")
    if host.strip()
}

CRITICAL_SERVICES = [
    "com.harness.pipeline",
    "com.harness.tier2-filter",
    "com.harness.tier2-filter-fast",
    "com.harness.harness-os-backend",
]

IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4002

TRADING_REQUIRED_FILES = [
    ROOT / "scripts" / "run_trading_cycle.py",
    ROOT / "scripts" / "build_trading_universe.py",
    ROOT / "scripts" / "check_paper_books_flat.py",
    ROOT / "scripts" / "ibkr_tws_paper_trader.py",
]


def _ibkr_watchdog_allowed_on_this_host() -> bool:
    return socket.gethostname() in ALLOWED_IBKR_WATCHDOG_HOSTS


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


# ── 자가복구(self-healing) ────────────────────────────────────────────────────
#  알림만으로는 자동매매가 멈춘 채 방치된다. watchdog가 직접 복구를 시도한다.

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
TRADER_JOBS = {
    "com.harness.turtle-auto-trader": LAUNCH_AGENTS_DIR / "com.harness.turtle-auto-trader.plist",
    "com.harness.ibkr-auto-trader": LAUNCH_AGENTS_DIR / "com.harness.ibkr-auto-trader.plist",
}
# 게이트웨이 자동 재시작은 start_ibgateway_ibc.sh 단일 경로로만 한다(중복 로직 금지).
# 이 스크립트가: GUI(Aqua) 세션 확인 → IBC 무인 로그인(-inline, Terminal 우회) → 실패 시 open 폴백 →
# 수동 로그인 필요 시 Slack 알림까지 캡슐화한다. watchdog는 트리거만 하고 다음 주기에 4002를 재확인한다.
# (watchdog LaunchAgent도 domain=gui/<uid>이므로 Popen 자식이 GUI 세션을 그대로 상속 → HeadlessException 회피)
GATEWAY_START_SCRIPT = ROOT / "scripts" / "start_ibgateway_ibc.sh"
GW_COOLDOWN_PATH = ROOT / "runtime" / "gateway_restart_cooldown"
GW_LOCK_PATH = ROOT / "runtime" / "gateway_restart.lock"  # 동시 재시작 방지(단일 실행 보장)
GW_RESTART_MIN_INTERVAL_SEC = 600  # 재시작 폭주 방지: 최소 10분 간격
GW_INSTALLATION_MISSING_SUPPRESS_SEC = 6 * 60 * 60
# 명시적 kill-switch: 자가복구가 CEO의 정지 결정을 덮어쓰지 못하게 하는 안전장치.
#  - auto_trading_disabled: 트레이더 잡 자동 reload 중단(자동매매 정지의 canonical 경로).
#  - ibgateway_disabled:    게이트웨이 자동 재시작 중단(게이트웨이를 의도적으로 내릴 때).
# 운영 규약: 자동매매/게이트웨이를 멈추려면 *반드시 이 플래그*를 쓴다. 단순 `launchctl unload`는
# 자가복구가 되살리도록 설계된 동작이므로 정지 수단으로 쓰지 않는다.
AUTO_TRADING_DISABLE_FLAG = ROOT / "runtime" / "auto_trading_disabled"
IBGATEWAY_DISABLE_FLAG = ROOT / "runtime" / "ibgateway_disabled"
IBGATEWAY_STATUS_PATH = ROOT / "docs" / "reports" / "ibkr_gateway_runtime_status.json"


def _loaded_labels() -> set[str] | None:
    """launchctl에 로드된 라벨 집합. 조회 실패/비정상 종료 시 None(판별 불가)."""
    try:
        res = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return None
        labels: set[str] = set()
        for ln in res.stdout.splitlines():
            parts = ln.split()
            # 데이터 행만(헤더 'PID Status Label' 제외): 첫 칼럼이 PID(int) 또는 '-'
            if len(parts) >= 3 and (parts[0] == "-" or parts[0].lstrip("-").isdigit()):
                labels.add(parts[-1])
        return labels
    except Exception:
        return None


def ensure_trader_jobs_loaded() -> list[str]:
    """두 자동매매 launchd 잡이 언로드돼 있으면 자동 reload. 자동매매 중단 방지의 핵심.

    단, AUTO_TRADING_DISABLE_FLAG가 있으면 자동 reload를 건너뛴다(CEO의 명시적 정지 존중).
    """
    if AUTO_TRADING_DISABLE_FLAG.exists():
        return ["⏸️ 자동매매 비활성 플래그 감지 — 트레이더 잡 자동 reload 건너뜀(의도적 중단 존중). 재개하려면 runtime/auto_trading_disabled 삭제"]
    labels = _loaded_labels()
    if labels is None:
        return ["⚠️ launchctl 미응답 — 트레이더 잡 로드 여부 판별 불가(자동복구 보류)"]
    actions: list[str] = []
    for label, plist in TRADER_JOBS.items():
        if label in labels:
            continue
        if not plist.exists():
            actions.append(f"🚨 {label} 미로드 + plist 없음({plist.name}) — 수동 조치 필요")
            continue
        try:
            r = subprocess.run(["launchctl", "load", str(plist)], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                actions.append(f"✅ 자가복구: {label} 언로드 감지 → 자동 reload 성공(다음 거래일 자동 execute 유지)")
            else:
                actions.append(f"🚨 {label} reload 실패(rc={r.returncode}): {r.stderr.strip()[:160]} — 수동 조치 필요")
        except Exception as e:
            actions.append(f"🚨 {label} reload 예외: {e} — 수동 조치 필요")
    return actions


def _gateway_port_open() -> bool:
    try:
        with socket.create_connection((IBKR_HOST, IBKR_PORT), timeout=5):
            return True
    except OSError:
        return False


def _gw_seconds_since_last_restart() -> float | None:
    try:
        if not GW_COOLDOWN_PATH.exists():
            return None
        ts = float(GW_COOLDOWN_PATH.read_text().strip())
        return max(0.0, datetime.now(timezone.utc).timestamp() - ts)
    except Exception:
        return None


def _gateway_status_snapshot() -> dict[str, object] | None:
    try:
        if not IBGATEWAY_STATUS_PATH.exists():
            return None
        return json.loads(IBGATEWAY_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _installation_missing_recently() -> bool:
    payload = _gateway_status_snapshot()
    if not payload:
        return False
    message = str(payload.get("message") or "")
    updated_at = str(payload.get("updated_at") or "")
    if "ibgateway_installation_missing" not in message:
        return False
    try:
        observed = datetime.fromisoformat(updated_at)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return observed >= datetime.now(timezone.utc) - timedelta(seconds=GW_INSTALLATION_MISSING_SUPPRESS_SEC)
    except Exception:
        return True


def ensure_gateway_up() -> list[str]:
    """IB Gateway(포트 4002) 다운/로그아웃 감지 시 IBC로 자동 재시작(쿨다운+단일실행락). 거래불가 사태 근본대책.

    동시성: 5분 주기 watchdog 실행이 겹쳐도(launchd 중첩) 단 하나만 런처를 띄우도록 flock(LOCK_EX|LOCK_NB)으로
    보호한다. 쿨다운 타임스탬프는 spawn *직전*에 기록해(폭주/watchdog 사망 시에도 재시작 storm 방지),
    Popen 자체가 예외로 실패한 경우에만 쿨다운을 해제해 다음 주기 즉시 재시도(가용성 보호)한다.

    좀비 락 우려 없음(Red Team 2026-06-10 Infra 1): flock은 *advisory + fd 기반*이라 락을 잡은
    프로세스가 SIGKILL/크래시로 죽으면 커널이 fd를 닫으며 락을 자동 해제한다. PID 파일 락과 달리
    수동 stale 정리·PID-liveness *게이팅*은 불필요하다(오히려 stale-steal은 이중 실행 위험).
    단, finding의 취지(보유자 추적)를 반영해 락 파일에 pid/시각/host를 기록하고 경합 시 노출한다(관측성).
    """
    if _gateway_port_open():
        return []
    if IBGATEWAY_DISABLE_FLAG.exists():
        return ["⏸️ IB Gateway 비활성 플래그 감지 — 자동 재시작 건너뜀(의도적 중단 존중). 재개하려면 runtime/ibgateway_disabled 삭제"]

    GW_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(str(GW_LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            # 경합: flock은 *살아있는* 보유자에게만 잡혀 있다(죽으면 커널이 자동 해제). 즉 좀비 락이
            # 아니라 실제 동시 복구 중. 진단성 강화(Red Team Infra 1): 락 파일에 기록된 보유자 정보 노출.
            holder = ""
            try:
                holder = GW_LOCK_PATH.read_text().strip()
            except OSError:
                pass
            who = f" (보유: {holder})" if holder else ""
            return [f"⏳ 다른 watchdog가 이미 게이트웨이 복구 진행 중{who} — 중복 런처 실행 방지로 건너뜀"]

        # 락 획득 → 보유자 정보(pid/시각/host) 기록(관측성). flock이 배타성을 보장하므로
        # 이 내용은 진단용일 뿐 정합성 판단에는 쓰지 않는다(stale-steal 같은 위험 로직 없음).
        try:
            os.ftruncate(lock_fd, 0)
            os.lseek(lock_fd, 0, os.SEEK_SET)
            holder_info = f"pid={os.getpid()} since={datetime.now(timezone.utc).isoformat(timespec='seconds')} host={socket.gethostname()}"
            os.write(lock_fd, holder_info.encode())
            os.fsync(lock_fd)
        except OSError:
            pass

        # 락 획득 후 재확인: 그 사이 다른 프로세스가 복구했을 수 있음
        if _gateway_port_open():
            return []
        since = _gw_seconds_since_last_restart()
        if since is not None and since < GW_RESTART_MIN_INTERVAL_SEC:
            return [
                f"🚨 IB Gateway 다운(포트 4002 미응답) — 최근 자동 재시작 {int(since)}s 전(쿨다운 {GW_RESTART_MIN_INTERVAL_SEC}s). "
                "복구 미수렴 시 Mac Mini 화면공유로 수동 점검 필요"
            ]
        if _installation_missing_recently():
            return [
                "🚨 IB Gateway 다운 + 설치물/경로 불일치 지속 — 최근 진단상 `gatewaystartmacos.sh` 또는 `IB Gateway.app`를 찾지 못했습니다. "
                "반복 재시작은 중단하고 설치 위치/환경변수(IBC_LAUNCHER_PATH, IBGATEWAY_APP_PATH) 점검이 필요합니다."
            ]
        if not GATEWAY_START_SCRIPT.exists():
            return [f"🚨 IB Gateway 다운 + 재시작 스크립트 부재({GATEWAY_START_SCRIPT.name}) — 수동 재로그인 필요"]

        # 쿨다운은 spawn *직전* 기록(폭주 방지: watchdog가 spawn 직후 죽어도 storm 안 남).
        GW_COOLDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GW_COOLDOWN_PATH.write_text(str(datetime.now(timezone.utc).timestamp()))
        try:
            # start_ibgateway_ibc.sh가 IBC -inline → open 폴백 → 알림까지 캡슐화. watchdog는 트리거만.
            subprocess.Popen(
                ["/bin/bash", str(GATEWAY_START_SCRIPT)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            # spawn 자체가 실패 → 쿨다운 해제(다음 주기 즉시 재시도 — 가용성 보호)
            try:
                GW_COOLDOWN_PATH.unlink()
            except OSError:
                pass
            return [f"🚨 IB Gateway 자동 재시작 실패: {e} — 수동 재로그인 필요(Mac Mini 화면공유)"]

        return [
            "⚙️ 자가복구: IB Gateway 다운 감지 → start_ibgateway_ibc.sh 트리거. "
            "IBC 무인 로그인(-inline) 시도, 실패 시 open 폴백 + 수동 로그인 알림. 다음 주기 재확인"
        ]
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


# ── IBKR Gateway 체크 ────────────────────────────────────────────────────────

def _check_ibkr() -> list[str]:
    try:
        with socket.create_connection((IBKR_HOST, IBKR_PORT), timeout=5):
            print(f"[OK] IBKR Gateway {IBKR_HOST}:{IBKR_PORT} 연결 정상")
            return []
    except OSError:
        return [f"🚨 IBKR Gateway 연결 끊김 — {IBKR_HOST}:{IBKR_PORT} 미응답\n  → 수동 재로그인 필요 (Mac Mini 화면 공유 또는 VNC Viewer)"]


def _check_trading_runtime() -> list[str]:
    issues = []
    for path in TRADING_REQUIRED_FILES:
        if not path.exists():
            issues.append(f"트레이딩 런타임 파일 누락: {path.name}")
    try:
        alpaca = get_account_summary()
        if not alpaca.get("ok"):
            issues.append(f"Alpaca 인증/계좌 조회 실패: {alpaca.get('error')}")
    except Exception as e:
        issues.append(f"Alpaca 런타임 점검 실패: {e}")
    return issues


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Watchdog 실행")

    all_issues: list[str] = []
    all_issues.extend(_check_services())
    all_issues.extend(_check_db())
    all_issues.extend(ensure_trader_jobs_loaded())   # 자가복구: 트레이더 잡 자동 reload
    all_issues.extend(ensure_gateway_up())           # 자가복구: 게이트웨이 자동 재시작
    all_issues.extend(_check_trading_runtime())

    if all_issues:
        print(f"[ALERT] 이상 {len(all_issues)}건 감지")
        for i in all_issues:
            print(f"  - {i}")
        _send_alert(f"이상 {len(all_issues)}건 감지", all_issues)
    else:
        print("[OK] 파이프라인 정상")


if __name__ == "__main__":
    if "--ibkr-only" in sys.argv:
        print(f"[{datetime.now(timezone.utc).isoformat()}] IBKR Watchdog(자가복구) 실행")
        if not _ibkr_watchdog_allowed_on_this_host():
            print(
                "[SKIP] 이 호스트는 IBKR watchdog 실행 대상이 아님 "
                f"(host={socket.gethostname()}, allowed={sorted(ALLOWED_IBKR_WATCHDOG_HOSTS)})"
            )
            raise SystemExit(0)
        # 5분 주기 자가복구: ① 게이트웨이 다운 시 IBC 자동 재시작 ② 트레이더 잡 언로드 시 자동 reload
        issues = ensure_gateway_up() + ensure_trader_jobs_loaded()
        if issues:
            print(f"[ALERT/REMEDIATE] {len(issues)}건")
            for i in issues:
                print(f"  - {i}")
            _send_alert("자동매매 자가복구 동작", issues)
        else:
            print("[OK] IBKR Gateway·트레이더 잡 정상")
    else:
        main()
