# Sales Playbook
# Version: 1.0
# Date: 2026-05-10
# Owner: Sales Agent

---

## 1. Purpose

이 문서는 `Physical AI Weekly`의 *paid funnel 운영*과 *custom memo lead 처리* 절차를 정의한다.

핵심 원칙:

- 익명 고객 self-service funnel (관계 기반 영업 X)
- 가격/할인/환불 정책 변경은 Product Planning + Legal Counsel + 대표 승인
- 단독 paid offer 발송 금지 (`legal_review_approve` + `qa_clear` 필수)
- subscriber 개인정보의 평문 공유 금지

상위 정책: `docs/strategy/MONETIZATION_STRATEGY.md`, `docs/strategy/PRICING.md`, `docs/strategy/MARKETING_STRATEGY.md`.

---

## 2. Funnel Stages

```
Awareness
   ↓
Free Subscriber (newsletter sign-up)
   ↓
Trial / Discounted First Month
   ↓
Paid (active subscriber)
   ↓
Retained (3+ months)
   ↓
(Optional) Custom Memo Lead
```

각 단계 사이에 *측정 가능한 conversion 신호*를 둔다.

| 단계 | 정의 | 핵심 신호 |
| --- | --- | --- |
| Awareness | newsletter URL 노출 | impression, X profile click |
| Free | email 등록 | sign-up event |
| Trial | 첫 paid 결제 또는 trial 시작 | first charge or trial_start |
| Paid | trial 종료 후 지속 결제 | second charge |
| Retained | 3개월 연속 결제 | third+ charge |
| Custom Memo Lead | 영문 또는 specific 의뢰 inbound | memo inquiry |

---

## 3. Conversion Mechanics

### 3.1 Awareness → Free

Owner: Subscriber Growth Agent (Marketing Strategy 실행 arm)

방법:
- 매 weekly issue를 publicly accessible로 발행 (sample preview)
- X thread / community post에서 newsletter URL 노출
- footer에 "구독하면 매주 받기" CTA

KPI:
- profile/post → sign-up rate (목표: 5%+)
- sign-up form abandonment rate (목표: 30% 이하)

### 3.2 Free → Trial / Paid

Owner: Sales Agent

trigger:
- free reader가 4회 이상 issue open한 경우 paid tier 노출 강화
- specific signal에 reply한 reader는 personalized paid offer 후보
- (단, *대표 또는 부대표의 주변 인맥인지* 확인 → 인맥이면 권유 *제외*)

paid 노출 방법:
- weekly issue 마지막 단락에 paid tier preview (1개 paid-only signal teaser)
- monthly에 1회 standalone paid invitation email
- 결제 페이지: 단순/명료, disclaimer 포함 (`docs/operations/LEGAL_REVIEW_PLAYBOOK.md §7.3`)

### 3.3 Trial → Paid

trigger:
- trial 종료 3일 전 reminder
- trial 중 engagement 낮은 경우 (open <40%) 추가 가치 제공 시도 (paid-only memo 발췌 등)

### 3.4 Paid → Retained

retention 활동:
- 매월 1회 reader-only Q&A 또는 quick poll
- 분기 1회 reader-driven topic 발행
- 환불/취소 직전 short exit interview (1 question: "어떤 가치가 부족했나요?")

### 3.5 Retained → Custom Memo Lead

trigger:
- retained subscriber 중 specific question 답장한 경우
- 영문 reader가 "consulting" 또는 "deep dive" 키워드로 inbound

처리:
- Sales Agent가 lead qualification (Persona D 점검)
- 가격 제안 ($300 default per `docs/strategy/PRICING.md`)
- *Legal review* + *Pre-Mortem* (첫 발송 시) 후 발송

---

## 4. Pricing Experiments

### 4.1 Baseline (Phase 1 default)

per `docs/strategy/PRICING.md`:
- Free: weekly issue
- Paid individual: 월 ₩9,900
- Paid supporter: 월 ₩19,900
- Custom memo: ₩300,000 또는 $300

### 4.2 Allowed Experiments (대표 승인 + Legal review 필수)

- 첫 달 50% 할인 (₩9,900 → ₩4,950, 1개월 한정)
- annual 결제 2개월 무료 (₩99,000/년, 정상 ₩118,800)
- custom memo bundle (3건 ₩750,000)

### 4.3 Forbidden Without Approval

- 가격 영구 인하 (대표 승인 + Pre-Mortem)
- 가격 인상 (대표 승인 + 기존 subscriber 사전 공지 30일)
- 무한 무료 trial 또는 freemium 구조 변경
- 환불 거부 정책 변경 (한국 소비자보호법 7일 보호 유지 의무)
- gift / referral inducement (legal review)

### 4.4 Experiment 운영

각 가격 실험은 *Pre-Mortem 첨부* 후 진행:
- 시작/종료 일시 명시
- 대상 cohort (신규 only / all)
- 성공 지표 (전환율, LTV, churn)
- 실패 시 rollback plan

A/B 테스트는 동시 2개 가격을 노출하지 않는다 (한국 표시광고법 risk). 시간 분리 (전후 비교) 또는 random cohort 분리.

---

## 5. Onboarding Sequence

paid subscriber가 첫 결제 후 받는 sequence (자동화).

| Day | 메시지 | 목적 |
| --- | --- | --- |
| 0 | 환영 + 첫 paid issue archive link | 즉시 가치 전달 |
| 1 | "어떻게 활용하고 계신가요?" 1-question survey | 초기 engagement |
| 7 | 가장 reaction 강한 historical issue 1건 | 가치 강화 |
| 14 | trial 종료 알림 (해당 시) | conversion timing |
| 30 | "1개월 review" reader-only Q&A invite | retention seed |

