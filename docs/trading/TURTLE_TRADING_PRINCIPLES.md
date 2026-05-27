# Turtle Trading Principles
# Version: 1.0 | Source: https://share.google/aimode/tZ9c8wHdjLvNG41dB
# 상위 규약: CLAUDE.md §4, docs/product/PLATFORM.md
# 최종 업데이트: 2026-05-25

---

## ⚠️ 핵심 선언 — Harness 트레이딩의 절대 원칙

> **Harness의 모든 주식 트레이딩 활동은 Turtle Trading 원칙을 엄격히 따른다.**
> 감(gut feeling), 임시 판단, 비정형 예외는 허용하지 않는다.
> 이 규칙을 우회하는 `capital_action_approve`는 대표의 명시적 서면 확인 없이 실행할 수 없다.

---

## 1. 전략 개요

Turtle Trading은 1980년대 Richard Dennis와 William Eckhardt가 개발한 **규칙 기반 추세 추종(trend-following) 전략**이다.

핵심 철학:
- 성공적인 트레이딩은 "직관"이 아니라 **정밀한 알고리즘에 대한 절대적 규율(absolute discipline)** 에서 나온다.
- 누구든 올바른 시스템을 배우면 성공적으로 트레이딩할 수 있다 (원실험 명제).
- 감정이 아닌 규칙이 결정한다.

---

## 2. 5대 핵심 구성요소

### 2-1. 시장 선택 (Market Selection)

| 항목 | 기준 |
|------|------|
| 거래 대상 | 유동성 높은 선물 시장: 원자재, 통화, 주요 지수 |
| 매수 원칙 | 가장 강한 시장을 매수한다 |
| 매도 원칙 | 가장 약한 시장을 공매도한다 |
| 목적 | 모멘텀 극대화 |

> **Harness 적용**: 개별 종목 선택 전 시장·섹터 강도 지표를 먼저 검토한다. 약세 시장에서 매수를 시도하지 않는다.

---

### 2-2. 포지션 사이징 (Position Sizing)

| 항목 | 기준 |
|------|------|
| 리스크 한도 | 트레이드당 **전체 계좌의 1%** 이하 |
| ATR 계산 | 20일 Average True Range (Turtles가 "N"이라 부름) |
| 포지션 크기 | N 기반 변동성으로 결정 |
| 피라미딩 | 수익 발생 시 순차적으로 최대 한도까지 단위 추가 |

> **공식**: `포지션 단위 = (계좌 × 1%) ÷ (N × 달러 가치)`

> **Harness 적용**: 어떤 단일 트레이드도 계좌 리스크의 1%를 초과하지 않는다. 포지션 크기는 반드시 ATR 계산 결과에 의해 결정된다.

---

### 2-3. 진입 신호 (Entry Signals)

두 개의 브레이크아웃 시스템을 병행 운영한다:

#### System 1 (단기)
| 방향 | 신호 |
|------|------|
| 매수 (Long) | 가격이 **20일 최고가** 돌파 시 |
| 매도 (Short) | 가격이 **20일 최저가** 하향 돌파 시 |

#### System 2 (장기)
| 방향 | 신호 |
|------|------|
| 매수 (Long) | 가격이 **55일 최고가** 돌파 시 |
| 매도 (Short) | 가격이 **55일 최저가** 하향 돌파 시 |

> **Harness 적용**: 진입은 반드시 System 1 또는 System 2 신호 발생 후에만 실행한다. 신호 없는 예측성 진입은 금지한다.

---

### 2-4. 리스크 관리 — 손절 (Stop-Loss)

| 항목 | 기준 |
|------|------|
| 손절 규칙 | 진입가에서 **2 × N** 역방향 이동 시 포지션 청산 |
| 목적 | 손실 상한 고정 + 감정적 판단 배제 |

> **공식**: `Stop-Loss = 진입가 ± (2 × ATR)`

> **Harness 적용**:
> - 손절 수준은 진입 전 반드시 사전 계산하여 기록한다.
> - 손절선 이탈 시 "조금만 더 기다리자"는 예외 없다.
> - `capital_action_approve` 기록 시 손절가 필드 필수 입력.

---

### 2-5. 청산 신호 (Exit Signals)

#### System 1 청산
| 포지션 | 청산 조건 |
|--------|-----------|
| 롱 (Long) | 가격이 **10일 최저가** 하향 이탈 시 |
| 숏 (Short) | 가격이 **10일 최고가** 상향 이탈 시 |

#### System 2 청산
| 포지션 | 청산 조건 |
|--------|-----------|
| 롱 (Long) | 가격이 **20일 최저가** 하향 이탈 시 |
| 숏 (Short) | 가격이 **20일 최고가** 상향 이탈 시 |

> **Harness 적용**: 청산 신호가 발생하면 즉시 실행한다. "더 올라갈 것 같다"는 이유로 청산을 미루지 않는다.

---

## 3. 요약 파라미터 테이블

