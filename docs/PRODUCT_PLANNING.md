# Product Planning
# Version: 1.1
# Date: 2026-05-10
# Owner: Product Planning Agent

---

## 1. Purpose

이 문서는 `Physical AI Weekly` 및 후속 상품의 *정의, 패키징, 가격 ladder, 기능 우선순위*를 관리한다.

핵심 원칙:

- 단일 wedge로 시작 (Phase 1 = `Physical AI Weekly` only)
- 기능 추가는 *subscriber feedback과 paid 전환 신호*가 만든다 (CEO 직관 X)
- 가격/패키징 변경은 Product Planning + Legal Counsel + 대표 승인
- 다국어 확장은 `docs/governance/LANGUAGE_POLICY.md` Phase 진입 조건 충족 시에만
- paid product는 부대표와 비전문가 독자의 이해 허들을 통과해야 한다. 기술을 모르는 주부, 일반 직장인, 초보 투자자 persona가 핵심 내용을 이해하지 못하면 유료 발행 금지.
- 공개 샘플만으로 벤치마킹이 부족할 경우, 대표 승인과 Legal/Pre-Mortem을 거쳐 경쟁사 유료 구독을 한시적으로 구매할 수 있다.

상위 정책: `docs/strategy/MONETIZATION_STRATEGY.md`, `docs/strategy/PRICING.md`, `docs/governance/LANGUAGE_POLICY.md`.

---

## 2. Phase 1 Product Definition

### 2.1 Product

`Physical AI Personal Intelligence Brief`

### 2.2 Promise

매주 Physical AI / AGI / robotics / semiconductor / aerospace / 자동화 영역의 고순도 신호를 고객별 관심사, 이해 수준, watchlist와 연결해 한국어와 영어로 제공한다.

Phase 1에서는 한국어 master를 우선하되, 유료 상품에는 영어판 또는 영어 executive summary를 반드시 포함한다. 기타 언어는 별도 시장성과 QA 가능성을 검토한 뒤 대표 승인으로만 추가한다.

### 2.3 Non-Promise (명시적 제외)

- 투자 수익 보장
- 모든 뉴스 coverage
- 실시간 알림
- 검증되지 않은 기술 claim
- 주식/코인 매매 추천 (자본시장법 risk)
- 특정 회사의 매수/매도 권유

### 2.4 Format

| 요소 | Free Tier | Paid Tier |
| --- | --- | --- |
| 발행 주기 | 주 1회 | 주 1회 또는 월 1회 deep brief |
| 언어 | 한국어 | 한국어 + 영어 필수 |
| 신호 개수 | 3~5개 | 고객 관심사 기반 핵심 신호 + watchlist |
| 길이 | 짧은 공개 브리프 | 고객별 personalized brief + PDF/웹 |
| 영문 출처 링크 | 포함 | 포함 |
| 한국/글로벌 implication | 한국어 중심 | 한국어 + 영어, 필요 시 글로벌 관점 |
| reader Q&A | 없음 | 고객 질문 1개 이상 반영 |
| watchlist | 약식 | 고객별 회사/기술/지표 watchlist |
| archive 접근 | 공개 archive | 고객별 web portal / PDF archive |

### 2.5 Language Requirement

- 무료 발행: 한국어 primary. 영어 요약은 optional.
- 유료 발행: 한국어와 영어가 모두 포함되어야 한다.
- 영어판은 단순 기계번역이 아니라 QA/Legal/Red Team을 통과한 별도 edition이어야 한다.
- 일본어, 중국어, 스페인어 등 추가 언어는 native/cross-LLM QA와 수요 검증 없이는 발행하지 않는다.
- 자세한 언어 정책은 `docs/governance/LANGUAGE_POLICY.md`를 따른다.

### 2.6 Vice President / Non-Expert Hurdle

유료 상품은 부대표 또는 비전문가 주변인 persona의 허들을 통과해야 한다.

통과 기준:

| 기준 | 설명 |
| --- | --- |
| One-line clarity | 첫 1분 안에 "이 보고서가 무엇을 해주는지" 이해 |
| Jargon barrier | 어려운 용어는 즉시 쉬운 설명 동반 |
| Investor relevance | 투자 관련 의미는 이해되지만 매수/매도 권유처럼 보이지 않음 |
| Watchlist utility | 어떤 회사/기술을 계속 봐야 하는지 알 수 있음 |
| Trust | 과장, 사기성, 근거 없는 예측처럼 보이지 않음 |
| Pay reason | 무료 글과 유료 상품의 차이가 느껴짐 |

부대표가 `hard_to_understand` 또는 `not_payworthy`로 판단하면 유료 발행은 `qa_block` 처리한다.

### 2.7 Competitive Benchmarking Source Policy

Product Planning Team은 경쟁사 공개자료와 공개 샘플을 Library에 축적한다.

공개자료가 부족한 경우:

- `docs/reports/PAID_COMPETITOR_SUBSCRIPTION_APPROVAL_PACKET_2026-05-10.md`에 따라 대표 승인 요청
- 비용 집행은 `capital_action_approve`
- Legal review와 Pre-Mortem 필수
- 유료 자료는 전문 저장/재배포 금지
- report anatomy, delivery UX, quality bar만 기록

---

## 3. Free vs Paid Tier 분리 원칙

### 3.1 Free Tier 가치

- 매주 *충분한* 핵심 신호 받기 → reader가 "이거 무료라니" 느낌
- *소문*과 *공유*의 매개체
- 최소한의 한국 시장 implication 포함

### 3.2 Paid Tier 가치

paid 전환을 정당화하는 *3가지 차별*:

1. **추가 deep dive**: 매주 1개 신호에 대해 free보다 2배 분량의 분석 (가치 사슬, 경쟁 구도, 한국 산업 angle)
2. **paid-only memo**: 월 1~2건의 specific 회사/기술 short memo (1~2 page)
3. **archive 전체 access**: free는 최근 4주만, paid는 전체

### 3.3 분리 원칙

- *quality* difference (free가 부실하면 안 됨)이 아니라 *depth + access* difference
- free reader가 paid를 *원하게* 만드는 구조 (free에서 일부 paid 콘텐츠 preview)

---

## 4. Pricing Ladder

per `docs/strategy/PRICING.md`.

### 4.1 Active

| Product | Price | Status |
| --- | --- | --- |
| Free weekly issue | ₩0 | Active |
| Paid individual subscription | ₩9,900/month | Active |
| Paid supporter subscription | ₩19,900/month | Active (optional, no extra benefit beyond support) |
| Custom Physical AI Memo | ₩300,000 또는 $300 | Active (inbound only) |

### 4.2 Roadmap (Phase 2+)

| Product | Starting Price | Trigger |
| --- | --- | --- |
| Annual subscription discount | ₩99,000/year | paid 50명 이후 |
| Bespoke B2B research | ₩2,000,000+/project | inbound corporate 의뢰 5건 이후 |
| Corporate strategy subscription | ₩499,000/month | corporate inbound 3건 이후 |
| Physical AI market map | ₩500,000/report | reader survey 입증 |
| Technical due diligence support | ₩2,500,000+/project | VC/founder inbound 시 |

각 roadmap product는 active 진입 전 Pre-Mortem + Legal review + 대표 승인.

---

## 5. Feature Decision Process

### 5.1 Feature 추가 trigger

다음 신호 중 *2개 이상* 있을 때만 새 feature backlog 진입:

- subscriber feedback에서 동일 요청 3회 이상
- churn exit interview에서 동일 사유 3회 이상
- paid 전환 hesitation에서 동일 장애물 3회 이상
- 경쟁사 (SemiAnalysis 등) feature를 reader가 자발 인용 2회 이상

CEO 직관만으로 feature 추가 *금지*.

### 5.2 Backlog Priority

