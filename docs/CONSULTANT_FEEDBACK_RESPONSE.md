# Consultant Feedback Response
# Version: 3.2
# Date: 2026-05-10

---

## 1. Current Decision

최신 컨설턴트 진단을 수용해 Harness의 Phase 1 사업 모델을 다시 설계했다.

최종 Phase 1 모델:

- B2B enterprise intelligence가 아니다.
- 주식/코인 자동매매도 아니다.
- `Korean/English hybrid creator subscription`이다.
- 제품은 `Physical AI Weekly`다.
- 30일 목표는 weekly issue 4회, 무료 구독자 50명, paid subscriber 1명이다.

---

## 2. Accepted Reasoning

수용한 이유:

- 사용자의 1차 목적은 단기 매출 극대화가 아니라 자동화 로직으로 돌아가는 회사를 운영해보는 경험이다.
- B2B intelligence sales는 현재 대표/부대표/하드웨어/LLM 자원과 맞지 않는다.
- creator subscription은 1~2명 운영, LLM 자동화, 구독/결제/독자 관계 운영을 모두 경험할 수 있다.
- 부대표의 강점은 B2B cold outreach보다 한국어 콘텐츠 자연스러움, 일반 독자 이해도, 초기 독자 seed, paid hesitation 해석에 더 잘 맞는다.
- 자기자본 투자/자동매매는 장기 옵션으로 남기되 Phase 1의 핵심 모델로 두지 않는다.

---

## 3. Applied Changes

| Area | Applied Change |
| --- | --- |
| Business model | B2B paid brief -> creator subscription |
| Product | `Physical AI Weekly` |
| Pricing | 월 ₩9,900 paid individual, 월 ₩19,900 optional supporter/pro |
| 30-day target | issue 4회, 무료 구독자 50명, paid subscriber 1명 |
| Vice President role | content quality gate, reader empathy, paid hesitation |
| Slack | `#vp-market-read` -> `#vp-content-review` |
| Data model | `newsletter_issues`, `content_reviews`, `subscriber_snapshots` 추가 |
| OJT | B2B co-listening -> content review gate |

---

## 4. Rejected Or Deferred

No full reject.

Deferred:

- Enterprise B2B intelligence sales: paid subscriber와 독자 반응이 생긴 뒤 optional memo/team plan으로 재검토한다.
- Proprietary trading: 분석 정확도를 검증할 단계에서 소액 자기자본으로만 검토한다.
- Dashboard/SaaS: 구독자와 반복 사용 수요가 생기기 전까지 보류한다.

---

## 5. Verification

- Slack channel `#vp-market-read` renamed to `#vp-content-review`.
- Bot joined renamed channel.
- Python compile checks passed for modified scripts.
- `infra/schema.sql` applied to `harness_dev`.
- New tables confirmed:
  - `newsletter_issues`
  - `content_reviews`
  - `subscriber_snapshots`

---

## 6. Round 4 — Customer Acquisition Reality + Governance Layer

### 6.1 Customer Acquisition Reset

대표가 명시했다:

> "수익 창출을 할 대상은 결코 내 주변사람이 될 수 없기 때문에 양질의 고순도 유료 보고서를 익명의 고객에게 판매하여 수익창출을 할 수 있는 마케팅 전략을 세울 수 있는 상품기획팀과 마케팅 전략팀, 그리고 영업팀을 추가할 것"

따라서 직전 권고(부대표 네트워크를 무료 구독자 seed로 활용)를 *철회한다*.

새 원칙:

- 수익 창출 대상은 *익명 독자*만 인정한다.
- 부대표/대표의 주변 인맥은 paid acquisition target에서 제외한다.
- 부대표 생활권 pain은 product insight로만 활용하고, 직접 결제 요청 대상이 아니다.

### 6.2 New Governance Layer