각 message는 QA Agent의 `qa_clear` 통과한 template 사용.

---

## 6. Retention / Churn Management

### 6.1 Churn 조기 신호

- 3주 연속 issue not opened
- payment method 만료 임박
- 환불 cancellation page 진입
- support 문의 미해결

신호 발견 시 Sales Agent가 personalized re-engagement (자동 + 옵션). 단, 인맥이면 *수동 처리* 안 함.

### 6.2 Cancel 시도 단계

- step 1: cancel 클릭 → "어떤 점이 기대와 달랐나요?" (1 question, optional)
- step 2: 1-month pause 옵션 제안 (cancel 대신)
- step 3: cancel 확정 → 즉시 처리, 7일 환불 권리 안내
- step 4: 1주일 후 short exit follow-up (감정 없는 1 question)

### 6.3 Refund 처리

- 디지털 콘텐츠 7일 환불 보장 (한국 소비자보호법)
- 7일 이후 환불 요청은 case-by-case (default: 거절, 단 reasonable한 경우 처리)
- 환불 사유 기록 (churn analysis 데이터)
- chargeback 발생 시 즉시 Legal Counsel notify

---

## 7. Custom Memo Lead Qualification

영문 또는 specific 의뢰 inbound 시.

### 7.1 Qualification 체크

| 질문 | 통과 기준 |
| --- | --- |
| 발신자가 부대표/대표 인맥인가? | No (인맥이면 거절 또는 무료 일회 답변) |
| 의뢰 주제가 도메인 내인가? (Physical AI / robotics / semiconductor / AGI / 자동화) | Yes |
| 의뢰가 *투자 자문* 또는 *주식 매매 추천*을 요구하는가? | No (legal block) |
| 시간 산정 가능한가? (5 business day 내) | Yes |
| 가격 ($300) 수용 가능한가? | Yes |

### 7.2 Memo 작성 흐름

1. Sales Agent가 lead 접수 + qualification
2. Editor가 outline 작성
3. Codex/Claude가 evidence 수집 + draft
4. 부대표 readability review (영문이면 cross-LLM fluency check)
5. Red Team cross-LLM verification
6. Legal Counsel review (`legal_review_approve`)
7. Pre-Mortem 첨부 (첫 memo는 full, 이후 abbreviated 가능)
8. QA Agent `qa_clear`
9. 대표 승인
10. PDF 또는 Notion link 형태로 발송 + invoice
11. 결제 확인 후 자료 access 활성화

### 7.3 가격 협의

- $300이 default. 협상 *없음* (Phase 1)
- 더 큰 scope (deep memo) 의뢰 시 $1,500~ project로 분리 (`docs/strategy/PRICING.md` roadmap)
- 협상 요청 시 거절 또는 standard $300으로 유도

---

## 8. KPIs and Triggers

| KPI | Phase 1 Target (30일) | Trigger if Missed |
| --- | --- | --- |
| 무료 → trial conversion | 10% | paid offer 카피 재작성 |
| trial → paid conversion | 50% | trial 가치 강화 또는 trial 폐지 검토 |
| 30-day churn | <30% | onboarding sequence 강화 |
| 90-day retention | >50% | 콘텐츠 가치 재정의 |
| custom memo response rate | inbound 의뢰 100% qualified 처리 | 1주 내 응답 자동화 |
| refund rate | <5% | 가격 또는 약속 가치 재검토 |
| chargeback rate | <0.5% | Stripe/PG review trigger |

trigger 발동 시 `docs/operations/WEEKLY_BUSINESS_REVIEW.md` cadence에 escalate.

---

## 9. Subscriber Data Handling

### 9.1 PIPA 준수

- email + 결제 메타데이터만 저장
- 결제 정보는 PG사 보유 (회사 직접 보관 X)
- marketing 동의는 별도 분리
- 탈퇴 시 즉시 anonymize 또는 30일 내 삭제

### 9.2 Slack에 노출 금지

- subscriber email 평문 X
- 결제 정보 X
- 환불 사유의 개인 식별 정보 마스킹

### 9.3 외부 도구 export

- 외부 분석 도구로 export 시 *반드시* PIPA 검토 + Legal Counsel 승인
- aggregated/anonymized 형태만 허용

---

## 10. Compliance Reminders

| 활동 | 필수 게이트 |
| --- | --- |
| 신규 paid offer 발송 | Legal + Red Team + Pre-Mortem + QA + 대표 |
| 가격 변경 | Product Planning + Legal + Pre-Mortem + 대표 |
| 환불 처리 | 7일 보장 + 사유 기록 |
| 기존 subscriber에게 가격 인상 공지 | 30일 전 + Legal review |
| 광고 캠페인 / promo code | Marketing + Legal + `capital_action_approve` |
| custom memo 첫 발송 | full Pre-Mortem + Legal + QA |
| chargeback 발생 | Legal Counsel notify + Sales rollback plan |

---

## 11. Quick Reference

| 상황 | 행동 |
| --- | --- |
| free subscriber가 paid 문의 | 결제 페이지 링크 전달, 영업 X |
| 인맥이 paid 가입 의사 표시 | 자발적 가입은 막지 않으나 직접 권유 X. 1회 자세한 설명만 OK |
| 영문 reader가 deep dive 요청 | Persona D 분류 → custom memo flow |
| 환불 요청 | 7일 내 자동 처리, 7일 후 case-by-case |
| 가격 인하 의견 받음 | Product Planning에 backlog item, 대표 결정 |
| 광고하고 싶다 | Marketing Strategy Phase 2 trigger 확인, 모든 게이트 통과 |
| 같은 가격을 두 그룹에 다르게 노출 | 표시광고법 risk → Legal review 필수 |