| 구성요소 | System 1 | System 2 |
|----------|----------|----------|
| 진입 (Long) | 20일 최고가 돌파 | 55일 최고가 돌파 |
| 진입 (Short) | 20일 최저가 하향 | 55일 최저가 하향 |
| 손절 | 진입가 ± 2N | 진입가 ± 2N |
| 청산 (Long) | 10일 최저가 | 20일 최저가 |
| 청산 (Short) | 10일 최고가 | 20일 최고가 |
| 포지션 리스크 | 계좌 1% | 계좌 1% |
| ATR 기간 | 20일 | 20일 |

---

## 4. Harness 트레이딩 운영 규칙

### 4-1. 절대 원칙 (Non-Negotiables)

```
✅ 모든 포지션은 Turtle 신호에 근거해야 한다.
✅ 포지션 크기는 ATR 기반 1% 리스크 한도로 계산한다.
✅ 손절가는 진입 전 계산하고, 진입 기록 시 명시한다.
✅ 청산 신호 발생 시 즉시 실행한다.
❌ 신호 없는 예감/직관 기반 진입 금지.
❌ 손절선 이탈 후 홀딩 금지.
❌ 청산 신호 발생 후 "조금만 더" 대기 금지.
❌ 단일 트레이드에 계좌 1% 초과 리스크 부담 금지.
```

### 4-2. capital_action 연동

- 모든 트레이딩 관련 `capital_action_approve`는 다음 필드를 반드시 포함해야 한다:
  - `entry_system`: `S1` 또는 `S2`
  - `entry_signal_date`: 신호 발생일
  - `atr_value`: 계산에 사용한 N (20일 ATR)
  - `position_size_units`: 단위 수
  - `risk_pct`: 실제 리스크 비율 (≤ 1%)
  - `stop_loss_price`: 사전 계산된 손절가
  - `exit_system`: `S1` 또는 `S2`

- `CAPITAL_ACTIONS_ENABLED=false` 상태에서는 어떤 트레이딩 실행도 불가.

### 4-3. Pre-Mortem 의무

트레이딩 포지션 오픈 전 `docs/governance/PRE_MORTEM_PROTOCOL.md`에 따른 pre-mortem 작성 의무.
- worst-case: 손절 전 최대 낙폭 시나리오
- 복구 가능성: 손절 후 재진입 기준
- detection trigger: 손절 신호

### 4-4. Red Team 의무

트레이딩 thesis 발행 또는 대규모 포지션 오픈 시:
- `red_team_clear` (Claude + Gemini 또는 Claude + GPT reasoning) 필수
- Turtle 파라미터 계산 검증 포함

### 4-5. TurtleGate — 자동 차단 안전장치

**모든 트레이딩 capital_action은 `turtle_gate_clear` 없이는 실행될 수 없다.**

TurtleGate는 President Decision Agent가 아래 6개 항목을 자동 검증하는 메커니즘이다.
하나라도 누락/위반 시 자동으로 `turtle_gate_block`을 발행하고 진행을 중단한다.

```
[TurtleGate 체크리스트]
☐ 1. 진입 신호: System 1(20일 돌파) 또는 System 2(55일 돌파) 확인
☐ 2. ATR(N): 20일 Average True Range 계산값 명시
☐ 3. 포지션 리스크: 계좌 대비 ≤ 1% 확인
☐ 4. 손절가: 진입가 ± 2×ATR 계산 및 기록
☐ 5. 청산 시스템: System 1 또는 System 2 명시
☐ 6. Pre-Mortem: pre_mortem_approve 완료
☐ 7. Cross-LLM 신호 게이트: INVESTMENT_THESIS_TEMPLATE 섹션 8 통과 (2-of-3 approve)

→ 전부 통과: turtle_gate_clear 발행 → capital_action 진행 가능
→ 하나라도 실패: turtle_gate_block 발행 → 진행 즉시 중단
```

### 4-6. 신호→주문 변환 Cross-LLM 게이트

**투자 신호를 주문 의도로 변환하는 레이어는 단일 LLM 판단으로 처리할 수 없다.**

콘텐츠 산출물에 적용되는 2-of-3 cross-LLM 검증과 동등한 수준의 게이트를 신호→주문 변환에도 적용한다.

```
[신호→주문 Cross-LLM 게이트 절차]
1. 투자 thesis 초안 생성 (INVESTMENT_THESIS_TEMPLATE.md 기준)
2. 섹션 8 — Cross-LLM 게이트 실행:
   - Claude: 전략·논리·리스크 검토 → APPROVE / CONCERN / BLOCK
   - Gemini: 소스 교차검증, 수치·ATR 계산 확인 → APPROVE / CONCERN / BLOCK
   - GPT (선택): 판정 중재 → APPROVE / CONCERN / BLOCK
3. 2-of-3 APPROVE 달성 → gate_result: passed
4. BLOCK 판정 1개 이상 → CEO 확인 필수 (non-negotiable)
5. factual error / fabricated source / 법률 위험 → 자동 폐기

Non-negotiable finding (어느 모델 1개라도 발견 시 자동 폐기):
  - 존재하지 않는 ETF 티커
  - 잘못된 ATR 계산 (20% 이상 오차)
  - 자본시장법·외국환거래법 위반 가능성
  - turtle_gate 파라미터 누락
```

