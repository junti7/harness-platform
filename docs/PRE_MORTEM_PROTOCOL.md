# Pre-Mortem Protocol
# Version: 1.0
# Date: 2026-05-10
# Owner: President Decision Agent + Red Team Agent

---

## 1. Purpose

Pre-Mortem은 *결정을 내리기 전에 이미 실패했다고 가정하고 그 이유를 거꾸로 추적*하는 기법이다.

목적:

- Optimism bias 차단
- 평소 보이지 않는 worst-case 노출
- 회복 불가능한 결정의 사전 차단
- 대표가 30~60초 안에 *"이게 망하면 어떻게 되는지"*를 알고 결정하도록 보장

`pre_mortem_approve`는 high-impact 결정의 사전 조건이며, 미작성/부실작성 시 President Decision Agent는 decision card 생성을 *거부*한다.

---

## 2. When Required

다음 결정에는 Pre-Mortem이 *반드시* 첨부된다.

| 결정 유형 | Owner | 비고 |
| --- | --- | --- |
| paid offer 외부 발송 | Sales | 첫 발송 시 의무, 동일 offer 변형은 abbreviated 가능 |
| 외부 공개 claim (회사/제품/투자/예측) | Editor | 매번 |
| 광고 캠페인 집행 | Marketing | 예산/도달/duration 모두 명시 |
| 새 source 추가 | Evidence | scraping 범위 변경 시 |
| 데이터 정책 변경 | Engineering | 개인정보 처리 변경 시 |
| 가격 변경 | Product Planning | 인하/인상 모두 |
| 무료 → 유료 전환 (paywall 도입) | Product Planning | |
| 투자 thesis 발행 | Market & Investment | |
| capital action (비용/투자/계약) | President | 모든 capital action |
| 다국어 확장 | Product Planning | 새 언어 launch 시 |
| 외부 파트너십/계약 | President | |
| 부대표 또는 대표의 외부 인터뷰/소셜 발신 | President Office | brand-risk 평가 |

다음은 *abbreviated* (5분 짧은 버전) 가능:

- weekly issue 일반 발행 (반복 패턴, prior pre-mortem 적용)
- 기존 paid offer의 minor 카피 수정
- 동일 채널 동일 형식의 marketing 반복

---

## 3. Pre-Mortem Memo Template

```markdown
# Pre-Mortem Memo

- Date:
- Decision summary (1줄):
- Decision owner:
- Decision type: (paid_offer / claim / ad / source / pricing / capital_action / ...)
- Reversibility: reversible / partially / irreversible
- Required approvals: [legal_review_approve, red_team_clear, ...]

## Worst-Case Scenarios

### Scenario 1
- What happens:
- Probability: low / medium / high (이유)
- Max loss:
  - Financial: ₩
  - Legal/regulatory:
  - Reputational:
  - Time:
- Recovery: recoverable / partial / unrecoverable
- Mitigation (실행 전 차단):
- Detection trigger (실행 후 감지 신호):
- Response if triggered:

### Scenario 2
- (위 동일 구조)

### Scenario 3
- (위 동일 구조)

## Top mitigation actions (실행 전 적용)
- 1.
- 2.

## Trigger to halt or rollback (실행 후 감시)
- 1.
- 2.

## Decision
- [ ] pre_mortem_approve (대표 또는 owner 서명)
- [ ] pre_mortem_block (사유: )
- [ ] requires further review (다음 단계: )
```

---

## 4. Worst-Case Scenario Generation

각 결정에 대해 *최소 3개*의 worst-case scenario를 생성한다. 1개나 2개는 부족 — 인간은 첫 worst-case에 만족하고 멈추는 경향이 있다.

생성 방법 (LLM-assisted):

1. 결정 요약을 prompt로 주고 LLM에게 *"이 결정이 6개월 후 실패했다면 가장 그럴듯한 이유 5개"* 를 요청
2. 그중 발생 가능성이 의미 있는 3개 선택
3. 각 시나리오에 대해 *구체적*으로 작성 (추상 표현 금지)
   - 나쁜 예: "고객이 불만족"
   - 좋은 예: "첫 paid memo 발송 후 5명 중 3명이 환불 요청, 2명은 환불 거부 시 SNS 공개적 비판"
4. Cross-LLM red team이 추가 시나리오 1개를 *반드시* 더 제안 (기존 3개와 다른 관점)

시나리오 다양성 체크:

- 최소 1개는 *법률/규제* 관련
- 최소 1개는 *재무/현금* 관련
- 최소 1개는 *평판/관계* 관련
- 가능하면 *기술/운영 실패* 관련 1개

---

## 5. Probability Calibration

Probability는 정량 추정이 어려우므로 다음 anchor를 사용한다.

| Label | Frequency anchor | Examples |
| --- | --- | --- |
| Low | 1년에 1회 미만 | 외부 변호사 사건, 큰 자본 손실 |
| Medium | 분기 1~2회 | 환불 요청, 카피 오해, 구독 취소 spike |
| High | 매월 발생 가능 | 가벼운 컴플레인, 일부 reader 이탈 |

Bias 방지:

- "내가 잘 하면 안 일어남"이라는 생각이 들 때 한 단계 *올린다*.
- LLM이 "low"라고 했을 때 인간이 "medium"으로 의심할 만한 근거가 있으면 medium으로 기록.
- 한국 법률/규제 환경은 *중간 정도 strict*하다고 가정 (US보다 strict, EU보다 less strict).

---

## 6. Loss Type Taxonomy

### 6.1 Financial loss

- 환불액
- 광고/contractor/외부 변호사 비용
- 결제 수수료 손실 (chargeback fee)
- 매출 기회비용

단위: ₩ 명시. "큰 손실" 같은 모호 표현 금지.

### 6.2 Legal/regulatory loss

- 과태료/벌금 가능성
- 자본시장법 위반 시 *유사 투자자문업* 신고 위험
- 표시광고법 시정명령
- 소송 (소액이라도 시간/관심 비용)

### 6.3 Reputational loss

- SNS 부정 노출
- 구독자 trust 하락 (open rate 즉각 감소)
- 향후 partnership 거절
- 향후 채용/투자 유치 시 검색되는 흔적

심각도 anchor:

- Mild: 일부 구독자 불만 (recoverable in 1주)
- Medium: SNS 공개 비판 spread (recoverable in 1~3개월, 사과/수정 필요)
- Severe: 미디어 보도 또는 공식 항의 (recoverable >6개월 또는 unrecoverable)

### 6.4 Time loss

- 사후 수습 시간 (재발행, 환불 처리, 약관 재작성)
- 외부 변호사 대응 시간
- 재발 방지 인프라 구축 시간

---

## 7. Recovery Level

| Level | 정의 | 대응 |
| --- | --- | --- |
| Recoverable | 1주 이내 사과/수정/환불로 회복 | 기본 mitigation 충분 |
| Partial | 1~3개월 시간 들임. 일부 trust/매출 영구 손실 | 사전 차단 강화 + 발생 시 즉각 대응 plan 필수 |
| Unrecoverable | 회복 불가 (법적 처벌, 평판 영구 손상, 자본 영구 손실) | *결정 자체를 재고*. 또는 외부 변호사 + 단계적 진행 |

Unrecoverable risk가 medium 이상 확률로 존재하면 *기본적으로 block*하고 mitigation으로 risk를 떨어뜨린 후 재제출한다.

---

## 8. Mitigation Categories

### 8.1 사전 차단 (실행 전)

- 결정 범위 축소 (전체 발송 → 10명 한정 trial)
- A/B 테스트로 작게 시작
- disclaimer / 동의 문구 추가
- 외부 검토 (변호사 / 도메인 전문가)
- 자동 rollback 가능한 형태로 launch

### 8.2 발생 후 대응 (탐지 + 회복)

- 24시간 내 사과/수정 plan
- 환불 정책 사전 명시
- 고객 직접 연락 채널
- 미디어 대응 한 줄 statement 사전 준비

---

## 9. Detection Trigger (실행 후 감시)

worst case가 *발생 중*임을 알게 되는 신호를 정의한다. 신호 없이는 사후 대응이 늦는다.

예시:

- 24시간 내 환불 요청 N건 이상 → halt offer
- SNS 부정 멘션 N건 이상 → 사과/수정 statement
- open rate 30% 이하 → next issue 전 카피 재검토
- 외부 변호사 cease-and-desist 수신 → 즉시 발송 중단 + 외부 변호사 자문
- 결제 chargeback 비율 1% 초과 → Stripe/Paddle review trigger

---

## 10. Approval Flow

