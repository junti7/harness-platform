# Monetization Strategy
# Version: 2.1
# Date: 2026-05-10

---

## 1. Strategic Choice

Harness는 Phase 1에서 B2B SaaS나 enterprise intelligence sales를 추구하지 않는다.

Phase 1 수익화 모델은 `Korean/English hybrid creator subscription`이다.

Benchmark category:

- solo/duo analyst newsletter
- paid creator subscription
- deep niche intelligence publication

Harness는 Stratechery, SemiAnalysis, Doomberg 같은 creator-intelligence model을 참고하되, 초기 시장은 한국어 Physical AI/AGI 독자로 좁힌다. 구체적인 경쟁사 가격과 매출 추정은 별도 검증 대상이며, 운영 문서에서는 참고 모델로만 사용한다.

---

## 2. Product

Product name: `Physical AI Weekly`

Free issue:

- 매주 1회 발행
- 5~7개 고순도 signal
- 한국어 요약과 해석
- 왜 중요한지
- 한국 산업/직장인/일반 독자 implication
- 과장 또는 반론

Paid tier:

- 더 압축된 signal digest
- paid-only memo 또는 archive access
- 독자 질문 기반 short answer
- 발행 후 follow-up note

Optional memo:

- inbound request가 있을 때만 제공
- 특정 회사/기술/시장 질문에 대한 custom memo

---

## 3. Pricing

Phase 1:

- Free: public weekly issue
- Paid individual: 월 ₩9,900
- Paid supporter/pro: 월 ₩19,900
- Optional memo: ₩300,000 또는 $300부터

Pricing rule:

- 첫 30일에는 가격을 복잡하게 만들지 않는다.
- paid subscriber 1명을 만드는 것이 목표다.
- 할인, 무료 trial, 후원형 결제는 대표 승인 후 실험한다.

---

## 4. Distribution

### Customer Reality

수익 창출 대상은 결코 부대표 또는 대표의 주변 인맥이 아니다. 주변 사람들에게 직접 결제 요청을 하지 않는다. 익명 독자가 마케팅을 통해 유입되는 구조로만 매출을 인정한다.

이 원칙은 Marketing Strategy Team, Subscriber Growth Agent, Sales Agent 모두에 동일하게 적용된다.

Primary distribution:

- Substack primary. Welcome page, Notes, Recommendations, subscriber dashboard, welcome email, Chat, Sections를 growth system으로 사용
- X/Twitter, LinkedIn, 한국 tech community (geeknews, disquiet, 클리앙 IT 등)에 organic 발행
- SEO 기반 brand keyword (Physical AI 한국어, 임바디드 AI, 휴머노이드 분석 등)
- referral / share via reader

Substack 운영 세부 규칙은 `docs/operations/SUBSTACK_SYSTEM_PLAYBOOK.md`를 따른다.

Not primary (Phase 1):

- B2B cold outreach
- enterprise sales
- 부대표/대표 주변 인맥 동원
- dashboard sales

Paid acquisition:

- 광고 예산 집행은 `capital_action_approve` + `legal_review_approve` + `pre_mortem_approve` 사전 조건 필수
- Phase 1 default: $0 paid spend

### Marketing Strategy

상세 채널/persona/카피 설계는 `docs/MARKETING_STRATEGY.md` (Marketing Strategy Team owns)에서 다룬다.

핵심 원칙:

- 익명 고객 acquisition 전제
- channel mix: organic content > community seed > SEO > (선택적) paid
- persona: Physical AI 호기심 있는 한국어 독자, 일부 영문 독자 (memo 의향)
- 모든 외부 발신 카피는 Legal Counsel `legal_review_approve` + Red Team cross-LLM `red_team_clear` 통과 후 발행
- brand-risk 메시지는 대표 직접 승인

### Sales Funnel

상세 funnel/conversion 설계는 `docs/SALES_PLAYBOOK.md` (Sales Team owns)에서 다룬다.

핵심 단계:

1. Awareness (organic content/SEO/community)
2. Free subscriber (newsletter sign-up)
3. Paid trial / first month
4. Paid retained
5. Custom memo lead (B2B inbound only)

가격/할인/환불 정책 변경은 Product Planning Team 협의 + Legal Counsel review + 대표 승인 후에만 가능.

---

## 5. Operating Loop

1. Agent가 evidence를 수집한다.
2. Local model이 저가치 항목을 제거한다.
3. Premium model이 issue 후보와 초안을 만든다.
4. Codex가 pipeline, archive, publishing automation을 유지한다.
5. 부대표가 한국어 자연스러움과 일반 독자 이해도를 검토한다.
6. 대표가 최종 발행을 승인한다.
7. issue를 발행한다.
8. 독자 반응, 구독자 수, paid 전환을 기록한다.
9. weekly business review에서 다음 issue 방향을 정한다.

---

## 6. 30-Day Revenue Goal

Success:

- weekly issue 4회 발행
- Pretotyping CTR ≥ 2% 달성

Acceptable learning:

- Pretotyping CTR ≥ 1% 이고 hesitation reason을 기록하면 학습 인정
- paid subscriber가 없어도 paid tier 노출과 hesitation reason을 기록하면 학습 인정

Failure:

- 콘텐츠를 발행하지 않음
- 독자 모집 경로가 없음
- paid tier를 한 번도 노출하지 않음
- 자동화와 문서만 늘어나고 독자 반응이 없음

---

## 7. Later Paths

Phase 2:

- custom memo
- sponsorship
- paid community
- corporate/team plan

Phase 3:

- 자기자본 소액 portfolio로 분석 정확도 검증
- 외부 자금 운용 또는 투자 자문은 하지 않는다.
