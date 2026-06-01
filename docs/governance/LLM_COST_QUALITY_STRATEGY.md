# LLM Cost-Quality Operating Strategy
# Version: 1.2 — ✅ red_team_clear (2026-06-01)
# Owner: Chief of Staff
# 상위 규약: CLAUDE.md (Product-over-Pipeline Rule, Business Reality Constraint)
# Red Team: Gemini 2.5 Pro (clear-with-conditions) + Codex/GPT-5 (clear-with-conditions) + Claude (clear)

---

## 0. 배경 (Problem Statement)

OpenClaw·페르소나 LLM을 비용 기준으로 싼 것부터 비싼 것까지 분산했더니:

- 회의실 토론(내부 페르소나 debate)에서 페르소나 답변 품질 편차가 너무 큼.
- 로컬 LLM(Ollama/Gemma)은 회사 맥락을 이해 못 하고 동문서답.
- 그렇다고 전부 프리미엄(Sonnet)을 쓰면 비용 압박 → 결국 "이도저도 아닌" 운영.
- "상황에 따라 adaptive하게 모델 변경"을 시도했으나 실패.

현재 라우팅 실태:
- `agents/registry.py`: 페르소나별 provider(claude/gemini/codex) + fallback. **품질 tier가 아니라 provider 가용성 기반.**
- `scripts/llm_fallback_manager.py` / `runtime/persona_llm_fallback.json`: timeout 기반 failover일 뿐, 비용·품질 라우팅 아님.
- OpenClaw Chat/Tool/Formatter 3개 모두 Claude Sonnet 4.5 균일 사용.

---

## 1. 진단 (Root Cause)

**최적화 축이 틀렸다.**

1. **Adaptive-by-situation은 원래 안 되는 접근이다.** 모호한 "상황" 신호로 모델을 실시간 선택하는 건 디버깅이 불가능하다. 실패는 튜닝 부족이 아니라 구조적 한계다. → 정적(static) task-tier 라우팅으로 대체한다.

2. **비용 압박의 근원은 "돈 안 되는 곳에 좋은 모델"이다.** 회의실 토론은 직접 수익이 0인데 Sonnet을 쓴다. CLAUDE.md의 Business Reality Constraint·Product-over-Pipeline Rule과 정면 충돌.

3. **로컬 LLM의 동문서답은 능력 한계(capability ceiling)다.** 설정으로 못 고친다. 좁고 스키마 고정된 작업에만 투입해야 한다.

---

## 2. 핵심 원칙 (Operating Principles)

### 원칙 1 — 비용이 아니라 "산출물의 목적지(destination)"로 라우팅한다

3개 레인으로 **정적 테이블** 고정. adaptive 제거.

| 레인 | 대상 작업 | 모델 | 핵심 |
|---|---|---|---|
| **A. 기계적(Mechanical)** | dedup, 분류, 추출, JSON 포매팅, tool 라우팅, Tier 2 게이트 | Ollama / Haiku | 맥락 이해 불필요. 로컬이 동문서답 안 하는 유일 영역 |
| **B. 내부 추론(Internal Reasoning)** | 페르소나 의견, 회의실 토론, 내부 메모 | Sonnet | 비용 레버 = 모델 품질이 아니라 **빈도/인원** |
| **C. 고객·자본(Customer/Capital)** | WTP 카피, 유료 산출물, CEO decision card, 투자 thesis, QA, Red Team | Opus / Sonnet 고정 | 품질 절대 타협 금지. 수익으로 연결되는 유일 지점 |

### 원칙 2 — 로컬 LLM은 추론 레인에 절대 넣지 않는다 + Lane A는 검증한다

Gemma/Ollama는 Lane A 전용. Lane B/C에 넣으면 동문서답이 보장된다.

**[Red Team 반영] Lane A는 무해한 배관이 아니다.** 싼 모델의 JSON 오류·잘못된 tool routing·잘못된 schema 매핑이 조용히 Lane B/C로 전파(cascade)된다. 따라서 Lane A는 "신뢰"가 아니라 "검증" 대상이다:

- **출력 검증 게이트(guardrail):** Lane A의 structured 출력(JSON, tool 선택)은 schema/허용값 검증을 통과해야 한다. 실패 시 **자동으로 Sonnet에 재실행(escalate)**. 신뢰하지 말고 검증한다.
- **task-level 승급 규칙(코드로 정의):** "복잡하면 Sonnet"은 운영 불가능한 모호함이다. 프로그래밍 가능한 규칙으로 못박는다.
  - 금융 거래·고객 데이터 접근이 걸린 tool call → Sonnet 강제
  - 3단계 초과 agent chain의 routing → Sonnet
  - schema 검증 1회 실패 → 해당 task Sonnet 재실행

### 원칙 3 — 비용을 줄일 때는 모델 품질이 아니라 VOLUME을 줄인다

예산이 쪼들리면 (우선순위 순):
1. 회의 빈도 ↓ (매일 → 주 2회)
2. 회의당 페르소나 ↓ (전원 → 핵심 3명)
3. 호출당 context 길이 cap
4. **Sonnet→Gemma 다운그레이드 금지**

품질 floor를 지키면 "남는 답변은 전부 쓸모 있음"이 유지된다. 전 영역 품질 삭감 = "이도저도 아닌" 상태.

### 원칙 4 — 예산 게이트는 '조용한 다운그레이드'가 아니라 '볼륨 차단기'다 (단, 텔레메트리 선행)

