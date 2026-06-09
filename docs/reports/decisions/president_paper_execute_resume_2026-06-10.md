# President Decision — Paper Execute 거래 재개 결재

- 문서유형: President Decision Record (대표 결재 기록)
- 결재일: 2026-06-10
- 결재자: 대표(President/CEO)
- 상신/기록: 비서실장(Chief of Staff)
- correlation_id: `paper-execute-resume-20260610`
- 관련 AR: `ar_tracker.jsonl` → `AR-PAPER-EXEC-RESUME-20260610`

---

## 1. 결정

paper 리셋이 **Flat 완료**(Alpaca 0주문/0포지션 · IBKR 0주문/0포지션)된 상태에서,
**paper execute 거래를 즉시 재개**한다.

검증 잡(`run_post_open_verification.py`)이 권고한 "다음 거래일 dry-run only 1회 추가 소크"를
**대표 권한으로 생략하고 재개**한다.

- 결정값(decision): `approved`
- 대상(target): paper trading execute 재개 (Alpaca paper + IBKR paper)
- 성격: **운영 결정(operational resume)** — 실자본 집행(capital_action) 아님

## 2. 맥락

- 리셋 직후 상태: `paper_trading_reset_status.json` → `flat: true`.
  → `run_trading_cycle._reset_pending()`는 `reset_pending AND not flat`이므로 **이미 미차단**.
- 트레이더 launchd plist는 `PAPER_TRADING_AUTO_EXECUTE=true` (turtle / ibkr 양쪽).
- "dry-run only"는 검증 잡의 **권고 문구**였을 뿐 코드상 강제 차단이 아니었음.
- 양쪽 브로커 dry-run OK · runtime guard OK → `ready_for_execute=true` 도달 후 재개 판단.

## 3. 범위 — 이 결재가 승인하는 것 / 하지 않는 것

**승인함:**
- Alpaca paper / IBKR paper(4002) 계좌에서의 execute 모드 자동매매 재개.
- 종목별 Turtle 게이트를 통과한 진입·청산 주문의 paper 체결.

**승인하지 않음 (불변):**
- 실자본 집행 — `CAPITAL_ACTIONS_ENABLED=false`, **AR-018 red_team_block 유지**. 실돈은 움직이지 않는다.
- Turtle 5대 원칙 / `turtle_gate_*` 로직 변경 — 일절 손대지 않음.
- 단일 트레이드 계좌 리스크 1% 초과 — 금지 유지.

## 4. 가드레일 (재개 후에도 강제 유지)

- 진입은 **20/55일 브레이크아웃 + ATR + 손절(진입가±2×ATR) + 리스크≤1% + TurtleGate PASS** 전부 충족 시에만. 신호 없으면 execute여도 0건이 정상.
- 청산 신호(System1 10일 / System2 20일) 발생 시 지연 없이 청산.
- runtime guard / flat watcher / post-open verification 모니터링 계속 가동.
- 이상 징후(미체결 청산 누적, 게이트 우회, 리스크 초과) 발생 시 즉시 재차단.

## 5. 잔여 리스크 (인지·수용)

- (a) 권고된 1일 dry-run 소크 생략 → 재개 첫 거래일 runtime 불안정 가능성. 완화: post-open verification + 인시던트 알림 유지.
- (b) paper 체결은 실자본 성과를 보장하지 않음(슬리피지·체결 차이). 본 재개의 목적은 AR-018 청산/MDD 로직 실데이터 검증.

## 6. 집행 명령 (Mac Mini prod에서 실행)

```
ssh 100.97.175.44 'cd ~/projects/harness-platform && source .venv/bin/activate && \
  python scripts/run_trading_cycle.py --broker alpaca --execute && \
  python scripts/run_trading_cycle.py --broker ibkr --execute'
```

스케줄 자동 execute 유지 확인:
```
ssh 100.97.175.44 'launchctl list | grep -i "turtle-auto-trader\|ibkr-auto-trader"'
```

> 비서실장 주: 비서실 셸의 SSH 키 인증이 거부되어 prod 직접 집행 불가. 위 명령은 대표님이 실행한다.
> 집행 결과(체결/0건/게이트 사유)는 본 기록에 후속 첨부한다.

### 집행 로그 (확정)

**Alpaca paper execute** — 2026-06-10 08:30 KST, 대표가 대시보드 `Alpaca 가상 주문` 버튼(`POST /api/paper-trading/execute` = `turtle_auto_trader.py --execute`)으로 집행.
- 계좌 NAV $99,076.98 · 포지션 없음(flat) · **진입 0건**.
- 라이브 주문 확인: 오늘(06-10) 신규 주문 없음(최근 주문 = 06-08 리셋 청산 4건 filled). 전 종목 중립으로 20/55일 브레이크아웃 신호 부재 → 진입 미발생(정상).

**IBKR paper execute** — 2026-06-10 08:31 KST, 비서실장이 `ssh macmini` 복구 후 `run_trading_cycle.py --broker ibkr --execute`로 집행 (EXIT=0).
- 계좌 DUQ416334 · NAV $1,007,743.91 · 포지션 없음 · 유니버스 24종목 **전부 중립** · **진입 0건**.
- 예: NVDA −12.0%, TSM −4.9%, ROK −1.6% (모두 System2 고점 하회) → 브레이크아웃 진입 신호 없음.

**결론:** 양쪽 브로커 execute 재개·정상 작동 확인. 현 시점 진입 신호가 없어 0건이며, 이는 Turtle 규율(신호 없으면 진입 안 함)에 부합. 향후 거래일은 launchd 스케줄 잡(execute=true)이 자동 집행.

## 7. 서명

- 결재: 대표(President/CEO) — 2026-06-10
- 기록: 비서실장(Chief of Staff)
