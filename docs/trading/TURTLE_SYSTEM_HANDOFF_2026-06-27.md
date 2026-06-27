# Turtle 자동매매 시스템 핸드오프 — 2026-06-27

## 세션 요약

Alpaca 페이퍼 계좌 -5.76% 원인 진단 → Red Team(CEO 주문, Codex+Copilot) → P0/P1/사이징/피라미딩/분산/B1 전면 구현 완료.  
**다음 세션 작업**: Phase B2 — IBKR 트레이더를 `core/turtle_strategy.py`에 연결 (IB Gateway 연결 필수).

---

## 1. 진단 결과 요약

### 실제 포지션 (2026-06-27 브로커 진실)
| 종목 | 수량 | 평단가 | 손절가(교정) |
|------|------|--------|-------------|
| VRT  | 13주 | $326.29 | $284.50 |
| MU   | 13주 | $1188.39 | $990.67 |
| ASX  | 62주 | $40.51 | $35.34 |

**핵심 발견**: state 파일 진입가가 브로커 평단과 불일치(F5). VRT는 state $358.37 → 잘못된 손절 $321.24로 **오청산 직전**이었음.

### F1-F6 구조적 결함 (Red Team r1: 2-of-2 BLOCK)
| 코드 | 결함 | 심각도 |
|------|------|--------|
| F1 | 추세필터 없음 — 하락 중에도 진입 | P1 |
| F2 | 상관 한도 없음 — AI 매크로 단일 베팅 | P1 |
| F3 | 2N 사이징(보수적) — 백테스트로 1N 확정 | P1 |
| F4 | 체결≠제출 — 부분체결·거부 방치 | P0 |
| F5 | state 비원자화 멀티-writer → 진입가 불일치 | P0 |
| F6 | 손절 비상주화 — ATR 재계산 흔들림 | P0 |

---

## 2. 완료 작업 전체

### P0 — 구조 안전 (커밋 bb841ad)
**파일**: `scripts/turtle_auto_trader.py`

- `wait_for_fill()`: 주문 제출 후 터미널 상태(filled/rejected/cancelled)까지 폴링. 미체결 시 포지션 기록 안 함.
- **상주손절(resident stop)**: 체결 직후 브로커에 gtc stop 주문 즉시 발행. Gap-down 보호.
- `reconcile_positions()`: 브로커에 있고 state엔 없는 고아 포지션 입양 + 상주손절 소급. 브로커에 없고 state엔 있는 유령 정리.
- `state_set_position()` / `state_pop_position()` / `state_set_last_run()`: `update_json_atomic`(flock+재독+델타) 원자화. `save_state()` 통째쓰기 폐기.
- `manage_positions()`: tracked 손절가 고정(ATR 재계산 흔들림 제거), `cp <= stop`(등호 포함).

**테스트**: `tests/test_turtle_auto_trader_p0.py` — 8건 pass

### 1회성 reconcile (커밋 3dfe64e)
**파일**: `scripts/reconcile_paper_positions.py`

2026-06-27 Mac Mini `--execute` 적용:
- VRT: 진입가 $358.37→$326.29, 손절 $321.24→$284.50
- MU: 진입가 $1132.59→$1188.39, 손절 $965.16→$990.67
- ASX: 진입가 $43.60→$40.51, 손절 $38.42→$35.34
- 브로커 상주손절 3건 accepted

### P1 — 전략 보강 (커밋 b282512)
**파일**: `scripts/turtle_auto_trader.py`

- **F3 사이징(1N 확정)**: `shares = (계좌×1%) / ATR`. 실효 리스크 ~2%(2N 기준). `TURTLE_MAX_RISK_PCT=0.02`.
- **F2 상관 한도**: `EQUIVALENT_ETF_SETS`(SMH↔SOXX, BOTZ↔ROBO) 동시보유 금지. `CORR_GROUP` 그룹별 유닛 상한(`PAPER_MAX_CORR_UNITS` 기본 3).
- **F1 추세필터**: `passes_trend_filter()` — 100일 MA 위에서만 롱. 데이터 부족 시 fail-open.
- `portfolio_heat()`: 포지션 합산 리스크 ÷ 계좌. `PAPER_MAX_PORTFOLIO_HEAT=0.10` 초과 시 신규 진입 차단.

**테스트**: `tests/test_turtle_auto_trader_p1.py` — 13건 pass

### 사이징 거버넌스 개정 (AR-20260627-004)
백테스트 결과(IEX 2020-07~2026-06, 1487 bars):

