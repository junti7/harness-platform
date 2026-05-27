# Hand-off: Alpaca Paper Trading 자동화 구축 완료
**작성일:** 2026-05-25  
**작성자:** Claude Sonnet 4.6  
**세션 범위:** Alpaca 모의투자 자동화 전체 구축

---

## 1. 완료된 작업 목록

### 1-1. Alpaca API 연결 수정
- `.env`의 `ALPACA_SECRET_KEY` 잘린 값(34자) → 정상값(46자) 수정
- `ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2` (Paper 모드)

### 1-2. 신규 파일

| 파일 | 역할 |
|---|---|
| `scripts/alpaca_paper_trading.py` | Alpaca API 래퍼 + Turtle 신호 계산 + 대시보드 데이터 |
| `scripts/turtle_auto_trader.py` | 자동매매 파이프라인 (신호 스캔 → TurtleGate → 주문) |
| `scripts/setup_turtle_scheduler_mac_mini.sh` | Mac Mini launchd 설치 스크립트 (로컬용, 경로 하드코딩됨) |

### 1-3. 수정된 파일

| 파일 | 변경 내용 |
|---|---|
| `harness-os/backend/main.py` | `GET /api/paper-trading/dashboard`, `POST /api/paper-trading/run`, `POST /api/paper-trading/execute` 엔드포인트 추가 |
| `harness-os/frontend/src/components/AlpacaPaperMonitor.tsx` | 새 컴포넌트 (계좌 요약, KPI, 신호 테이블, 주문 내역, Dry-Run/Execute 버튼) |
| `harness-os/frontend/src/App.tsx` | Execution Throughput 카드 제거 → AlpacaPaperMonitor 삽입 |
| `harness-os/frontend/src/App.css` | Alpaca 섹션 스타일 추가 (signal badge, pnl cell, execute button, run-result box 등) |
| `harness-os/frontend/src/components/types.ts` | `AlpacaAccount`, `AlpacaPosition`, `TurtleSignal`, `AlpacaOrder`, `AlpacaAR018Kpi`, `AlpacaChartPoint`, `AlpacaPaperDashboard` 타입 추가 |
| `.env` | `PAPER_TRADING_AUTO_EXECUTE=false`, `PAPER_TRADING_UNIVERSE`, `PAPER_TRADING_MAX_POSITIONS` 추가 |
| `scripts/openclaw_codex_bridge.py` | `GOG_KEYRING_BACKEND` 항상 주입 (file 기본값) |

---

## 2. 현재 실행 상태

### Mac Mini launchd 스케줄
```
이름: com.harness.turtle-auto-trader
경로: /Users/juntaepark/Library/LaunchAgents/com.harness.turtle-auto-trader.plist
실행: 월~금 13:30 UTC = 22:30 KST = 09:30 EDT (NYSE 개장)
모드: --execute (실제 Paper 주문)
로그: docs/reports/turtle_trader_stdout.log / turtle_trader_stderr.log
```

### 현재 포지션 (2026-05-25 기준)
```json
{
  "SOXX": {
    "entry_ts": "2026-05-25T10:51:13+00:00",
    "system": "S2",
    "entry_price": 537.05,
    "atr": 19.64,
    "stop_loss": 497.77,
    "qty": 51,
    "side": "buy"
  }
}
```
- 주문 상태: `accepted` (주말 → 2026-05-27 화요일 개장 시 체결 예정)
- 주 5월 26일(월): 미국 현충일(Memorial Day) → 휴장

### 상태 파일
- `docs/reports/paper_trading_positions.json` — Turtle 진입 포지션 추적
- `docs/reports/paper_trading_log.jsonl` — 모든 진입/청산/스킵 이벤트 로그

---

## 3. 매매 로직 요약

### 유니버스
```
NVDA, SMH, SOXX, BOTZ, TSLA, PLTR, ROBO, QQQ
(Physical AI / 반도체 테마. env: PAPER_TRADING_UNIVERSE)
```

### 진입 조건 (Turtle Trading)
| 시스템 | 진입 | 청산 |
|---|---|---|
| S1 | 전일 종가 > 직전 20거래일 최고가 | 10거래일 최저가 이탈 |
| S2 | 전일 종가 > 직전 55거래일 최고가 | 20거래일 최저가 이탈 |

### TurtleGate (자동 검증 5항목)
1. 진입 신호 존재 (`breakout_long` 또는 `breakout_short`)
2. ATR > 0
3. 계좌 리스크 ≤ 1% (`risk_pct ≤ 0.01`)
4. 손절가 > 0
5. 청산 시스템 유효 (S1 또는 S2)

항목 6~7 (pre-mortem, cross-LLM legal)은 **실계좌 전환 시에만** 필요 (AR-018 조건 6, 7).

### 포지션 사이징
```
리스크 금액 = 계좌 가치 × 1%
주문 수량 = floor(리스크 금액 / (2 × ATR))
최대 동시 포지션 = 6개 (PAPER_TRADING_MAX_POSITIONS)
```