```
Decision proposed
    ↓
Pre-Mortem memo 작성 (owner + LLM-assisted)
    ↓
Cross-LLM red team이 시나리오 1개 추가
    ↓
Legal Counsel review (법률 시나리오 점검)
    ↓
대표 (또는 owner) decision:
    - pre_mortem_approve → 다음 approval로 진행
    - pre_mortem_block → 결정 보류, mitigation 강화 후 재제출
    - requires_further_review → 외부 자문 또는 대기
```

President Decision Agent는 pre-mortem 미첨부 시 decision card 생성을 *거부한다*.

---

## 11. Worked Examples

### Example A: 첫 paid memo $300 발송

**Decision**: 첫 inbound 영문 lead 1명에게 paid memo $300 발송. 주제: 한국 robotics 스타트업 5개 시장 평가.

**Worst-case 1 (legal)**:
- What: 평가에 "투자 가치" 표현 포함 → 자본시장법 유사 자문업 의심
- Probability: low (1번 단발성)
- Max loss: 외부 변호사 자문 ₩2M, 표현 수정 후 재발송
- Recovery: recoverable
- Mitigation: §7.3 disclaimer 강제, "투자 권유 아님" 명시
- Detection: 고객 또는 제3자가 "투자 자문 받았다"고 표현하는 경우

**Worst-case 2 (reputational)**:
- What: 평가받은 회사 중 1곳이 발견하고 "비방"이라며 항의
- Probability: low~medium (회사명 명시 시 medium)
- Max loss: SNS 공개 항의, 사과/수정, 일부 reader 이탈
- Recovery: partial
- Mitigation: 사실 기반 + 출처 명시 + 비교 시점 명시 (§4.6)
- Detection: 24시간 내 회사 또는 PR 담당의 직접 연락

**Worst-case 3 (financial)**:
- What: 고객이 환불 요청 + chargeback
- Probability: low
- Max loss: $300 + chargeback fee $25
- Recovery: recoverable
- Mitigation: 환불 정책 사전 명시, 7일 환불 보장
- Detection: 결제 후 7일 내 refund/chargeback 신호

**Decision**: pre_mortem_approve (대표) + 위 3가지 mitigation 모두 적용 후 발송.

---

### Example B: weekly issue에서 특정 회사의 IPO 시점 예측 표현 포함

**Decision**: 이번 주 issue에서 "Figure AI는 2026년 안에 상장할 가능성이 높다" 표현 포함.

**Worst-case 1 (legal)**:
- What: 특정 회사 주식 매매 권유로 해석 가능
- Probability: medium (단정적 표현 사용 시)
- Max loss: 자본시장법 시정 또는 자문업 신고 의심
- Recovery: partial
- Mitigation: 표현을 "보도된 funding 패턴은 2026~2027 IPO 가능성을 시사한다 (출처: ...)"로 변경
- Detection: 독자/외부 항의

**Worst-case 2 (reputational)**:
- What: 예측이 틀림 → "이 newsletter는 부정확하다"는 인식 확산
- Probability: high (예측 본질상)
- Max loss: 신뢰도 하락
- Recovery: partial (다음 issue에서 self-correction memo로 일부 회복)
- Mitigation: 예측이 아닌 "현재 신호 해석"으로 framing
- Detection: open rate 감소 또는 reader 직접 피드백

**Worst-case 3 (factual)**:
- What: Figure AI 측이 직접 "사실 아님" 항의
- Probability: low
- Max loss: 사과/수정 issue 발행
- Recovery: recoverable
- Mitigation: 회사명 + 출처 + 시점 명시, "출처 보도 기반" disclaimer
- Detection: 직접 연락 or PR statement

**Decision**: pre_mortem_block. 표현을 "투자/예측"이 아닌 "신호 해석"으로 재작성한 후 재제출.

---

## 12. Quick Reference

| 결정 종류 | Pre-Mortem 필수 | abbreviated 가능 |
| --- | --- | --- |
| paid offer 첫 발송 | Yes (full) | No |
| 동일 paid offer 카피 minor 수정 | Yes (abbreviated) | Yes |
| weekly issue 일반 발행 | abbreviated (반복 적용) | Yes |
| 새 카테고리 issue 처음 발행 | Yes (full) | No |
| 광고 캠페인 (어떤 예산이든) | Yes (full) | No |
| capital action (모든 비용) | Yes (full) | No |
| 가격 인상 | Yes (full) | No |
| 가격 인하 (할인) | Yes (full) | No |
| 다국어 launch | Yes (full) | No |
| 외부 인터뷰 | Yes (full) | No |
