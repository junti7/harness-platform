# SOUL.md — Harness 전략 결정 기록부

> 이 문서는 Harness의 중대 전략 전환 결정을 영구 보관하는 기록부입니다.
> 비서실장(Jarvis)이 관리하며, CEO 승인 결정만 등재됩니다.

---

## 결정 #001 — B2C 뉴스레터 → B2I 내부 투자 의사결정 엔진 전환

**결정일**: 2026-05-24
**correlation_id**: `strategy-pivot-b2i-20260524`
**결정권자**: 대표(President/CEO)
**기록 대행**: Jarvis 비서실장 (AR-022 대행)

### 결정 내용

Harness의 사업 모델을 **B2C 뉴스레터 구독 서비스**에서 **내부 투자 의사결정 엔진(B2I)**으로 전면 전환한다.

### 전환 배경

- Physical AI 리서치 파이프라인(Tier 1~3)이 고품질 투자 신호를 생산하고 있음
- IBKR(Interactive Brokers) API 기반 자기계정 ETF 운용을 통한 내부 수익 창출 모델로 전환
- 기존 B2C 뉴스레터(Substack/Maily) 발행 및 독자 모집 계획은 **전면 보류(hold)**

### 보류 처리된 AR 목록

| AR | 내용 | 상태 변경 |
|---|---|---|
| AR-009 | dossier 포맷 초안 + unit economics | open → hold |
| AR-010 | pre_mortem 메모 (#003 발행) | open → hold |
| AR-011 | red_team_clear (#003 발행) | open → hold |
| AR-012 | legal_review_approve (#003 발행) | open → hold |
| AR-013 | qa_clear (#003 발행) | open → hold |
| AR-014 | QA 체크리스트 통합 | open → hold |
| AR-015 | Coach OJT 업데이트 | open → hold |
| AR-20260524-001~013 | 콘텐츠 모델 변경 후속 AR | open → hold |

### 신규 등록된 AR 목록 (B2I 전환)

| AR | 담당 | 내용 | 기한 |
|---|---|---|---|
| AR-016 | Jarvis | 전환 총괄 관리 + SOUL.md 기록 | 2026-05-24 |
| AR-017 | KITT | IBKR 자기계정 자본시장법/외국환거래법 적법성 진단 | 2026-05-27 |
| AR-018 | Watchman | B2I 전환 리스크 5종 + KILL_CRITERIA Stop-Loss 기준 | 2026-05-27 |
| AR-019 | Ledger | 초기 투자 $7,000 시나리오 3종 + BEP 산출 | 2026-05-28 |
| AR-020 | Vision | Physical AI 투자 Thesis 표준 템플릿 | 2026-05-28 |
| AR-021 | TARS | IBKR 온보딩 6단계 점검 + paper trading 플랜 | 2026-05-29 |
| AR-022 | Friday (Jarvis 대행) | KPI 재설정 + SOUL.md 기록 | 2026-05-24 |

### CEO 추가 결정 사항 (2026-05-24)

| 번호 | 결정 내용 |
|---|---|
| 결정-1 | Gemini 외국환거래규정 풀스캔 비용 ($3~5) 승인 |
| 결정-2 | 외부 변호사 대신 Claude Legal Skill 활용으로 대응 |
| 결정-3 | AR-022 SOUL.md 수정은 Jarvis 대행 |
| 결정-4 | B2I 전환 Pre-Mortem 발주 승인 |
| 결정-5 | Paper Trading 기간 8주→2주 단축 (2026-05-27 CEO 결정). 기완료 항목(Alpaca 연결·SOXX 주문·Cross-LLM 게이트) 인정. 완료 기준일: **2026-06-08**. 잔여 검증: MDD 모니터링·청산 로직. |
| 결정-6 | 한국은행 외환거래 회신 수령 및 지정은행 해외예금/증권취득 신고 의무 완료 확인 (연간 $100K 이하 송금 시 신고 불필요 한도 적용, 은행 확인 최종 승인 완료, 2026-05-31 CEO 결정) |

### 신규 KPI (B2I 모델 기준)

| 지표 | 정의 |
|---|---|
| IBKR 개설 완료율 | 계좌 개설 → 입금 → 첫 주문 실행까지 단계 완료율 |
| Thesis 생성 성공률 | 파이프라인 Tier 3 출력 → Thesis 템플릿 완성 비율 |
| Thesis 검증 성공률 | red_team_clear + legal_review_approve 통과 비율 |
| 포트폴리오 MDD 준수율 | Stop-Loss 킬스위치 미발동 기간 비율 |
| LLM 비용 대비 투자 수익률 | 월 투자 수익 / 월 LLM API 비용 |

### 불변 원칙 (전환 후에도 유지)

- capital_action_approve 없이 실제 자금 집행 절대 불가
- legal_review_approve + red_team_clear + pre_mortem_approve 3종 게이트 사전 충족 필수
- 모든 투자 결정은 CEO 최종 승인 후 실행

---

*기록: 2026-05-24 | 비서실장 Jarvis 대행 | correlation_id: strategy-pivot-b2i-20260524*

---

## 결정 #002 — AI 교육 컨설팅 메인 격상 + 뉴스레터 Backend 전환

**결정일**: 2026-05-24
**correlation_id**: `edu-consulting-20260524`
**결정권자**: 대표(President/CEO)
**기록 대행**: 비서실장(Chief of Staff)

### 결정 내용

Harness의 **외부 수익 라인**을 AI 교육 컨설팅으로 확정하고, 기존 Physical AI 뉴스레터 파이프라인은 외부 발행 없이 **IBKR B2I 투자 정보 수집 Backend**로 운영한다.

### 3-Layer 사업 구조 (확정)

| Layer | 역할 | 상태 |
|---|---|---|
| **교육 컨설팅** | 메인 외부 수익. 초·중등 학부모 대상 AI 반의존 자문 구독 | ✅ 메인 격상 |
| **뉴스레터 파이프라인** | 외부 발행 중단. IBKR 투자 신호 수집·분석 내부 Backend | Backend 전환 |
| **B2I IBKR 투자 엔진** | 내부 자기계정 투자 (AR-018 red_team_block 해제 조건 충족 후) | ⏳ 대기 |

### Pre-Mortem 승인 (2026-05-24)

`pre_mortem_approve` 기록 완료 (AR-029). 5개 시나리오 CEO 검토·승인.
통과 조건: pretotyping 선행 / 학원법 전문가 / VP 검토 / 집중력 명시 / 경쟁 레이더.

### DEEP RESEARCH 예산 (2026-05-24)

월 $100 한도. 초과 시 CEO 별도 승인. 예상 실소비 $35~60/월.

### 불변 원칙 (추가)

- 교육 컨설팅 고객-facing 산출물은 VP 검토 + QA `qa_clear` 필수
- 뉴스레터 파이프라인은 외부 발행 불가 (Backend 전용)
- 교육사업 외부 발행·유료 제안 전 Red Team `red_team_clear` 필수 (진행 중)

---

### Paper Trading 선행 의무 프로토콜 (상시 모니터링 및 OpenClaw 연동)

**프로토콜 수립일**: 2026-05-27
**실행 및 검증 주체**: OpenClaw (비서실장) & Codex (기술 지원)

대표님 또는 관계자가 모의 투자 실적, 현황, 또는 KPI 달성 여부를 물을 경우, OpenClaw는 수동으로 요약을 요구하거나 추정 답변을 하지 말고 **반드시 아래 실시간 조회 명령을 수행**하여 현황을 브리핑해야 합니다.

#### 1. 실시간 조회 및 KPI 자동 산출 명령
```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py alpaca-status --format text
```

#### 2. 검증할 3대 핵심 KPI (SOUL.md 명시 기준)
1. **① 누적 가상 수익률**: 8주(단축 2주) 누적 가상 수익률 ≥ SPY 벤치마크 수익률 - 5% (5/24이후 기준)
2. **② 신호 정확도**: 신호 발생 후 2주 내 방향 일치율 ≥ 55% (데이터 부족 시 2주 대기 상태로 보고)
3. **③ 최대 포지션 손실**: 최대 단일 포지션 unrealized loss ≤ -15%

---

*기록: 2026-05-24 | 비서실장(Chief of Staff) | correlation_id: edu-consulting-20260524*