| 신규 요구 | 반영 위치 |
| --- | --- |
| 법무팀 (실행 전 법률 검토) | `AGENTS.md §3.11 Legal Counsel Agent`, `CLAUDE.md` `legal_review_approve` 신설, BOS.md flow에 Legal review 단계 추가, ORG_PLAN/CURRENT_STAFFING 반영 |
| 최악 상황 안전장치 (Pre-Mortem) | `CLAUDE.md §5 Must` Pre-Mortem 규칙, `AGENTS.md §8.1 Pre-Mortem Rule`, `pre_mortem_approve` approval type 신설 |
| Cross-LLM Red Team (코드 + MD + 의사결정) | `AGENTS.md §3.8` Red Team upgrade — 서로 다른 reasoning LLM 최소 2개 cross-verify, `red_team_clear`/`red_team_block` 기록 |
| 상품기획/마케팅 전략/영업팀 | `AGENTS.md §3.12 Product Planning`, `§3.13 Marketing Strategy`, `§3.14 Sales`. ORG_PLAN, CURRENT_STAFFING, BOS.md §3, MONETIZATION_STRATEGY.md, CUSTOMER_DISCOVERY_PLAYBOOK.md 반영 |

### 6.3 High-Impact Decision Pre-conditions

| Approval | Required pre-conditions |
| --- | --- |
| `report_publish_approve` | `legal_review_approve` + `red_team_clear` |
| `monetization_experiment_approve` | `legal_review_approve` + `red_team_clear` + `pre_mortem_approve` |
| `investment_thesis_approve` | `red_team_clear` + `pre_mortem_approve` |
| `capital_action_approve` | `legal_review_approve` + `red_team_clear` + `pre_mortem_approve` + `CAPITAL_ACTIONS_ENABLED=true` |

### 6.4 Doc Wrapper Roadmap

`CLAUDE.md §10`에 다음 신규 doc target을 등록. 내용 작성은 후속 round.

- `docs/operations/LEGAL_REVIEW_PLAYBOOK.md`
- `docs/governance/RED_TEAM_PROTOCOL.md`
- `docs/governance/PRE_MORTEM_PROTOCOL.md`
- `docs/strategy/MARKETING_STRATEGY.md`
- `docs/operations/SALES_PLAYBOOK.md`
- `docs/product/PRODUCT_PLANNING.md`

### 6.5 Updated File Versions (Round 4)

| File | Version |
| --- | --- |
| `CLAUDE.md` | v3.1 |
| `AGENTS.md` | v3.1 |
| `docs/strategy/BUSINESS_OPERATING_SYSTEM.md` | v2.1 |
| `docs/strategy/MONETIZATION_STRATEGY.md` | v2.1 |
| `docs/operations/CUSTOMER_DISCOVERY_PLAYBOOK.md` | v2.1 |
| `docs/governance/ORG_PLAN.md` | v2.1 |
| `docs/operations/SLACK_OPERATING_SYSTEM.md` | v1.3 |
| `docs/governance/CURRENT_STAFFING.md` | v1.1 |
| `docs/CONSULTANT_FEEDBACK_RESPONSE.md` | v3.0 |

---

## 7. Round 5 — QA Team + Pre-Mortem + Legal Playbook + Language Policy

### 7.1 Trigger

대표가 4개 추가 요청을 했다:

1. `LEGAL_REVIEW_PLAYBOOK.md` 내용 채우기
2. `PRE_MORTEM_PROTOCOL.md` 내용 채우기
3. 고객-facing 산출물 품질 검증 QA Team 신설
4. 발행 언어 정책 (한국어/영어 vs 다국어) 지침 작성

### 7.2 Decision Log

