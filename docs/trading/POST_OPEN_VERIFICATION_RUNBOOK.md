# 장 개장 후 자동투자 확인 절차

목적:
- `Alpaca`, `IBKR`가 reset 이후 계획대로 복구됐는지 확인
- `flat -> dry-run -> execute 재개` 순서를 강제
- 사람 판단 기준과 자동 판정 기준을 분리

## 1. 원칙

1. `flat` 전에는 execute 재개 금지
2. `flat` 직후에도 곧바로 execute 재개 금지
3. 최소 1거래일은 `dry-run only`
4. 아래 네 조건이 모두 맞아야만 execute 재개 검토
   - `trading_runtime_guard.json.ok = true`
   - `paper_trading_reset_status.json.flat = true`
   - `run_trading_cycle.py --broker alpaca` dry-run 성공
   - `run_trading_cycle.py --broker ibkr` dry-run 성공

## 2. 자동 점검 명령

```bash
.venv/bin/python scripts/run_post_open_verification.py
```

생성 파일:
- `docs/reports/post_open_verification.json`

판정 의미:
- `ready_for_execute = false`
  - 아직 execute 재개 금지
- `ready_for_execute = true`
  - 런타임/flat/dry-run 기준은 통과
  - 그래도 즉시 execute 재개하지 않고, 다음 거래일 dry-run only 1회 유지

## 3. 수동 확인 순서

### A. 런타임 가드

```bash
.venv/bin/python scripts/trading_runtime_guard.py
```

확인 항목:
- Alpaca 인증 성공
- IBKR gateway 연결 성공
- 아래 스크립트 존재
  - `scripts/run_trading_cycle.py`
  - `scripts/build_trading_universe.py`
  - `scripts/check_paper_books_flat.py`
  - `scripts/ibkr_tws_paper_trader.py`
- launchd 존재
  - `com.harness.turtle-auto-trader`
  - `com.harness.ibkr-auto-trader`
  - `com.harness.paper-reset-watch`

### B. flat 확인

```bash
.venv/bin/python scripts/check_paper_books_flat.py
```

확인 기준:
- `alpaca.flat = true`
- `ibkr.flat = true`
- `flat = true`
- `reset_pending = false`

`market_open = true`인데도 `flat = false`면:
- 미체결 청산 주문 상태를 먼저 봄
- 브로커 잔존 포지션을 우선 정리

### C. dry-run 검증

```bash
.venv/bin/python scripts/run_trading_cycle.py --broker alpaca
.venv/bin/python scripts/run_trading_cycle.py --broker ibkr
```

확인 기준:
- return code `0`
- `paper_trading_reset_pending` block 아님
- 신규 주문 없이 스캔/신호 계산/유니버스 빌드가 정상 완료

## 4. Harness OS 확인 위치

- `http://100.97.175.44:8000/`
- `트레이딩 오퍼레이션`
- 확인 카드:
  - `Paper Reset 상태`
  - `Alpaca 주문/포지션 수`
  - `IBKR 주문/포지션 수`

## 5. execute 재개 조건

아래가 모두 만족될 때만 수동으로 다음 단계 검토:

1. `post_open_verification.json.ready_for_execute = true`
2. 최소 1거래일 dry-run only 완료
3. 브로커 실제 book과 내부 상태 파일 정합성 확인
4. 대표가 execute 재개를 명시적으로 승인

## 6. 금지

- `flat = false` 상태에서 launchctl kickstart로 auto trader 강제 실행
- dry-run 없이 execute 재개
- 기존 잔존 포지션을 임의로 strategy state에 억지 동기화
- `reset_pending`을 수동으로 false로 바꾸고 우회 실행
