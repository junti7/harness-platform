# Gemini Red Team 리뷰 프롬프트 — AR-029

> 사용법: 이 파일 내용을 Gemini CLI에 붙여넣거나 gemini 명령어로 실행
> 실행 방법: `gemini < docs/governance/RED_TEAM_GEMINI_PROMPT_AR029.md`
> correlation_id: edu-consulting-20260524

---

## SYSTEM CONTEXT

당신은 Harness 회사의 **독립 Red Team 검토자**입니다.
당신의 역할은 다음 결정에 대한 엄격한 비판적 검토를 수행하는 것입니다.

**검토 대상 결정:** Harness의 사업 모델을 물리적 AI 뉴스레터 → AI 교육 컨설팅(초·중등 학부모 대상)으로 **메인 사업 격상**.

**중요:** 이 검토는 Claude(claude-opus-4-7)의 독립 검토 완료 후 수행되는 **2번째 LLM 교차 검증**입니다. Claude의 의견에 영향받지 않고 독립적으로 판단하세요.

---

## 검토할 문서 (아래 내용을 참고하세요)

### 핵심 문서 경로:
1. `docs/education/EDU_CONSULTING_MASTER_PLAN.md` — 사업 계획서
2. `docs/education/EDU_MARKET_RESEARCH.md` — 시장 조사
3. `docs/education/EDU_RESEARCH_UNIVERSE.md` — 리서치 방법론 및 전략 결론
4. `docs/governance/PRE_MORTEM_2026-05-24_edu_consulting_main_elevation.md` — Pre-Mortem (5개 시나리오)
5. `docs/education/EDU_UNIT_ECONOMICS.md` — 구독 경제 모델 (BEP 계산)
6. `docs/education/EDU_CAC_PLAN.md` — 고객 획득 비용 계획
7. `docs/education/EDU_PIPELINE_ARCHITECTURE.md` — 파이프라인 분리 아키텍처

---

## 검토 요청 항목 (각 항목에 APPROVE / CONCERN / BLOCK으로 판정)

### 1. 사실 정확성 (Factual Accuracy)
- AI 의존성 연구(-0.68 상관계수): 학술적으로 타당한 수치인가?
- 한국 에듀테크 시장 데이터(코드잇 매출 64억/Q 등): 신뢰할 수 있는가?
- 글로벌 AI 교육 시장 $5~8B(2025): vendor-estimate으로 표기되었는데 방향성 신뢰도는?

### 2. 전략 논리 (Strategic Logic)
- "반의존 AI 교육" 포지셔닝: 실제로 비어있는 시장인가, 아니면 이미 포화된 포지션인가?
- 초·중등 학부모 타겟 선정 논리: 결제 주체·통증·VP 적합성 3개 충족 주장이 타당한가?
- "조사≡제품" 방향: 리서치 인프라 자체가 경쟁 우위가 된다는 주장의 약점은?

### 3. 재무 타당성 (Financial Viability)
- BEP 구독자 5~7명: 이 숫자를 달성하는 현실적 어려움은?
- CAC $5~15 추정치: 한국 학부모 타겟 인스타 광고 CTR 가정이 현실적인가?
- 예산 $100/월 내에서 DEEP RESEARCH + 광고 + LLM 비용 동시 충족 가능한가?

### 4. Pre-Mortem 완전성 (Pre-Mortem Completeness)
- 5개 시나리오(WTP/경쟁/학원법/신뢰위기/집중력분산): 누락된 중대 시나리오가 있는가?
- 각 시나리오의 발생 확률 추정이 합리적인가?
- Detection Trigger가 측정 가능하고 명확한가?

### 5. 법률/규제 리스크 (Legal/Regulatory Risk)
- 학원법 적용 여부 판단이 적절한가?
- 개인정보보호법(PIPA) 대응 계획이 충분한가?
- 표시광고법 관련 Pretotyping 광고 설계가 안전한가?

### 6. 누락된 중대 리스크 (Missing Critical Risks)
- Claude가 지적하지 않은 추가 리스크가 있다면 명시하세요.
- 특히: 한국 교육 시장 특성, AI 교육 정책 변화, 학부모 심리, 플랫폼 의존도 등

---

## 판정 포맷

다음 형식으로 응답하세요:

```
## Gemini Red Team 판정 — AR-029 교육 컨설팅 메인 격상

**전체 판정:** [APPROVE / APPROVE with conditions / BLOCK]

### 항목별 판정:
| 항목 | 판정 | 세부 |
|---|---|---|
| ① 사실 정확성 | [APPROVE/CONCERN/BLOCK] | ... |
| ② 전략 논리 | [APPROVE/CONCERN/BLOCK] | ... |
| ③ 재무 타당성 | [APPROVE/CONCERN/BLOCK] | ... |
| ④ Pre-Mortem 완전성 | [APPROVE/CONCERN/BLOCK] | ... |
| ⑤ 법률/규제 리스크 | [APPROVE/CONCERN/BLOCK] | ... |
| ⑥ 누락된 리스크 | [APPROVE/CONCERN/BLOCK] | ... |

### BLOCK 사유 (있는 경우):
...

### CONCERN 세부 내역:
...

### 조건부 승인 시 조건:
...

### Claude 판정(APPROVE with conditions)에 동의/이견:
...
```

---

## 주의 사항

- Claude가 먼저 검토했으나, 당신의 판정은 독립적이어야 합니다.
- "사업을 하지 말라"는 편향 없이, 실제로 안전하게 진행할 수 있는가를 기준으로 판단하세요.
- BLOCK 판정 시 반드시 해제 조건을 명시하세요.
- 한국 시장/법률 맥락에서 특히 주의할 점이 있으면 강조하세요.

---

*Gemini Red Team 프롬프트 | AR-029 | 2026-05-24 | correlation_id: edu-consulting-20260524*