---

## 4. 기존 Physical AI 파이프라인 상태

- **스케줄:** 매일 KST 10:00 자동 실행 (`com.harness.pipeline`)
- **최근 실행 결과:**
  - 5/21: 수집 1121 → 정제 5 → 발행 0
  - 5/23: 수집 997 → 발행 0
  - 5/25: 수집 75 → 정제 5 → 발행 0
- **발행 0 이유:** `qa_clear` 없이 발행 보류 규칙 적용 중 (CLAUDE.md 정책)
- **파이프라인과 매매의 연결:** 현재 없음. 뉴스 파이프라인은 Substack 발행용, 매매는 순수 가격 기반. 향후 실계좌 전환 시 "유니버스 필터링 신호"로 연결 검토 가능.

---

## 5. AR-018 조건 현황

| 조건 | 내용 | 상태 |
|---|---|---|
| 1 | IBKR 계좌 구조 이해 | ✅ |
| 2 | 한국은행 자문 + 외국환 거래 법률 확인 | ⏳ **대기 중** (CEO가 결과 통지 예정) |
| 3 | Turtle Trading 원칙 문서화 | ✅ |
| 4 | Paper Trading 자동화 구축 | ✅ **이번 세션 완료** |
| 5 | 8주 Paper Trading 선행 운영 | 🏃 **시작됨** (2026-05-25~) |
| 6 | Pre-Mortem 작성 | ⏳ 조건5 완료 후 |
| 7 | Claude+Gemini+Codex cross-LLM legal review | ⏳ 조건2 완료 후 |

---

## 6. 다음 작업 목록

### 즉시 필요
- [ ] 2026-05-27 화요일: SOXX 주문 체결 확인 (Alpaca 대시보드 또는 `GET /api/paper-trading/dashboard`)
- [x] Mac Mini에도 `docs/reports/paper_trading_positions.json` 동기화 확인
  - 2026-05-25 Codex 확인 및 조치 완료.
  - 로컬 최신 SOXX 추적 상태를 Mac Mini `/Users/juntaepark/projects/harness-platform/docs/reports/`로 동기화.
  - Mac Mini 원격 dry-run 결과: SOXX는 `already_tracked`로 스킵, 신규 진입 0건.
  - 중복 주문 방지를 위해 `scripts/turtle_auto_trader.py`의 `should_enter()`에 `state["turtle_positions"]` 기존 추적 종목 차단 조건 추가.

### 단기 (1~2주)
- [ ] Paper Trading 8주 운영 중 매주 KPI 리뷰 (AR-018 조건5 진행 상황)
- [ ] 한국은행 자문 결과 수신 후 AR-018 조건2 처리

### 중기 (조건5 완료 후)
- [ ] AR-018 조건6: Pre-Mortem 작성 (IBKR 실계좌 전환용)
- [ ] AR-018 조건7: cross-LLM legal review (Claude + Gemini + Codex)
- [ ] IBKR 실계좌 Turtle Trading 이전

### 아키텍처 개선 검토 (실계좌 전환 시)
- [ ] 뉴스 파이프라인 → 유니버스 필터링 신호 연결 (기사 감정/빈도 기반)
- [ ] 일봉 데이터를 장 마감 후(~23:00 KST) 업데이트하도록 스케줄 조정 (현재 09:30 EDT = 22:30 KST 장 개장 직전)

---

## 7. 실행 명령어 참조

```bash
# 드라이런 (로컬)
cd /Users/juntae.park/projects/harness-platform
.venv/bin/python scripts/turtle_auto_trader.py

# 실제 실행 (로컬)
.venv/bin/python scripts/turtle_auto_trader.py --execute

# 대시보드 API 테스트
SECRET="jcP_dE8nAITLjFGe0qmjN34V1g46AWB9Vf4unnz9Bz4"
curl -s -X POST http://127.0.0.1:8000/api/paper-trading/run -H "X-Harness-Secret: $SECRET"

# Mac Mini 원격 드라이런
ssh juntaepark@192.168.0.203 "cd /Users/juntaepark/projects/harness-platform && .venv/bin/python scripts/turtle_auto_trader.py"

# Mac Mini 스케줄 상태 확인
ssh juntaepark@192.168.0.203 "launchctl list | grep turtle"
```

---

## 8. 주의사항

- `PAPER_TRADING_AUTO_EXECUTE=false` → 로컬 기본값. `--execute` 플래그 또는 env=true 로 override.
- Mac Mini launchd는 `PAPER_TRADING_AUTO_EXECUTE=true`를 EnvironmentVariables에서 주입.
- `paper_trading_positions.json`이 삭제되면 손절 관리 불가 → 절대 삭제 금지.
- Alpaca Paper 계좌 ID: `PA3P9HKZG6LL`
- 실계좌 전환 전 `ALPACA_BASE_URL`을 `https://api.alpaca.markets/v2`로 변경 필요.