| 시스템 | CAGR | MaxDD | MAR |
|--------|------|-------|-----|
| B&H SMH | 20.3% | -45.4% | 0.91 |
| 2N 사이징(구) | 14.5% | -20.5% | 0.71 |
| **1N 사이징(확정)** | **22.7%** | -24.4% | **0.93** |
| 1N + 피라미딩 | 32.9% | -36.8% | 0.90 |
| **1N + 피라미딩 + sleeve** | **36.4%** | -25.8% | **1.41** |

**CLAUDE.md + TURTLE_TRADING_PRINCIPLES.md 개정**: ≤1% → ≤2%(클래식 1유닛) + 포트폴리오 heat 상한.

### #2 피라미딩 (커밋 f5c9954, 롱 전용)
**파일**: `scripts/turtle_auto_trader.py`

- **숏 피라미딩 기각**: 백테스트 MAR 0.16(반도체 secular 불장 역행). **롱 전용 확정.**
- `pyramid_positions()`: ½N 유리 이동마다 유닛 추가(최대 `PAPER_MAX_UNITS`=4).
- 추가 시 전체 stop → 최근유닛-2N 상향 + 상주손절 교체 + 체결확인 + heat 연동.
- state에 `n_at_entry / last_unit_price / unit_count / risk_usd` 기록.

**테스트**: `tests/test_turtle_auto_trader_pyramid.py` — 7건 pass

### #1 분산 sleeve (커밋 b660e6f + c35f0bf)
**파일**: `scripts/turtle_auto_trader.py`

**측정 상관(vs SMH, 2024-2026 일간수익률)**:
- ROBO 0.78, QQQ 0.91, BOTZ 0.78, NVDA 0.81, VRT 0.72 — 전부 한 AI 매크로
- TLT +0.04, GLD -0.23, DBC +0.16, UUP +0.18 — **진짜 무상관**

추가 사항:
- `DIVERSIFIERS = ["TLT", "GLD", "DBC", "UUP"]` 유니버스 추가 (`PAPER_DIVERSIFY_ENABLED=true`)
- **상관그룹 재보정**: ROBO/QQQ/BOTZ→SEMI(leak 차단), GOOG/META→AIPLATFORM, COHR→SEMI, sleeve 각자 독립(BOND/GOLD/COMMOD/USD)
- **AI-SW 추가(SNOW/CRWD/DDOG) 기각**: MAR 1.41→1.05, 상관 ~0.45라 분산 악화

**테스트**: `tests/test_turtle_auto_trader_p1.py`에 신규 2건 추가

### Phase B1 — strategy core 추출 (커밋 edbeac0)
**파일**: `core/turtle_strategy.py`

브로커 중립 순수 전략 로직(주문/계좌/시세 호출 0):

| 함수 | 역할 |
|------|------|
| `compute_atr(bars, period)` | ATR 계산 |
| `signal_from_bars(symbol, bars)` | Donchian 돌파 신호 |
| `size_shares(account_value, atr)` | 1N 사이징 |
| `turtle_gate_check(signal, acct, max_risk_pct)` | 5항목 게이트 |
| `correlation_block(symbol, held, ...)` | 동등ETF+그룹 한도 |
| `portfolio_heat(positions, acct)` | 합산 heat |
| `trend_filter_ok(closes, price, ...)` | 추세필터 |
| `exit_signal(bars, system, side)` | 청산 신호 |
| `pyramid_decision(tracked, price, acct, ...)` | 피라미딩 결정 |

**검증**: `tests/test_turtle_strategy_core.py` — 12건 pass (직접 단위 + parity)  
**parity 보장**: `core.CORR_GROUP == t.CORR_GROUP`, `core ≡ turtle_auto_trader` 동치 검증.  
**Alpaca 트레이더 무수정** — 회귀 위험 0.

---

## 3. 전체 테스트 현황 (48 pass)

| 테스트 파일 | 건수 | 상태 |
|------------|------|------|
| `tests/test_turtle_auto_trader_p0.py` | 8 | ✅ |
| `tests/test_turtle_auto_trader_p1.py` | 13 | ✅ |
| `tests/test_turtle_auto_trader_pyramid.py` | 7 | ✅ |
| `tests/test_turtle_strategy_core.py` | 12 | ✅ |
| `tests/test_core_atomic_io.py` | 8 | ✅ |
| **합계** | **48** | **모두 pass** |

---

## 4. 주요 파일 변경 목록

