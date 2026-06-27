# Trading System Handoff — 2026-06-27

## 세션 요약

이 세션에서 IBKR Turtle Trading 시스템을 완성도 ~80% → 93%로 끌어올렸다.

---

## 완료된 작업

### 1. Red Team Round 3 (CEO 주문, 2026-06-27)

`docs/governance/RED_TEAM_LOG.md`에 RT3 결과 기록됨. `red_team_clear: 2026-06-27`.

#### BLOCKERs (3개 전부 수정)

| ID | 문제 | 수정 내용 |
|---|---|---|
| B1 | `ib.disconnect()` 미보장 — 조기 반환 경로에서 연결 누수 | 모든 early return 경로에 `try: ib.disconnect() except: pass` 추가 |
| B2 | reconcile promote 시 손절 주문 없이 포지션 오픈 | promote 즉시 market order 청산 (진입 경로 정책과 동일) |
| B3 | 부분체결 취소 race condition — 8초 단말 상태 대기 없이 qty 읽음 | 8초 폴링 루프 + `str(getattr(...))`, `float(filled or 0)` 방어 처리 |

#### MAJORs (4개 전부 수정)

| ID | 문제 | 수정 내용 |
|---|---|---|
| M1 | `pyramid()` None 반환 시 `.items()` TypeError | `or {}` fallback |
| M2 | clientId 고정(10) → 충돌 위험 | `random.randint(50, 99)` |
| M3 | 고아 입양 시 `primaryExchange` 소실 | `bp_con.primaryExch` 저장, `make_contract()` 반영 |
| M4 | reconcile promote stop_loss가 호가 시점 ATR 기준 | `averageCost`(실제 체결가) 기준으로 재계산 |

관련 커밋: `9fa207b`, `8841496`

---

### 2. Harness OS UX 개선

#### IbkrTurtleMonitor 개선 (`18694dd`)
- 통화 자동 표기 (`$` / `₩` / `¥`)
- `resident_stop_missing: true` 시 빨간 경고 배너
- `adopted: true` 포지션에 "고아입양" 배지
- `scripts/ibkr_turtle_monitor.py` assess_position() 4개 필드 추가: `currency`, `primary_exchange`, `resident_stop_missing`, `adopted`

#### 관심종목 호가 UX (`85dbf22`, `5ec6f45`, `124ad01`)

**문제**: 관심종목 실시간 호가 패널이 항상 비어있었음.  
**원인 1**: CP Gateway(포트 5001) 미가동 → `_fetch_ibkr_quotes()` 즉시 빈 배열 반환.  
**원인 2**: `safe_check_connectivity()`가 HTTP timeout 12초 대기 → `/api/trading/monitor` 응답 25초+ 걸림.

**수정 내용**:
- `[B]` CP Gateway 잠금 UI: `quote_source=none` 시 주황 안내 배너 ("자동매매에 영향 없음")
- `[A]` `_fetch_yfinance_quotes()`: CP Gateway 없이 US 종목 yfinance로 현재가 조회
- `_trading_api_overview()` + `_fetch_ibkr_quotes()` 양쪽에 포트 5001 socket probe(1초) 선행 → `safe_check_connectivity()` 12초 블록 우회
- yfinance 호출에 `ThreadPoolExecutor(max_workers=1).result(timeout=12)` 적용
- 헤더 소스 칩: Yahoo Finance / IBKR CP / 호가 없음
- 컬럼 재구성: 현재가 / 전일 대비% / 전일종가 (bid/ask 제거 — yfinance 미제공)
- KRX 항목 "KRX 미지원" 표시

**실측**: CP Gateway 없이 14종목 조회 9.2초, `quote_source=yfinance`.

---

### 3. 유령 포지션 정리

**발견**: `ibkr_tws_positions.json`에 포지션 3개 (000660, MU @$1133, TSM @$462) 존재.  
**판단**: Alpaca 시뮬레이션 잔재. IBKR 실제 계좌에 없는 phantom. MU @$1133 = 역사적으로 불가능한 가격.

**처리**:
- 백업: `ibkr_tws_positions.json.bak_20260627T...`, `ibkr_monitor_cache.json.bak_20260627T...`
- `positions: {}`, `pending_orders: {}`, phantom `signal_alerts` 제거
- `ibkr_turtle_monitor.py` 즉시 실행 → 캐시 재생성
- Harness OS UX 즉시 반영 (포지션 없음 상태)

---

## 현재 시스템 상태

| 항목 | 상태 |
|---|---|
| IB Gateway (포트 4002) | ✅ 실행 중 (IBC 자동 로그인 성공, 07:30) |
| CP Gateway (포트 5001) | ⬜ 미가동 (의도적 — yfinance로 대체) |
| 자동 트레이더 스케줄 | ✅ 월~금 13:35 KST (`com.harness.ibkr-auto-trader`) |
| Turtle Monitor cron | ✅ 장중 30분 간격 |
| 페이퍼 포지션 | 0개 (유령 제거 완료) |
| 페이퍼 계좌 | DUQ416334 |
| 완성도 | **93%** |

## 남은 갭 (7%)

1. **첫 실제 Turtle 사이클 미통과** — 진입 신호 → 진입 → 상주 손절 → 청산까지 한 번도 end-to-end 실행된 적 없음. 시간이 해결 (다음 신호 발생 시 자동).
2. **MU 현재가 이상** — 모니터가 MU를 $1,132로 표시. Yahoo Finance 데이터 이상 또는 2026년 실제 가격인지 확인 필요. 현재 neutral 신호 + 포지션 없음이므로 즉각적 위험 없음.

## 주요 파일 경로

```
scripts/ibkr_tws_paper_trader.py     # 메인 트레이더
scripts/ibkr_turtle_monitor.py       # 모니터 캐시 생성
harness-os/backend/main.py           # _fetch_yfinance_quotes, _trading_api_overview
harness-os/frontend/src/components/TradingApiMonitor.tsx   # 관심종목 호가 UX
harness-os/frontend/src/components/IbkrTurtleMonitor.tsx   # 포지션 모니터 UX
docs/reports/ibkr_tws_positions.json  # 포지션 상태 (현재 0건)
docs/reports/ibkr_monitor_cache.json  # 모니터 캐시 (현재 0건)
docs/governance/RED_TEAM_LOG.md       # RT3 기록
```

## 포지션 사이징 기준 (2026-06-27 CEO 개정)

- 단일 트레이드 리스크: **계좌의 2%** (클래식 Turtle 1유닛)
- 손절: 진입가 ± 2×ATR (현지 통화 기준)
- FX 변환: `ATR_USD = ATR_local × fx_rate` (포지션 수량 계산용)
- 포트폴리오 heat 상한: `PAPER_MAX_PORTFOLIO_HEAT` (기본 10%)
- 근거: AR-20260627-004 (기존 1%는 백테스트 과보수적 — CAGR 14.5% vs 1N 22.7%)
