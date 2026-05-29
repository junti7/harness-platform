"""
IBKR Paper Trading — Turtle Trading 자동화
Alpaca 페이퍼 트레이딩과 병행 운영. 비교 실적 측정용.

- 포트: 5001 (Mac Mini 기준, 5000은 ControlCenter 점유)
- 모드: 페이퍼 트레이딩 전용
- 유니버스: Harness 리서치 파이프라인 선정 종목 (글로벌 포함)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── 설정 ──────────────────────────────────────────────────────────────────────

IBKR_BASE = os.getenv("IBKR_CP_API_BASE_URL", "https://localhost:5001/v1/api")
IBKR_VERIFY_TLS = False  # self-signed cert
LOG_PATH = ROOT / "docs/reports/ibkr_paper_trading_log.jsonl"
STATE_PATH = ROOT / "docs/reports/ibkr_paper_positions.json"

# Harness 리서치 유니버스 (글로벌 포함 — Alpaca 불가 종목 추가 가능)
# IBKR에서는 미국 주식 + 아래 추가 가능
UNIVERSE = os.getenv(
    "IBKR_PAPER_UNIVERSE",
    "NVDA,AVGO,TSM,MU,ANET,VRT,TER,CRWV,SYM,ISRG,ROK,"
    "CEG,VST,GEV,PWR"  # 전력 인프라 (향후 추가)
).split(",")

TURTLE_S1 = 20   # System 1 진입: 20일 최고가
TURTLE_S2 = 55   # System 2 진입: 55일 최고가
TURTLE_ATR = 20  # ATR 기간
TURTLE_STOP_MULT = 2.0
TURTLE_RISK_PCT = 0.01  # 계좌 1%

_SESSION = requests.Session()
_SESSION.verify = IBKR_VERIFY_TLS


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{IBKR_BASE}/{path.lstrip('/')}"
    r = _SESSION.get(url, params=params or {}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"IBKR {r.status_code}: {r.text[:200]}")
    return r.json()


def _post(path: str, body: dict) -> dict:
    url = f"{IBKR_BASE}/{path.lstrip('/')}"
    r = _SESSION.post(url, json=body, timeout=15)
    if not r.ok:
        raise RuntimeError(f"IBKR POST {r.status_code}: {r.text[:200]}")
    return r.json()


# ── 게이트웨이 상태 확인 ───────────────────────────────────────────────────────

def check_gateway() -> dict:
    try:
        data = _get("/iserver/auth/status")
        return {
            "ok": True,
            "authenticated": data.get("authenticated", False),
            "competing": data.get("competing", False),
            "connected": data.get("connected", False),
            "message": data.get("message", ""),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tickle() -> bool:
    """세션 keepalive. 주기적으로 호출 필요."""
    try:
        _post("/tickle", {})
        return True
    except Exception:
        return False


# ── 계좌 조회 ─────────────────────────────────────────────────────────────────

def get_account() -> dict:
    try:
        accounts = _get("/portfolio/accounts")
        # 페이퍼 트레이딩 계좌 선택
        paper = next((a for a in accounts if "paper" in str(a.get("id", "")).lower()), None)
        acct = paper or (accounts[0] if accounts else {})
        acct_id = acct.get("id", "")

        summary = _get(f"/portfolio/{acct_id}/summary")
        nav = summary.get("netliquidation", {}).get("amount", 0)
        cash = summary.get("totalcashvalue", {}).get("amount", 0)
        return {
            "ok": True,
            "account_id": acct_id,
            "net_liquidation": float(nav),
            "cash": float(cash),
            "is_paper": "paper" in str(acct_id).lower(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 종목 conid 조회 ──────────────────────────────────────────────────────────

def resolve_conid(symbol: str) -> int | None:
    """티커 → IBKR contract ID"""
    try:
        results = _get("/iserver/secdef/search", {"symbol": symbol, "secType": "STK"})
        if not results:
            return None
        # 미국 주식 우선
        for r in results:
            for cd in r.get("conids", []):
                if r.get("exchange", "") in ("NASDAQ", "NYSE", "ARCA", ""):
                    return int(cd)
        return int(results[0].get("conids", [0])[0]) if results[0].get("conids") else None
    except Exception:
        return None


# ── 가격 데이터 조회 (Turtle 신호 계산용) ──────────────────────────────────────

def get_market_data(conid: int) -> dict | None:
    """현재가 + 기본 시장 데이터"""
    try:
        data = _get("/iserver/marketdata/snapshot", {
            "conids": str(conid),
            "fields": "31,70,71,82,84,86"  # last, high52, low52, volume, bid, ask
        })
        if not data:
            return None
        item = data[0] if isinstance(data, list) else data
        return {
            "last": float(item.get("31", 0) or 0),
            "high52": float(item.get("70", 0) or 0),
            "low52": float(item.get("71", 0) or 0),
        }
    except Exception:
        return None


# ── 포지션 조회 ──────────────────────────────────────────────────────────────

def get_positions(account_id: str) -> list[dict]:
    try:
        data = _get(f"/portfolio/{account_id}/positions/0")
        positions = []
        for p in (data if isinstance(data, list) else []):
            positions.append({
                "conid": p.get("conid"),
                "symbol": p.get("ticker", p.get("contractDesc", "")),
                "qty": float(p.get("position", 0)),
                "avg_cost": float(p.get("avgCost", 0)),
                "market_value": float(p.get("mktValue", 0)),
                "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
            })
        return positions
    except Exception:
        return []


# ── 주문 실행 ────────────────────────────────────────────────────────────────

def place_order(account_id: str, conid: int, side: str, qty: int, dry_run: bool = True) -> dict:
    if dry_run:
        return {"status": "dry_run", "conid": conid, "side": side, "qty": qty}
    try:
        body = {
            "orders": [{
                "conid": conid,
                "secType": f"{conid}:STK",
                "orderType": "MKT",
                "side": side.upper(),  # BUY / SELL
                "quantity": qty,
                "tif": "DAY",
            }]
        }
        result = _post(f"/iserver/account/{account_id}/orders", body)
        # 확인 메시지가 있으면 재전송
        if isinstance(result, list) and result and result[0].get("messageIds"):
            confirm_body = {"confirmed": True}
            result = _post(f"/iserver/account/{account_id}/orders", {
                **body, "confirmed": True
            })
        return {"status": "submitted", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── 상태 파일 ────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"positions": {}, "last_run": None, "baseline": None}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def log_entry(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 메인 ──────────────────────────────────────────────────────────────────────

def run(execute: bool = False) -> None:
    dry_run = not execute

    print("=" * 60)
    print(f"IBKR Paper Trader — {'DRY RUN' if dry_run else '*** EXECUTE ***'}")
    print(f"실행시각: {now_iso()}")
    print("=" * 60)

    # 1. 게이트웨이 상태 확인
    gw = check_gateway()
    if not gw.get("ok"):
        print(f"[ERROR] IB Gateway 연결 실패: {gw.get('error')}")
        print("  → start_ibgateway.sh 실행 후 브라우저 2FA 로그인 필요")
        return
    if not gw.get("authenticated"):
        print(f"[ERROR] 인증 필요: {gw.get('message')}")
        print("  → https://localhost:5001 접속 후 IBKR 계정으로 로그인")
        return
    print(f"Gateway: 인증됨 | 연결: {gw.get('connected')} | 경쟁: {gw.get('competing')}")

    # 2. 계좌 조회
    acct = get_account()
    if not acct.get("ok"):
        print(f"[ERROR] 계좌 조회 실패: {acct.get('error')}")
        return
    account_id = acct["account_id"]
    nav = acct["net_liquidation"]
    print(f"계좌: {account_id} | NAV: ${nav:,.2f} | 현금: ${acct['cash']:,.2f}")
    if not acct.get("is_paper"):
        print("[WARNING] 페이퍼 트레이딩 계좌가 아닙니다! 실계좌 진행 중단.")
        return

    state = load_state()
    state.setdefault("positions", {})
    if not state.get("baseline"):
        state["baseline"] = {"nav": nav, "set_at": now_iso()}
        print(f"[베이스라인 설정] NAV ${nav:,.2f} @ {now_iso()}")

    # 3. 신호 스캔 (단순화 버전 — IBKR 마켓데이터 제한으로 직접 가격 히스토리 필요)
    print("\n── 신호 스캔 ──")
    print("※ IBKR 페이퍼 트레이딩은 실시간 마켓데이터 구독이 필요합니다.")
    print("  현재 구현: Gateway 연결 확인 + 계좌 조회 단계")
    print("  다음 단계: 마켓데이터 구독 후 Turtle 신호 계산 활성화")

    for sym in [s.strip() for s in UNIVERSE if s.strip()]:
        conid = resolve_conid(sym)
        if conid:
            md = get_market_data(conid)
            price = md.get("last", 0) if md else 0
            print(f"  {sym}: conid={conid} | ${price:.2f}")
        else:
            print(f"  {sym}: conid 조회 실패")

    # 세션 유지
    tickle()

    state["last_run"] = now_iso()
    save_state(state)

    print("\n" + "=" * 60)
    print(f"완료 | IBKR 페이퍼 트레이딩 Gateway 연결 확인")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBKR Paper Trader")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run(execute=args.execute)