| Request | Decision | Implementation |
| --- | --- | --- |
| LEGAL_REVIEW_PLAYBOOK.md 내용 작성 | Accept | 11개 섹션 생성 — 트리거, 한국법 체크리스트(자본시장법/표시광고법/약관규제법/PIPA/저작권/부정경쟁), 국제법(GDPR/US securities), risk pattern library, disclaimer template 4종, cross-LLM 절차, output template, 외부 변호사 escalation |
| PRE_MORTEM_PROTOCOL.md 내용 작성 | Accept | 12개 섹션 생성 — 트리거, memo template, scenario 생성법, probability calibration anchor, loss taxonomy, recovery level, mitigation, detection trigger, approval flow, 2개 worked example, quick reference |
| QA Team 신설 | Accept | `AGENTS.md §3.14A QA Agent` 신설 — VP/Red Team/Legal과 분리된 fact + format + schema + link + terminology + 다국어 fluency final gate. `qa_clear` approval type 추가. `BOS.md §3 QA Team`, `ORG_PLAN`, `CURRENT_STAFFING`, `SLACK_OS` 반영 |
| 다국어 정책 | Accept | `LANGUAGE_POLICY.md` 신설 — Phase 1 = 한국어 + 영어 on-demand, Phase 2 진입 5조건, 언어 후보 ranking (영어 → 일본어 → 중국어 진입 금지), translation workflow, multi-language QA checklist, premature expansion 6대 risk |

### 7.3 Strategic Guidance on Languages

**현재 결정**: Phase 1 = 한국어 primary + 영어 on-demand. 다른 언어 *금지*.

핵심 reasoning:
- 한 언어에서 검증되지 않은 콘텐츠를 여러 언어로 확장 시 *약한 콘텐츠를 N개 언어로 갖는다*.
- LLM 자동번역은 "이해 가능"이지 "현지 native가 신뢰할 수준의 자연스러움"은 아니다.
- QA burden은 언어당 N배 → 본 사이즈에서 다국어 동시 운영은 QA collapse 위험.
- 부대표 native fluency는 한국어. 영어는 cross-LLM + (필요 시) 외주 native reviewer로 보완.

**Phase 2 진입 조건 (5개 AND)**:
1. 한국어 paid subscriber 50명 또는 월 ₩500K 매출
2. 한국어 weekly issue 12회 안정 발행
3. 영문 inbound paid memo 5건 처리 경험
4. QA + Legal pipeline 안정 운영
5. 부대표 OJT module 4 통과

### 7.4 New Approval Type

`qa_clear` 추가. 모든 외부 발행 / paid memo / marketing copy / 다국어 번역본의 사전 조건.

| Approval | Updated pre-conditions |
| --- | --- |
| `report_publish_approve` | `legal_review_approve` + `red_team_clear` + **`qa_clear`** |
| `monetization_experiment_approve` | `legal_review_approve` + `red_team_clear` + `pre_mortem_approve` + **`qa_clear`** |
| `investment_thesis_approve` | `red_team_clear` + `pre_mortem_approve` + **`qa_clear`** |
| Multi-language publish | **`qa_clear` (cross-LLM verified)** + `legal_review_approve` per jurisdiction |

### 7.5 Updated File Versions (Round 5)

| File | Version |
| --- | --- |
| `CLAUDE.md` | v3.2 |
| `AGENTS.md` | v3.2 |
| `docs/strategy/BUSINESS_OPERATING_SYSTEM.md` | v2.2 |
| `docs/governance/ORG_PLAN.md` | v2.2 |
| `docs/operations/SLACK_OPERATING_SYSTEM.md` | v1.4 |
| `docs/governance/CURRENT_STAFFING.md` | v1.2 |
| `docs/CONSULTANT_FEEDBACK_RESPONSE.md` | v3.1 |

### 7.6 New Files Created (Round 5)

| File | Version | Purpose |
| --- | --- | --- |
| `docs/operations/LEGAL_REVIEW_PLAYBOOK.md` | v1.0 | Legal Counsel Agent 운영 절차, 한국/국제법 체크리스트, disclaimer 템플릿 |
| `docs/governance/PRE_MORTEM_PROTOCOL.md` | v1.0 | high-impact 의사결정 전 worst-case 분석 절차, 템플릿, 2개 worked example |
| `docs/LANGUAGE_POLICY.md` | v1.0 | 발행 언어 Phase 정책, 다국어 확장 trigger, multi-language QA checklist |

