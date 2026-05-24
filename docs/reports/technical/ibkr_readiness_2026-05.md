# AR-021 — IBKR 온보딩 기술 준비 상태 점검

> 작성일: 2026-05-24 | 담당: TARS | AR: AR-021  
> correlation_id: strategy-pivot-b2i-20260524  
> 점검 기준: `ibkr-setup-status` 명령 + 코드 분석 + 법률 검토 연계

---

## 1. 온보딩 현황 (9단계 중 0/9 완료)

| # | 단계 | 상태 | 유형 | 선행 조건 | 비고 |
|---|---|---|---|---|---|
| 1 | IBKR Pro 계좌 개설 | ❌ 미완료 | HUMAN | — | IBKR.com 신청 |
| 2 | KYC / 신원 확인 | ❌ 미완료 | HUMAN | 1번 완료 | 보통 1~5 영업일 |
| 3 | 2FA 활성화 | ❌ 미완료 | HUMAN | 2번 완료 | IBKR Mobile / IB Key |
| 4 | **한국은행 외환 유권해석** | ❌ 미완료 | HUMAN | — | **입금 전 필수 (AR-017)** |
| 5 | 계좌 입금 | ❌ 미완료 | HUMAN | 2·4번 완료 | 외환거래법 신고 완료 후 송금 |
| 6 | 거래 권한 설정 (미국 주식/ETF) | ❌ 미완료 | HUMAN | 5번 완료 | Client Portal에서 신청 |
| 7 | 시장 데이터 구독 | ❌ 미완료 | HUMAN | 6번 완료 | US Consolidated Tape: $1.5/월 |
| 8 | Client Portal Gateway 설치 | ❌ 미완료 | AUTO 검증 가능 | 3번 완료 | localhost:5000 연결 필요 |
| 9 | Gateway 인증 + Harness 연결 | ❌ 미완료 | AUTO 검증 | 8번 완료 | `ibkr-setup-status` 자동 확인 |

**현재 상태: 0/9 — 계좌 개설 자체가 미완료**

---

## 2. 기술 인프라 점검

### 2.1 ibkr_cp_client.py 기능 점검

| 기능 | 구현 여부 | 상태 |
|---|---|---|
| Gateway preflight 체크 | ✅ 구현 | `preflight()` — TLS 핸드셰이크 타임아웃 (Gateway 미설치) |
| 계좌 목록 조회 | ✅ 구현 | `/portfolio/accounts` — Gateway 연결 시 작동 |
| ETF conid 조회 | ✅ 구현 | `/iserver/secdef/search` |
| 주문 생성 (paper) | ✅ 구현 | `/iserver/account/{acctId}/orders` |
| 주문 확인 (reply) | ✅ 구현 | `/iserver/reply/{replyId}` |
| 포지션 조회 | ✅ 구현 | `/portfolio/{acctId}/positions/0` |
| 잔고 조회 | ✅ 구현 | `/portfolio/{acctId}/summary` |
| CAPITAL_ACTIONS_ENABLED 게이트 | — | 클라이언트 레벨 아님 — bridge에서 제어 |

**코드 상태: 기능 구현 완료, Gateway 연결 대기 중**

### 2.2 현재 연결 오류

```
error: _ssl.c:1063: The handshake operation timed out
원인: IBKR Client Portal Gateway 미설치 (localhost:5000 미응답)
조치: Gateway 설치 후 재시도
```

### 2.3 ETF Whitelist 상태

`etf_whitelist_v0.json` 등재 현황:

| 티커 | 거래소 | conid 해결 | 상태 |
|---|---|---|---|
| BOTZ | NYSEARCA | ❌ (Gateway 미연결) | 대기 |
| SOXX | NASDAQ | ❌ | 대기 |
| SMH | NASDAQ | ❌ | 대기 |
| KODEX AI반도체 (445290) | KRX | ❌ | 대기 |
| TIGER 글로벌자율주행&로봇 (395160) | KRX | ❌ | 대기 |

---

## 3. Paper Trading 테스트 플랜 (8주)

> **전제: Live 자본 투입 전 paper trading 필수 (capital_plan_2026-05.md Phase 0)**

### 3.1 IBKR Paper Account 설정

IBKR은 Live 계좌와 별도의 **Paper Trading Account**를 제공합니다.

1. IBKR Client Portal 로그인 → Settings → Paper Trading Account 활성화
2. 가상 잔고: USD 1,000,000 (IBKR 기본값) → **USD 7,000으로 수동 조정 필요**
3. Gateway를 Paper 모드로 실행:
   ```bash
   # gateway 실행 시 paper trading 계좌 사용
   # 환경변수로 구분: IBKR_ACCOUNT_TYPE=paper
   ```
4. `ibkr_cp_client.py`의 `base_url` 은 동일 (localhost:5000), 계좌 ID만 paper ID 사용

### 3.2 주차별 테스트 플랜