```
scripts/turtle_auto_trader.py       — P0+P1+사이징+피라미딩+분산 전면 개정
scripts/reconcile_paper_positions.py — 1회성 state 교정 (이미 실행 완료)
scripts/backtest_turtle.py          — 백테스트 도구 (분석용, 프로덕션 미배포)
core/turtle_strategy.py             — 신규: 브로커 중립 전략 코어
core/atomic_io.py                   — update_json_atomic (기존)
tests/test_turtle_auto_trader_p0.py — P0 테스트
tests/test_turtle_auto_trader_p1.py — P1 테스트 (신규 2건 포함)
tests/test_turtle_auto_trader_pyramid.py — 피라미딩 테스트
tests/test_turtle_strategy_core.py  — B1 core 테스트
docs/trading/TURTLE_SYSTEM_DIAGNOSIS_2026-06-27.md
docs/governance/PRE_MORTEM_2026-06-27_turtle_paper_to_live.md
docs/governance/RED_TEAM_REQUEST_TURTLE_DIAGNOSIS_2026-06-27.md
docs/governance/RED_TEAM_LOG.md     — 2건 추가
docs/reports/ar_tracker.jsonl       — AR-20260627-001~004
CLAUDE.md                           — 사이징 ≤2% 개정 (2곳)
docs/trading/TURTLE_TRADING_PRINCIPLES.md — 사이징 개정 (3곳)
```

---

## 5. 프로덕션 유니버스 (Mac Mini 실행 중)

```
개별주: GOOG, NVDA, TSLA, SYM, META, AVGO, TSM, VRT, COHR, ASX, MU
sleeve: TLT, GLD, DBC, UUP
```

**스케줄**: `com.harness.turtle-auto-trader.plist` — 매주 월요일 13:30 KST (`--execute` 강제).

---

## 6. 다음 세션 — Phase B2 (IBKR 연결)

### 전제 조건
- [ ] Mac Mini IB Gateway 실행 확인: `python scripts/ibkr_runtime_status.py`
- [ ] gui/501 세션(Aqua) 활성 상태
- [ ] TWS paper account 로그인 완료

### B2 작업 목록 (`scripts/ibkr_tws_paper_trader.py`)

현재 IBKR 트레이더 현황:
- S2-only 신호 (`calc_turtle_signal()` 내장)
- 1N 사이징 우연 일치
- S1 신호 없음
- 추세필터 없음
- 상관 한도 없음
- heat cap 없음
- 피라미딩 없음
- 분산 sleeve 없음
- 체결 게이트 없음

**B2 교체 목록**:

1. `calc_turtle_signal()` → `core.signal_from_bars()` (IBKR bars 포맷 어댑터 필요)
2. 인라인 사이저 → `core.size_shares()` + `core.turtle_gate_check()`
3. `core.correlation_block()` 추가
4. `core.trend_filter_ok()` 추가
5. `core.pyramid_decision()` + IBKR 주문 실행 추가
6. `core.portfolio_heat()` + heat cap 추가
7. 분산 sleeve (TLT/GLD/DBC/UUP) 유니버스 추가
8. `wait_for_fill()` 체결 게이트 추가
9. **smoke test — IB Gateway 연결 상태에서 필수**

### B3
IBKR 전 사이클 통합 테스트.

### 주의사항
- B2는 **실자본 경로**. 블라인드 배포 금지.
- IBKR bars 포맷 = `{date, open, high, low, close, volume}` (Alpaca와 키 다름).
- 상주손절 = IBKR `orderType='STP'`, `tif='GTC'`.
- 실계좌 전환은 B2/B3 + `turtle_gate_clear` + `pre_mortem_approve` + CEO 승인 후.

---

## 7. AR 현황

| AR | 내용 | 상태 |
|----|------|------|
| AR-20260627-001 | Pre-Mortem 작성 | ✅ 완료 |
| AR-20260627-002 | 진단 리포트 작성 | ✅ 완료 |
| AR-20260627-003 | Cross-LLM Red Team | ✅ `red_team_block` (2-of-2) |
| AR-20260627-004 | 거버넌스 개정(사이징 2%) | ✅ 완료 |

---

## 8. 핵심 설계 결정 (변경 시 백테스트 재확인)

| 결정 | 값 | 근거 |
|------|-----|------|
| 사이징 | 1N (계좌×1%/ATR) | 백테스트 MAR 최고 |
| 단일 트레이드 한도 | ≤2% (실효 2N) | CEO 확정 |
| 포트폴리오 heat 상한 | 10% | `PAPER_MAX_PORTFOLIO_HEAT` |
| 피라미딩 | 롱 전용, ½N 트리거, 최대 4유닛 | 숏은 MAR 0.16으로 기각 |
| 분산 sleeve | TLT/GLD/DBC/UUP | 측정 무상관 유일 |
| AI-SW 추가(SNOW 등) | 기각 | MAR 1.41→1.05 |
| 숏 전략 | 기각 | MAR 0.93→0.16 |
| 추세필터 | 100일 MA, fail-open | `PAPER_TREND_MA_DAYS` |
| 상관 그룹 상한 | 3유닛/그룹 | `PAPER_MAX_CORR_UNITS` |

---

*작성: 2026-06-27 핸드오프 세션 | 커밋 범위: bb841ad ~ edbeac0*