이 게이트는 `INVESTMENT_THESIS_TEMPLATE.md` 섹션 8과 연동되며, 게이트 결과 파일은 `docs/reports/llm_outputs/` 아래 저장한다.

---

## 5. CEO Override Protocol — 예외 처리 절차

> **원칙: TurtleGate는 CEO도 단독으로 해제할 수 없다.**

`turtle_gate_block` 상태에서 대표(CEO)가 강제 진행을 결정하려면 아래 절차를 반드시 따른다.

### 5-1. `trading_turtle_override` 발행 요건

다음 4가지가 모두 기재되어야만 유효한 override로 인정된다:

```
[trading_turtle_override 필수 기재 항목]
1. 위반 항목: 어떤 Turtle 규칙을 어기는지 명확히 기술
   예: "System 2 진입 신호 없이 포지션 오픈"

2. 구체적 이유: 규칙을 우회하는 근거
   예: "시장 구조 변화로 인한 일시적 신호 지연 판단"

3. 잔여 리스크 인정:
   - 예상 최대 손실 금액 기재
   - "이 결정으로 인한 손실은 시스템 외 판단에 의한 것임을 인정한다"
   
4. 날짜 + 대표 명의:
   - 발행 날짜 (ISO 8601)
   - CEO 명의 (성명 기재)
```

### 5-2. Override 기록 위치

`trading_turtle_override`는 다음 경로에 파일로 저장 후 `docs/reports/ar_tracker.jsonl`에 등록한다:

```
docs/trading/overrides/YYYY-MM-DD_<ticker>_override.md
```

### 5-3. Override 후 의무

- Override 후 해당 포지션은 **일일 손익을 별도 추적**한다.
- 손실이 예상 최대 손실의 50%에 도달하면 Business Risk Management Agent가 즉시 대표에게 알린다.
- Override 이력은 분기별 Red Team 검토 대상에 포함된다.

### 5-4. Override 남용 방지

연속 3회 이상 `trading_turtle_override`가 발행되면:
- Business Risk Management Agent가 `risk_escalation_note`를 발행한다.
- CFO Agent가 해당 기간의 override 트레이드 손익을 별도 집계한다.
- 대표는 "시스템 복귀 또는 시스템 개정" 중 하나를 명시적으로 선택해야 한다.

---

## 6. Phase 2 포지션 사이징 후보 — Half-Kelly

> **상태**: 검토 대기 (2026-05-27 CEO 결정). 현재는 1% 고정룰 유지. 실데이터 충분 후 적용.

### 개요

Half-Kelly Criterion은 Kelly 공식으로 산출된 최적 베팅 비율의 50%를 사용하는 포지션 사이징 기법이다.

- Full Kelly 대비 변동성 50% 감소, 수익 약 75% 유지
- 과도한 리스크 노출 없이 장기 복리 성장 최적화

### Turtle Trading과의 결합 방식

Turtle 시스템의 **진입·청산·손절 규칙은 그대로 유지**하고, 포지션 사이징 공식에만 Half-Kelly를 적용한다.

**현재 (Phase 1)**:
```
포지션 단위 = (계좌 × 1%) ÷ (ATR × 주가)
```

**Phase 2 후보**:
```
Full Kelly  = (평균손익비 × 승률 - 패률) ÷ 평균손익비
Half Kelly  = Full Kelly ÷ 2
포지션 단위 = (계좌 × Half-Kelly%) ÷ (ATR × 주가)
```

### 적용 조건 (Phase 2 진입 전 충족 필요)

| 조건 | 기준 |
|---|---|
| 트레이드 샘플 수 | 최소 30회 이상 |
| 승률 추정 신뢰도 | 95% 신뢰구간 ±5% 이내 |
| 평균 손익비 산출 | 실거래 데이터 기반 (백테스트 아닌 실데이터 우선) |
| CEO 승인 | Half-Kelly 파라미터 확정 후 별도 capital_action 승인 |

### 예상 도입 시점

2026년 9월 이후 (Live 전환 후 3개월 실데이터 확보 후 재검토)

---

## 7. 참고 자료

- [Investopedia — Turtle Trading Strategy](https://www.investopedia.com/articles/trading/08/turtle-trading.asp)
- [TrendSpider — Turtle Trading Knowledge Base](https://trendspider.com/learning-center/the-turtle-trading-strategy/)
- 원천 링크: https://share.google/aimode/tZ9c8wHdjLvNG41dB

---

## 8. 변경 이력

| 날짜 | 버전 | 내용 | 작성자 |
|------|------|------|--------|
| 2026-05-25 | 1.0 | 초안 작성 — Turtle Trading 5대 원칙 전면 정의 | Copilot (대표 지시) |
| 2026-05-27 | 1.1 | §6 추가 — Half-Kelly Phase 2 포지션 사이징 후보 등록 (CEO 결정) | Claude (Sonnet 4.6) |
