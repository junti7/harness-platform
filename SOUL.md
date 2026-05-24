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