| Priority | 정의 | 예시 |
| --- | --- | --- |
| P0 | 매출 직접 영향 | paid teaser 위치 변경, 결제 페이지 단순화 |
| P1 | retention 직접 영향 | onboarding sequence, archive UX |
| P2 | acquisition 보조 | sample issue 공개, SEO 메타 |
| P3 | optional / nice-to-have | 색상 커스텀, 발행시간 옵션 |

### 5.3 A/B Test Backlog

Phase 1에서 검증할 hypothesis (가설 우선):

1. paid teaser를 issue *상단*에 두면 conversion이 더 높은가?
2. issue 제목 길이 (짧은 vs 긴) 어느 쪽 open rate 높은가?
3. 한국 시장 implication을 *맨 처음*에 두면 share rate 높은가?
4. paid tier에 deep dive를 *완전 가림* vs *teaser 노출* 어느 쪽 전환 높은가?
5. 발행 시간 (금요일 오전 vs 일요일 저녁) 어느 쪽 open 높은가?

각 test는 동시 2가지 가격 노출 *금지* (한국 표시광고법 risk). 시간 분리 또는 random cohort.

### 5.4 Feature Decision Flow

```
Hypothesis (3 signals 이상)
    ↓
Product Planning Agent backlog 진입
    ↓
대표 priority confirm
    ↓
A/B test design (필요 시)
    ↓
Legal review (가격/약관 변경 시)
    ↓
Implementation (Codex)
    ↓
Pre-Mortem (high-impact 시)
    ↓
QA gate
    ↓
Launch
    ↓
2주 후 결과 review → Backlog 또는 Cleanup
```

---

## 6. Subscriber Feedback to Backlog Pipeline

### 6.1 Feedback 수집 채널

- newsletter platform reply
- X mentions / DM
- weekly issue 내 1-question survey (선택적)
- monthly retention survey
- churn exit interview

### 6.2 분류

부대표가 1차 분류:
- "공감대 있음" (3+ subscriber 동일 의견)
- "1회성" (신경 쓰지 말 것)
- "Persona 외" (target audience 외 의견)

### 6.2.1 Customer Memory Accumulation

모든 고객 feedback은 일회성 comment로 끝내지 않는다. 다음 DB 객체에 누적한다.

| Data | Table | Purpose |
| --- | --- | --- |
| 고객 기본 profile | `customer_profiles` | 언어, 지식수준, tier, consent |
| 고객 event / feedback | `customer_memory_events` | 클릭, 답장, 혼란, hesitation, 요청 누적 |
| 관심사 | `customer_interest_tags` | 주제별 weight 관리 |
| watchlist | `customer_watchlists` | 회사/기술/지표 추적 |
| 질문 | `customer_questions` | 다음 리포트에서 답변해야 할 질문 |
| 상품 개선 | `product_upgrade_events` | 고객 feedback으로 상품이 어떻게 바뀌었는지 기록 |
| 산출물 참조 이력 | `artifact_memory_usage` | 특정 report가 어떤 memory를 반영했는지 QA 증빙 |

저장 금지:

- 보유종목
- 매수/매도 계획
- 목표 수익률
- 자산규모
- 민감 개인정보
- 동의 없는 personalization data

### 6.3 Product Planning Agent 처리

분류 후 Product Planning이 backlog item 작성:

```markdown
# Backlog Item

- Source: subscriber feedback / churn / hypothesis
- Persona affected:
- Frequency:
- Proposed feature:
- Cost to implement:
- Expected impact: P0/P1/P2/P3
- Hypothesis:
- A/B testable?
```

### 6.3.1 Upgrade Reuse Rule

고객 feedback에서 나온 개선사항은 해당 상품에만 머무르지 않는다.

Product Planning Agent는 각 `product_upgrade_events`에 대해 다음을 기록한다.

- 어떤 feedback/memory에서 나온 개선인지
- 어떤 상품에 적용했는지
- 다른 상품에도 적용 가능한지
- 적용 후 metric 변화가 있었는지
- 다음 QA에서 확인해야 할 항목

예:

| Feedback | Upgrade | Apply to |
| --- | --- | --- |
| "용어가 어려움" | beginner glossary block 추가 | free issue, paid brief, OJT |
| "어떤 회사를 봐야 할지 모르겠음" | watchlist table 추가 | paid brief, custom memo |
| "투자 의미가 흐림" | scenario map + legal-safe 투자 관련성 섹션 | paid brief, market map |
| "영문 자료가 필요함" | English executive summary 추가 | paid brief, custom memo |

### 6.4 대표 weekly review에 포함

매주 월요일 BR에 backlog top 3 보고. 대표가 priority 결정.

---

## 7. Roadmap Product Considerations

### 7.1 Bespoke B2B Research

- inbound corporate 의뢰 5건 누적 후 active 검토
- 가격 starting ₩2M+
- 1건당 5~10 business day
- legal 부담 큼 (회사 분석 시 부정경쟁방지법, 비공개 정보 risk)
- 대표 직접 작성 또는 외부 contractor `capital_action_approve`

### 7.2 Corporate Strategy Subscription

- 기업 단위 ₩499K/month
- *내용은 동일하지만 가격이 다른* 형태는 표시광고법 risk
- 차별: 기업 명의 결제 + multi-seat access + 분기 1회 internal Q&A
- Legal review 강화

### 7.3 Physical AI Market Map

- 분기 1회 ₩500K/report
- subscriber survey에서 "한 페이지 시장 지도" 요청 누적 시 검토
- 시각화 비용 + 데이터 검증 비용 고려

### 7.4 Technical Due Diligence

- VC/founder inbound 시 case-by-case
- 가격 ₩2.5M+/project
- 외부 변호사 자문 + Legal review 강화 (투자 자문 의심 매우 높음)
- 단독 실행 *금지* — 항상 대표 검토

각 roadmap product는 *paid subscriber 검증 후* 활성화 검토.

---

## 8. Compliance with Other Docs

| 결정 유형 | 필수 게이트 |
| --- | --- |
| 가격 인상/인하 | Product Planning + Legal Counsel + Pre-Mortem + 대표 |
| 새 product launch | Product Planning + Marketing + Legal + Pre-Mortem + 대표 |
| 환불 정책 변경 | Legal Counsel + 대표 |
| 약관 변경 | Legal Counsel + Pre-Mortem (subscriber 영향 클 시) + 대표 |
| 다국어 확장 | `docs/governance/LANGUAGE_POLICY.md` Phase 진입 조건 |
| 기능 제거 | subscriber 사전 공지 14일 + Pre-Mortem |

---

## 9. Anti-Patterns

다음 패턴 *금지*:

- 기능 폭주 (feature creep) — 매주 새 feature 추가
- 가격 빈번 변경 — subscriber 신뢰 하락
- 무조건 free tier 강화 — paid 정당성 약해짐
- 무조건 paid tier 강화 — free 가치 약해져 acquisition 약화
- 같은 가격 두 가지로 동시 노출 (표시광고법)
- "곧 추가됩니다" 약속 (Legal: 미확정 약속 risk)
- competitor feature 무조건 따라하기

---

## 10. Quick Reference

| 상황 | 행동 |
| --- | --- |
| 새 feature 아이디어 떠올랐다 | 3 signal 누적 확인 → backlog → 대표 priority |
| 가격 인하 요청 받음 | Backlog item, 대표 결정 (단독 X) |
| paid subscriber가 추가 기능 요청 | 1개월 누적 후 *동일 요청 3개 이상* 시 backlog |
| 새 product launch 검토 | Pre-Mortem + Legal + Marketing 협의 + 대표 |
| 다국어 확장 검토 | Phase 2 진입 5조건 확인 (`LANGUAGE_POLICY.md`) |
| free → paid 전환 낮음 | paid teaser / deep dive 차별 재정의 (Sales Playbook 협의) |
| churn 높음 | exit interview 분석 → backlog → onboarding/retention 강화 |
| competitor가 새 feature 출시 | *바로 따라하지 않음*. subscriber 의견 먼저 수집 |