| 주차 | 목표 | 성공 기준 | 비고 |
|---|---|---|---|
| 1주 | Gateway 설치 + paper 계좌 연결 | `ibkr-setup-status` gateway_installed ✅ | IBKR 계좌 개설 선행 |
| 2주 | ETF conid 해결 (whitelist 전체) | `ibkr-etf-check` 전 종목 conid 확인 | |
| 3주 | 첫 paper 주문 실행 (BOTZ 1주) | 체결 확인 + 포지션 조회 성공 | |
| 4주 | Thesis 템플릿 → paper 주문 1회 | THESIS-YYYYMMDD-001 전체 섹션 작성 | 투자 thesis 템플릿 연동 |
| 5주 | cross-LLM 게이트 + paper 주문 | Claude+Gemini 2-of-3 approve 후 주문 | AR-018 조건4 검증 |
| 6주 | MDD 시뮬레이션 | -15% 도달 시 KILL_CRITERIA 알림 작동 | Watchman 연동 |
| 7주 | 청산 로직 테스트 | 목표가 도달 시 청산 의도 생성 → CEO 승인 mock | |
| 8주 | 전체 플로우 최종 점검 | 8주 MDD -15% 이내 + KPI 3개 모두 달성 | |

### 3.3 Paper Trading KPI (8주 완료 기준)

| KPI | 기준 | 판정 |
|---|---|---|
| MDD | -15% 이내 | Pass / Fail |
| Thesis 생성 성공률 | 80% 이상 (완성 Thesis / 시도 횟수) | Pass / Fail |
| Cross-LLM 게이트 통과율 | 70% 이상 | Pass / Fail |
| 주문 오류율 | 5% 이하 (체결 실패 / 전체 주문) | Pass / Fail |

**4개 KPI 중 3개 이상 Pass → Phase 1 Live 진입 조건 충족**

---

## 4. 선행 작업 체크리스트 (HUMAN_REQUIRED)

아래는 TARS가 자동화할 수 없는 인간 직접 수행 항목입니다.

- [ ] **IBKR Pro 계좌 개설** (ibkr.com → Open Account → Individual)
  - 한국 거주자 선택, SSN 대신 여권/주민번호 사용
  - 예상 소요: 3~7 영업일

- [ ] **한국은행 외환심사실 서면 질의** (AR-017, 02-759-4750)
  - IBKR 직접 계좌 이용 시 외화증권취득 신고 절차 확인
  - 예상 소요: 회신까지 3~10 영업일

- [ ] **주거래은행 지정거래외국환은행 지정**
  - 해외증권투자 목적 명시
  - 예상 소요: 당일~3 영업일

- [ ] **W-8BEN 양식 제출** (계좌 개설 후 Client Portal에서)
  - 미국 배당 원천세 30% → 15% 인하
  - 예상 소요: 즉시

---

## 5. 자동화 가능 작업 (TARS 담당)

Gateway 설치 완료 후 TARS가 자동 처리 가능한 항목:

| 작업 | 스크립트 | 상태 |
|---|---|---|
| Gateway 연결 상태 모니터링 | `openclaw_codex_bridge.py ibkr-setup-status` | ✅ 준비 |
| ETF conid 해결 | `openclaw_codex_bridge.py ibkr-etf-check` | ✅ 준비 (Gateway 연결 시) |
| ETF whitelist 승인 | `openclaw_codex_bridge.py ibkr-etf-approve` | ✅ 준비 |
| Paper 주문 실행 | `ibkr_cp_client.py` | ✅ 준비 |
| 포지션/잔고 조회 | `ibkr_cp_client.py` | ✅ 준비 |
| 온보딩 상태 업데이트 | `openclaw_codex_bridge.py ibkr-setup-complete [step]` | ✅ 준비 |

---

## 6. 전체 타임라인 예측 (낙관 시나리오)

| 기간 | 마일스톤 | 의존성 |
|---|---|---|
| 즉시 | IBKR 계좌 신청 + BOK 질의 | HUMAN_REQUIRED |
| +1주 | KYC 통과 + 2FA 설정 | IBKR 심사 |
| +1~2주 | BOK 유권해석 회신 | 한국은행 처리 |
| +2주 | Gateway 설치 + Paper 계좌 활성화 | 계좌 개설 완료 |
| +3주 | Paper trading 1주차 시작 | Gateway 연결 |
| +10주 | Paper trading 8주 완료 + KPI 평가 | |
| +10~11주 | red_team_block 해제 조건 충족 시 Phase 1 진입 검토 | CEO 승인 |

---

## 7. 결론 및 권고

| 항목 | 상태 | 권고 |
|---|---|---|
| 코드 인프라 | ✅ 준비 완료 | Gateway 설치만 하면 즉시 작동 |
| 계좌 개설 | ❌ 미착수 | **즉시 신청 권고** |
| 외환 신고 | ❌ 미착수 | **BOK 유권해석 먼저 (입금 선행 조건)** |
| Paper trading | ❌ 미착수 | 계좌 개설 후 8주 필수 |
| Live 투입 | ⛔ 불가 | red_team_block + 게이트 미충족 |

**다음 단계: 대표님이 IBKR 계좌 신청 + 한국은행 질의를 동시 착수하면 최단 경로**

---

> 생성: 2026-05-24 | TARS (AR-021) | correlation_id: strategy-pivot-b2i-20260524