일일 예산 한도 접근 시: **Lane B(내부 회의 빈도)를 먼저 차단하고, Lane C(고객-facing)를 마지막까지 살린다.**

**[Red Team 반영] 텔레메트리 없는 볼륨 삭감은 'blind austerity'다.** 볼륨을 자르기 전에 아래 지표를 측정한다. 지표가 악화되면 **볼륨 삭감을 중단**한다:

- routing 오류율 (잘못된 tool 선택 비율)
- schema 검증 실패율
- rework 비율 (Lane B→C 재작성 발생률)
- decision reversal 비율 (대표가 뒤집은 결정)
- founder 교정 시간 (대표가 산출물 고치는 데 쓴 시간)

지표 없이 "회의 줄이기"로 직행하지 않는다.

### 원칙 5 — 회의실을 broad하게 굶기지 않는다: 수익 추론 코어는 프리미엄으로 보호

**[Red Team 반영]** "첫 유료 구독자 전까지 회의실은 안 풀어도 된다"는 위험하다. 회의실이 offer 설계·WTP framing·학부모 pain 해석이 일어나는 곳이면, 저품질 토론은 overhead가 아니라 **직접적 수익 리스크**다 (대표의 희소한 시간 낭비 + confirmation bias).

따라서 Lane B를 일괄 삭감하지 않고, **작은 고품질 추론 코어를 보존**한다:

- WTP framing, offer 설계, **반대의견 합성(disagreement synthesis)** → 4대 수익 행동에 직결된 추론은 프리미엄 유지.
- 회의 인원을 줄이더라도 **adversarial 반대자(최소 1명)는 반드시 남긴다** — 동의만 하는 회의는 의미 없음.
- 절약 대상은 "수익과 무관한 반복적 페르소나 의견"이지, "의사결정 품질"이 아니다.

**Lane B→C 명시적 승급 경로(promotion path):** 내부 아이디어가 고객 산출물이 되는 지점에 deliberate 핸드오프를 둔다. `promote_to_customer_facing` 태그가 붙은 Lane B 산출물은 Lane C(Opus) 전체 review-and-rewrite를 강제 통과한다. 우연한 품질 누수 방지.

---

## 3. 즉시 적용값 (Concrete Defaults)

### OpenClaw Chat/Tool/Formatter 분리

| 구성요소 | 현재 | 변경 | 근거 |
|---|---|---|---|
| **Formatter** (스키마 출력 정리) | Sonnet | **Haiku/로컬** | 추론 없음. 가장 쉬운 절감 |
| **Tool 실행** (tool·파라미터 선택) | Sonnet | **기본 Haiku**, 복잡 판단만 Sonnet | bounded 판단 |
| **Chat** (대표 직접 대화) | Sonnet | **Sonnet 유지** | 품질 직접 체감, 타협 불가 |

### 페르소나 회의 cadence (잠정)

- 정례 회의실 토론: 주 2회, 핵심 페르소나 3명 기준.
- 전원 참석 회의는 high-impact 의사결정 직전에만.

---

## 4. 폐기 (Deprecate)

- "상황 기반 adaptive 모델 변경" 목표 폐기. 정적 task-tier 라우팅으로 대체.
- 비용 균일 분산(cheap→expensive 전 레인 적용) 폐기.

---

## 5. 검증 상태

### Red Team 1차 (2026-06-01)

| 모델 | 1차 판정 | 핵심 지적 |
|---|---|---|
| Gemini 2.5 Pro | clear-with-conditions | Lane A 검증 부재, Lane B→C 의존, 측정 부재 |
| Codex / GPT-5 | block | 동일 (Lane B 굶기면 C 붕괴, 라벨 Goodharting, 텔레메트리 부재) |
| Claude | synthesis | 2-of-3 clear 미달 → v1.1로 조건 반영 |

**반영된 조건 (v1.1):**
1. Lane A 출력 검증 게이트 + task-level 승급 규칙 (원칙 2)
2. 볼륨 삭감 전 품질 텔레메트리 선행 (원칙 4)
3. 수익 추론 코어 보존 + Lane B→C 승급 경로 (원칙 5)

### Red Team 2차 (v1.1 → v1.2, 2026-06-01)

| 모델 | 2차 판정 | 3개 원래 지적 처리 |
|---|---|---|
| Gemini 2.5 Pro | clear-with-conditions | 3개 모두 addressed |
| Codex / GPT-5 | clear-with-conditions | 3개 모두 addressed |
| Claude (synthesis) | clear | 2-of-2 충족 |

**신규 지적 4건 (구현 단계 이슈, 전략 block 사유 아님):**
1. 시맨틱 오류 — Lane A 구현 시 spot-check 추가
2. `promote_to_customer_facing` 수동 태깅 실패 — 정책: 고객 카피·가격·추천 닿는 건 auto-promote
3. 복잡도 정의 부족 — 구현 시 ambiguity·요약·cross-agent 기준 추가
4. 텔레메트리 임계값 미정 — 구현 시 X%/Y기간 + owner 명시

**✅ red_team_clear 달성 (2026-06-01)**

### 잔여 체크리스트

- [x] Red Team 1차 (v1.0) — 2-of-2 지적 반영
- [x] Red Team 2차 (v1.1) — ✅ red_team_clear 달성
- [ ] **대표 승인** ← 현재 단계
- [ ] 구현 (라우팅 테이블 + 검증 게이트 + 텔레메트리 + 볼륨 차단기)
