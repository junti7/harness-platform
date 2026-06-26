"""1회성 reconcile — 페이퍼 보유 포지션 state를 브로커 ground-truth로 교정 + 상주손절 backfill.

배경(2026-06-27): Red Team red_team_block 후속 P0 배포 후, 프로덕션 state의 일부 포지션
진입가가 브로커 실제 평단과 불일치(F5 멀티-writer 잔재)했다. 예: VRT state 진입가 $358.37 vs
브로커 평단 $326.29 → 잘못된 진입가 기준의 손절선($321.24)이 멀쩡한 포지션을 오청산할 위험.

이 스크립트는 현재 브로커 보유 포지션 각각에 대해:
  1) 진입가를 **브로커 평단(avg_entry_price)**으로 교정
  2) 2N 손절선을 **현재 ATR**로 재산정(1회성 baseline 확정 — 이후 manage는 이 고정값 사용)
  3) 기존 상주손절 주문 취소 후 **교정가로 상주손절 재배치**(stop_order_id 백필)
  4) state를 update_json_atomic 으로 원자적 기록

대상: (state에 추적 중) ∪ (turtle 유니버스) ∩ (브로커 실보유). 수동·비유니버스·미추적 포지션은 건드리지 않는다.

실행:
  python scripts/reconcile_paper_positions.py            # dry-run (조회·계산만, 주문/기록 없음)
  python scripts/reconcile_paper_positions.py --execute  # 실제 교정 + 상주손절 배치
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.turtle_auto_trader import (
    UNIVERSE, STOP_TIF, now_iso, load_state,
    state_set_position, cancel_order, _alpaca_post, log_entry,
)
from scripts.alpaca_paper_trading import (
    get_positions, _get_bars, _calc_atr,
    TURTLE_STOP_MULT, TURTLE_ATR_PERIOD,
)


def reconcile(execute: bool = False) -> dict:
    dry_run = not execute
    state = load_state()
    tracked = state.get("turtle_positions", {})
    tracked_syms = set(tracked.keys())
    universe_set = {s.strip().upper() for s in UNIVERSE}

    positions = get_positions()
    broker = {p["symbol"]: p for p in positions if "error" not in p}

    print("=" * 64)
    print(f"Paper Position Reconcile — {'DRY RUN' if dry_run else '*** EXECUTE ***'}")
    print(f"실행시각: {now_iso()}")
    print("=" * 64)

    results = []
    for sym, pos in broker.items():
        in_scope = (sym in tracked_syms) or (sym.upper() in universe_set)
        if not in_scope:
            print(f"\n  {sym}: 범위 밖(수동/비유니버스·미추적) — 건너뜀")
            continue

        broker_entry = float(pos.get("entry_price") or 0)
        cur = float(pos.get("current_price") or 0)
        qty = int(pos.get("qty") or 0)
        bars = _get_bars(sym, days=TURTLE_ATR_PERIOD + 5)
        atr = _calc_atr(bars, TURTLE_ATR_PERIOD) if len(bars) >= TURTLE_ATR_PERIOD + 1 else 0
        stop = round(broker_entry - TURTLE_STOP_MULT * atr, 2) if atr > 0 else None

        old = tracked.get(sym, {})
        old_entry = old.get("entry_price")
        old_stop = old.get("stop_loss")
        system = old.get("system", "S2")
        old_stop_id = old.get("stop_order_id", "")
        already_below = (stop is not None and cur <= stop)

        print(f"\n  {sym}: qty={qty}")
        print(f"     진입가  state ${old_entry} → 브로커 ${broker_entry:.2f}")
        print(f"     손절선  state ${old_stop} → 교정 ${stop} (ATR={atr:.2f}, 2N)")
        print(f"     현재가  ${cur:.2f}  →  {'⚠ 교정손절 아래(보유불가, 청산필요)' if already_below else '교정손절 위(보유 OK)'}")

        entry_rec = {
            "entry_ts": old.get("entry_ts") or now_iso(),
            "system": system,
            "entry_price": round(broker_entry, 2),
            "atr": round(atr, 4),
            "stop_loss": stop,
            "qty": qty,
            "side": "buy",
            "stop_order_id": old_stop_id,
            "reconciled": True,
        }

        action = {
            "ts": now_iso(), "action": "reconcile", "symbol": sym,
            "old_entry": old_entry, "broker_entry": round(broker_entry, 2),
            "old_stop": old_stop, "new_stop": stop, "current_price": cur,
            "already_below_stop": already_below, "dry_run": dry_run,
        }

        if not dry_run:
            # 1) 기존 상주손절 취소
            cancel_order(old_stop_id)
            new_stop_id = ""
            # 2) 상주손절 재배치 — 단, 이미 교정손절 아래면 stop 주문이 즉시발동/거절되므로
            #    상주손절을 걸지 않는다(다음 execute 잡의 manage_positions가 시장가 청산 처리).
            if stop and stop > 0 and not already_below:
                try:
                    so = _alpaca_post("/orders", {
                        "symbol": sym, "qty": str(qty), "side": "sell",
                        "type": "stop", "stop_price": str(stop), "time_in_force": STOP_TIF,
                    })
                    new_stop_id = so.get("id", "")
                except Exception as e:
                    action["stop_order_error"] = str(e)
            entry_rec["stop_order_id"] = new_stop_id
            action["new_stop_order_id"] = new_stop_id[:16]
            # 3) state 원자적 교정
            state_set_position(sym, entry_rec)
            print(f"     → 상주손절 {'배치 OK ('+new_stop_id[:12]+')' if new_stop_id else '미배치(청산 대상이거나 실패)'}")
        else:
            print("     → DRY-RUN (기록·주문 없음)")

        log_entry(action)
        results.append(action)

    print("\n" + "=" * 64)
    held = [r["symbol"] for r in results if not r["already_below_stop"]]
    to_exit = [r["symbol"] for r in results if r["already_below_stop"]]
    print(f"완료 | 교정 {len(results)}건 | 보유유지 {held or '없음'} | 청산필요 {to_exit or '없음'}")
    print("=" * 64)
    return {"status": "ok", "dry_run": dry_run, "reconciled": len(results),
            "held": held, "to_exit": to_exit}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paper position reconcile + resident stop backfill")
    parser.add_argument("--execute", action="store_true", help="실제 교정·상주손절 배치(미지정 시 dry-run)")
    args = parser.parse_args()
    res = reconcile(execute=args.execute)
    sys.exit(0 if res.get("status") == "ok" else 1)
