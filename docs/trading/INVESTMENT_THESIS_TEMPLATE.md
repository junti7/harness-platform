# Physical AI 투자 Thesis 표준 템플릿

> 작성일: 2026-05-24 | 담당: Vision | AR: AR-020  
> correlation_id: strategy-pivot-b2i-20260524  
> **사용 원칙: 모든 Thesis는 cross-LLM 검증(2-of-3 승인) 없이 실주문으로 전환 불가**

---

## 사용 방법

1. Tier 1~3 파이프라인 출력이 완성되면 이 템플릿을 복사
2. 각 섹션을 채운 뒤 `신뢰도 점수`가 **0.70 이상**인 경우에만 다음 단계 진행
3. CEO 검토 → cross-LLM 게이트(Red Team) → CEO 최종 승인 → 주문
4. 모든 주문 의도는 **Ledger 에스크로** 단계를 거쳐야 함

---

## THESIS-[YYYYMMDD]-[시퀀스] 템플릿

```
thesis_id: THESIS-YYYYMMDD-NNN
generated_at: YYYY-MM-DDTHH:MM:SS
pipeline_run_id: [Tier3 출력 correlation_id]
status: draft | pending_gate | approved | rejected | executed | invalidated
```

---

### 섹션 1 — 신호 개요 (Signal Summary)

**근거 소스** (Tier 1 수집 원본 — 최소 2개 독립 소스 필요)

| 소스 | 유형 | 발행일 | URL / 경로 | 근거 자세 |
|---|---|---|---|---|
| | 논문/공시/뉴스/특허 | | | verified / company-self-report / speculative |
| | | | | |

**핵심 신호 요약** (3문장 이내)

```
[Tier 2 필터 통과 후 Tier 3가 추출한 핵심 신호를 여기 기재]
```

**신호 강도** (Tier 3 출력 기준)

- [ ] 강 (Strong): 복수 소스 cross-confirm, 구체적 수치·날짜·계약
- [ ] 중 (Medium): 단일 신뢰 소스, 수치 있음
- [ ] 약 (Weak): 단일 소스, 추정·예측 위주

---

### 섹션 2 — 투자 Thesis

**핵심 주장** (1문장)

```
[예: "NVIDIA의 GB300 공급 쇼티지가 2026Q3 해소되면 BOTZ 내 로봇 제조사 매출이 
 전분기 대비 +12~18% 증가할 것이다"]
```

**논리 구조** (인과 체인)

```
신호 → 1차 영향 → 2차 영향 → ETF 수익 기제
[예: 공급 쇼티지 해소 → 제조업체 CAPEX 재개 → 로봇 도입 가속 → BOTZ AUM 증가]
```

**무효화 조건** (이 중 하나라도 발생하면 Thesis 자동 폐기)

```
- [예: NVIDIA GB300 출하 지연 3개월 이상 공식 발표]
- [예: 미·중 반도체 수출규제 신규 품목 추가]  
- [예: 주요 보유 종목 어닝 미스 -20% 이상]
```

**선행 지표** (thesis 추적용 — 주 1회 Tier 1에서 모니터링)

```
- [예: TSMC 월간 매출 발표]
- [예: NVIDIA 공급망 파트너 inventory 데이터]
```

---

### 섹션 3 — ETF 매핑

**대상 ETF** (etf_whitelist_v0.json 등재 필수)

| ETF 티커 | 이름 | 노출 비중 (해당 Thesis 관련) | whitelist 확인 |
|---|---|---|---|
| | | % | [ ] 확인 |
| | | % | [ ] 확인 |

**ETF 선택 근거**

```
[왜 이 ETF가 Thesis 노출에 최적인지 — 구성종목 상위 5개 기준]
```

**분산 체크**

- [ ] 단일 ETF 비중 ≤ 60% (전체 포트폴리오 기준)
- [ ] 동일 섹터 ETF 중복 노출 합계 ≤ 80%
- [ ] Physical AI 외 완충 자산 존재 여부: ___

---

### 섹션 4 — 진입 조건 (Entry)

**진입 트리거** (아래 조건이 **모두** 충족될 때만 주문 의도 생성)

```
- 기술적 조건: [예: 20일 이평선 위 + RSI < 65]
- 펀더멘털 조건: [예: 신호 강도 "중" 이상 + 소스 2개 이상]
- 비용 조건: 당일 LLM 비용 < 일일 한도의 80%
- 게이트 조건: cross-LLM 검증 완료 (2-of-3 approve)
```

**진입 시점**