---

## 8. Round 6 — Operational Playbooks (Marketing / Sales / Product / QA)

### 8.1 Trigger

대표가 4개 wrapper-only 문서의 *내용*을 채우라고 지시했다.

### 8.2 Files Created

| File | Version | Sections | Owner |
| --- | --- | --- | --- |
| `docs/strategy/MARKETING_STRATEGY.md` | v1.0 | 11 sections — Phase 1 constraints, persona 4종, channel mix (Tier 1/2/3), weekly/monthly content calendar, brand voice, KPIs, outbound restrictions, Phase 2 paid acquisition trigger, compliance reference | Marketing Strategy Agent |
| `docs/operations/SALES_PLAYBOOK.md` | v1.0 | 11 sections — funnel 5단계, conversion mechanics by stage, pricing experiments (allowed / forbidden), onboarding sequence, retention/churn, custom memo lead qualification, refund process, KPIs, PIPA 준수, compliance reminders | Sales Agent |
| `docs/product/PRODUCT_PLANNING.md` | v1.0 | 10 sections — Phase 1 product 정의, free vs paid 분리 원칙, pricing ladder (active/roadmap), feature decision process (3-signal rule), A/B test backlog, subscriber feedback 파이프라인, roadmap product 4종, anti-patterns | Product Planning Agent |
| `docs/operations/QA_PLAYBOOK.md` | v1.0 | 11 sections — 6개 checklist category (factual/format/link/terminology/voice/language), cross-LLM workflow + audit trail, 5개 artifact별 detailed checklist, distinct from VP/Red Team/Legal, output templates (qa_clear/qa_block), failure handling, KPIs | QA Agent |

### 8.3 Key Decisions Embedded

- Phase 1 marketing은 *organic-first*. paid spend default $0.
- 부대표/대표 *주변 인맥*을 paid 캠페인 타깃으로 *동원하지 않음* (재확인).
- pricing 실험은 시간 분리 또는 random cohort. 동시 가격 노출 금지 (한국 표시광고법).
- product feature 추가는 *3-signal rule* (subscriber 동일 요청 3회 이상). CEO 직관만으로 추가 금지.
- QA는 *fact + format*. 해석/의도는 다른 review 영역.
- 다국어 산출물은 cross-LLM QA *의무*.
- 모든 외부 발행은 4-gate (VP review + Red Team + Legal + QA) 통과 후 대표 publish 결정.

### 8.4 Document Roadmap Cleanup

`CLAUDE.md §10`의 doc table에서 `QA_PLAYBOOK.md`의 "(roadmap)" 표기 제거 (이제 active).

### 8.5 Updated File Versions (Round 6)

| File | Version |
| --- | --- |
| `CLAUDE.md` | v3.2 (doc table 갱신) |
| `docs/CONSULTANT_FEEDBACK_RESPONSE.md` | v3.2 |

### 8.6 New Files Created (Round 6)

| File | Version |
| --- | --- |
| `docs/strategy/MARKETING_STRATEGY.md` | v1.0 |
| `docs/operations/SALES_PLAYBOOK.md` | v1.0 |
| `docs/product/PRODUCT_PLANNING.md` | v1.0 |
| `docs/operations/QA_PLAYBOOK.md` | v1.0 |

### 8.7 Operating Readiness

이 시점에 회사 운영의 *문서적 준비*는 사실상 완료된다. 다음 자연스러운 단계:

- 첫 weekly issue 작성 (실전)
- 운영 결과를 weekly business review에 누적
- 발견된 gap을 docs로 backport (반대 방향 — *문서 → 운영*에서 *운영 → 문서*로)

문서 추가는 *발견된 gap이 있을 때만* 작성. 추가 wrapper-only 문서는 *생성 금지*.