```
- 선호 시간대: 미국 시장 오전 (EST 09:30~11:30, KST 23:30~01:30)
- 분할 매수: [ ] 1회 일괄 / [ ] 2~3회 분할 (___% / ___% / ___)
```

**진입 규모**

```
- 1회 Thesis 최대 투입: USD ___ (전체 포트폴리오의 ___%)
- Phase 1 hard-cap: USD 500 (capital_plan_2026-05.md Phase 1 기준)
```

---

### 섹션 5 — 청산 조건 (Exit)

**목표 수익 청산** (Profit Target)

```
- 1차 목표: +___% 달성 시 포지션의 50% 청산
- 최종 목표: +___% 달성 시 잔여 청산
- 목표 도달 예상 기간: ___ 주
```

**손절 청산** (Stop-Loss — KILL_CRITERIA 연동)

```
- 포지션 손실 -15%: 자동 청산 알림 생성 → CEO 승인 후 청산
- 포트폴리오 전체 MDD -20%: 강제 청산 (Watchman KILL_CRITERIA)
```

**Thesis 무효화 청산**

```
- 섹션 2의 무효화 조건 중 1개라도 발생 시 즉시 청산 의도 생성
- CEO 승인 후 체결 (자동 실행 불가)
```

**시간 청산** (Time-based Exit)

```
- 진입 후 ___ 주 경과 + 목표 미달성 시: 포지션 재검토 후 유지/청산 결정
```

---

### 섹션 6 — 무효화 추적 (Invalidation Log)

| 날짜 | 점검 항목 | 결과 | 조치 |
|---|---|---|---|
| | | OK / WARN / INVALIDATED | |

---

### 섹션 7 — 신뢰도 점수 (Confidence Score)

아래 항목을 채점하여 합산 점수로 게이트 통과 여부 결정.

| 항목 | 배점 | 획득 | 근거 |
|---|---|---|---|
| 소스 독립성 (2개 이상 서로 다른 출처) | 20 | | |
| 소스 신뢰도 (peer-reviewed / 공시 / 주요 언론) | 20 | | |
| 수치·날짜·계약 구체성 | 15 | | |
| Physical AI 직접 연관성 | 15 | | |
| ETF 내 보유 종목 노출 확인 | 10 | | |
| 무효화 조건 명시 | 10 | | |
| 선행 지표 정의 | 10 | | |
| **합계** | **100** | **___** | |

**통과 기준: 70점 이상**

- 70점 미만: Thesis 폐기 또는 추가 조사 후 재작성
- 70~84점: cross-LLM 게이트 통과 후 CEO 검토
- 85점 이상: 우선순위 검토 대상

---

### 섹션 8 — Cross-LLM 게이트 (주문 전 필수)

**검증 참여 모델** (최소 2-of-3 approve 필요)

| 모델 | 역할 | 판정 | 핵심 발견 |
|---|---|---|---|
| Claude | 전략·논리 검토 | APPROVE / CONCERN / BLOCK | |
| Gemini | 소스 교차검증, 수치 확인 | APPROVE / CONCERN / BLOCK | |
| GPT (선택) | 판정 중재 | APPROVE / CONCERN / BLOCK | |

**게이트 통과 조건**

- 3개 모델 중 2개 이상 APPROVE
- BLOCK 판정이 하나라도 있으면 → CEO 확인 필수 (non-negotiable)
- factual error, fabricated source, 법률 위험 발견 시 → 자동 폐기

**게이트 결과**

```
gate_result: pending | passed | blocked
gate_completed_at: 
gate_evidence: [파일 경로]
```

---

### 섹션 9 — CEO 검토 및 최종 승인

**검토 요약** (CEO에게 전달하는 1페이지 브리프)

```
Thesis ID: 
신호: [1문장]
대상 ETF: [티커]
진입 규모: USD ___
목표 수익: +___%
손절: -___%
신뢰도: ___점/100
게이트: [passed/blocked]
```

**CEO 결정**

- [ ] APPROVE → `capital_action_approve` 기록 후 주문 의도 생성
- [ ] REJECT → 폐기 사유 기록
- [ ] HOLD → 추가 정보 필요 사항 기재: ___

---

### 섹션 10 — 실행 이력 (Execution Log)

| 날짜 | 액션 | ETF | 수량 | 단가 | 체결 금액 | 승인자 |
|---|---|---|---|---|---|---|
| | BUY/SELL | | | | | CEO |

---

> 템플릿 버전: v1.0 | 생성: 2026-05-24 | Vision (AR-020)  
> correlation_id: strategy-pivot-b2i-20260524  
> AR-018 조건4(신호→주문 cross-LLM 게이트) 반영 완료 — 섹션 8 참조
