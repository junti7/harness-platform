# Harness Business Operating System
# Version: 2.4
# Date: 2026-05-10

---

## 1. Purpose

Harness의 목적은 AI 뉴스 요약기가 아니다.

Harness의 목적은 대표(President/CEO)와 부대표(Vice President)가 다수 LLM, 로컬 하드웨어, 자동화 파이프라인을 활용해 `한국어 Physical AI weekly subscription`을 운영하고, 콘텐츠 발행, 독자 반응, 유료 구독, optional memo, 장기 자기자본 검증까지 이어지는 작은 자동화 회사를 실제로 운영해보는 것이다.

궁극적 목표는 자동화 운영 경험과 실제 매출이다. 단기 매출 극대화가 목적은 아니지만, 매출이 계속 0이면 사업 모델은 재검토한다.

---

## 2. Business Model

Phase 1 primary model:

- Model: Korean/English hybrid creator subscription
- Product: `Physical AI Weekly`
- Audience: Physical AI, AGI, robotics, semiconductor, automation에 호기심 있는 한국어 독자
- Free tier: weekly public issue
- Paid tier: 월 ₩9,900~₩19,900
- 30-day target: free subscribers 50명 + paid subscriber 1명
- Delivery: Substack primary + Notion archive (per `docs/operations/NOTION_OPERATING_SYSTEM.md`) + Slack operating workflow

Phase 2:

- Optional custom memo
- 한국어 또는 영어 paid memo
- 가격: ₩300,000 또는 $300부터 실험

Phase 3:

- 자체 분석 정확도를 검증하기 위한 소액 자기자본 투자
- 외부 자금 운용, 투자 자문, 자동매매 판매는 하지 않는다.

---

## 3. Human Roles

### 대표(President/CEO)

대표는 editor-in-chief이자 최종 의사결정권자다.

책임:

- 콘텐츠 방향과 포지셔닝 결정
- 발행 승인
- paid tier 가격과 offer 승인
- 외부 공개 claim 승인
- custom memo 또는 자기자본 투자 검토 승인
- 자본 집행 승인
- agent 권한 확대 승인

대표는 모든 중간 수집물에 개입하지 않는다. 대표는 publish, pricing, brand risk, capital action에 집중한다.

### CEO Chief of Staff Function

Codex는 대표 비서실장 기능을 수행한다.

책임:

- 대표와 부대표의 지시사항을 checklist로 전환
- 각 지시사항의 owner, status, blocker, output artifact 추적
- 장기 리서치/벤치마크 작업을 여러 LLM에게 병렬 분배
- 완료/미완료/보류를 명확히 보고
- 대표/부대표 검토 문서를 PDF, Slack brief, decision card 형태로 제공
- LLM 협업 내역을 별도 보고서로 남김

비서실장 기능은 대표의 의사결정을 대체하지 않는다. 대표가 더 적은 개입으로도 중요한 결정을 빠뜨리지 않도록 운영 기억장치와 실행 추적 장치 역할을 한다.

### 부대표(Vice President)

부대표는 `Content Quality Gate & Reader Empathy Lead`다.

부대표의 현실적 강점:

- 약 10년간 기업 조직 생활 경험
- 현재 생활권의 또래 주부, 여성 직장인, 가족/교육/가정 운영 감각
- EQ와 독자 반응 감지
- 비전문가가 이해할 수 있는지 판단하는 능력
- 제목, 문장, 설명 방식의 자연스러움 판단

부대표의 Phase 1 역할:

- 발행 전 한국어 draft가 읽히는지 검토
- 너무 어렵거나 과장된 표현 표시
- 일반 독자가 공유할 수 있는 제목/요약 제안
- 댓글, DM, 구독 취소, paid hesitation의 정성적 해석
- Marketing Strategy Team이 작성한 카피의 자연스러움 review

부대표는 B2B cold outreach 담당자가 아니다. 또한 부대표 또는 대표의 주변 인맥은 paid subscriber 모집 대상이 아니다. 수익 창출 대상은 마케팅을 통해 유입되는 익명의 독자다.

### Legal Counsel Function

Legal Counsel은 외부 newsletter 발송, paid offer 발행, 광고 카피, 데이터 수집 정책 변경, 환불/약관 정책 시 사전 법률 리스크를 검토한다. 적용법은 한국 자본시장법, 표시광고법, 약관규제법, 개인정보보호법, 저작권법, 부정경쟁방지법 등이다. 해외 결제는 GDPR 등도 식별한다. 변호사 자격 활동을 대체하지 않으며 high-risk 사안은 외부 변호사 자문을 권고한다.

### Red Team (Cross-LLM Verification)

Red Team은 코드, MD 문서, high-impact 의사결정의 약점을 *서로 다른 신뢰도 높은 LLM 최소 2개*로 cross-verify한다. 동일 모델 self-review는 인정하지 않는다. 두 모델 의견이 충돌하면 third opinion 또는 인간 결정.

### Product Planning Team

`Physical AI Weekly` 및 후속 상품(custom memo 등)의 정의, 패키징, 가격 ladder, 기능 우선순위를 설계한다. subscriber feedback과 conversion data를 product backlog로 변환한다.

### Marketing Strategy Team

익명 고객 acquisition 전략을 수립한다. 관계 기반 outreach가 아니라 organic content + paid channel mix를 운영한다. persona 정의, 브랜드 메시지, content calendar, 채널 KPI를 결정한다.

Substack를 primary publication/growth system으로 사용할 때의 세부 운영은 `docs/operations/SUBSTACK_SYSTEM_PLAYBOOK.md`를 따른다.

### Sales Team

paid funnel(free → trial → paid → retained)을 운영한다. conversion 실험, 가격 테스트, onboarding 시퀀스, churn 분석을 담당한다. custom memo 문의가 들어오면 lead qualification을 한다.

### Business Operations Team

Business Operations Team은 `/goal` closed loop의 운영 예측 및 이상징후 감지 전담 조직이다.

책임:

- 최종목표에 대한 deadline hit probability 추정
- daily / 3-day / weekly cadence로 KPI 추적
- 노출 / CTR / CVR / retention 등 핵심 변수를 분해해 병목 진단
- anomaly detection
- local strategy revision 제안
- executive escalation 필요 여부 판단
- 수학 모형(`goal_model_spec`)의 변수, 식, 파라미터, threshold 유지

원칙:

- 작은 운영 흔들림은 local revision으로 해결한다.
- 구조적 실패 징후가 있을 때만 대표/부대표에 escalate 한다.
- 감이 아니라 변수와 식으로 판단한다.

출력:

- goal health brief
- forecast memo
- diagnostic memo
- local revision proposal
- escalation note

### QA Team

고객에게 판매/노출되는 모든 산출물 (weekly issue, paid memo, marketing copy, paid landing, custom report, 다국어 번역본)의 발행 직전 final 품질 검증을 담당한다. fact + source 일치, link/format/schema, terminology, brand voice, 다국어 fluency를 점검한다. VP content review (readability), Red Team (adversarial), Legal Counsel (regulatory)와 분리된 *기술적/사실적 발행 readiness gate*다. 출력은 `qa_clear` 또는 `qa_block`. 다국어 산출물은 cross-LLM QA verification 의무.

### Language Policy

발행 언어 정책은 `docs/LANGUAGE_POLICY.md`를 따른다. Phase 1은 한국어 primary + 영어 on-demand. 다른 언어 launch는 Phase 2 진입 조건 (한국어 paid subscriber 50명 또는 월 ₩500K 매출, 12회 안정 발행, 영문 paid memo 5건 처리, QA/Legal pipeline 안정, VP OJT module 4 통과) 충족 후 대표 승인 필수. LLM 자동번역만으로 paid 콘텐츠 발행 금지.

### AI Agents

AI agent는 인간 판단을 대체하지 않는다. AI agent는 수집, 필터링, 초안 작성, 검증, 번역, 요약, 편집 보조, 발행 준비, 독자 지표 정리, marketing/sales/legal/red team 보조 분석을 담당한다.

---

## 4. Operating Flow

Harness의 표준 creator subscription flow:

1. Evidence collection
2. Signal filtering
3. Weekly issue candidate selection
4. Korean/English draft generation
5. Technical and claim verification
6. Vice President content review (readability, shareability)
7. Cross-LLM Red Team verification (서로 다른 reasoning LLM 2개 이상)
8. Legal Counsel review (광고/규제/저작권/약관)
9. Pre-Mortem 작성 (worst-case 시나리오, 발생 확률, 최대 손실, 회복 가능성, detection trigger — `docs/PRE_MORTEM_PROTOCOL.md`)
10. QA final gate (fact + format + schema + link + terminology + 다국어 시 cross-LLM fluency — `qa_clear`)
11. President publish decision (with `legal_review_approve` + `red_team_clear` + `qa_clear` + `pre_mortem_approve` precondition)
12. Publish free issue
13. Marketing distribution (organic / paid channel mix per `docs/MARKETING_STRATEGY.md`)
14. Sales funnel monitoring (free → trial → paid → retained)
15. Track subscriber feedback
16. Store customer memory and product upgrade events
17. Product Planning iteration (next issue / pricing / packaging / cross-product reuse)
18. Business Operations forecast / anomaly review
19. Weekly business review
20. Optional capital action (with full Pre-Mortem + Legal + Red Team + `CAPITAL_ACTIONS_ENABLED=true`)

수익 창출 대상은 부대표 또는 대표의 주변 인맥이 아니라, Marketing Strategy → Subscriber Growth → Sales 파이프라인을 통해 유입되는 익명 독자다. 주변 인맥에게 직접 결제 요청을 하지 않는다.

기존 4-Tier AI Pipeline은 내부 엔진으로 유지한다.

- Tier 1: raw evidence 수집
- Tier 2: local gate / 저비용 필터링
- Tier 3: premium analysis / draft and analysis
- Tier 4: publishing / archive / subscriber delivery

---

## 5. Content Product Definition

`Physical AI Weekly`의 기본 구성:

- 이번 주 핵심 signal 5~7개
- 각 signal의 원문 출처
- 왜 중요한가
- 한국 산업/직장인/일반 독자 관점 implication
- 과장 가능성 또는 반론
- 다음에 지켜볼 것

Non-promise:

- 투자 수익 보장
- 모든 뉴스 coverage
- 실시간 알림
- 검증되지 않은 기술 claim
- 주식/코인 매매 추천

---

## 6. Monetization

초기 paid tier:

- 월 ₩9,900~₩19,900
- 무료 issue보다 더 짧고 정제된 signal digest
- archive access 또는 paid-only memo 포함 가능

Optional memo:

- 특정 회사, 기술, 산업 이슈에 대한 custom memo
- 시작 가격: ₩300,000 또는 $300
- inbound request 또는 명확한 관심이 있을 때만 진행

Revenue rule:

- 30일 목표는 paid subscriber 1명이다.
- 90일 이상 매출 0이면 콘텐츠 포지셔닝, 주제, 발행 채널, 가격을 재검토한다.

---

## 7. Approval Semantics

Canonical approval type은 `CLAUDE.md §4`를 따른다.

creator model에서 자주 쓰는 approval 의미:

| Approval Type | Meaning | Money Moves? |
| --- | --- | --- |
| `signal_approve` | issue 후보로 채택 | No |
| `report_publish_approve` | free 또는 paid issue 발행 승인 | No direct investment |
| `monetization_experiment_approve` | paid tier, memo, sponsorship test 승인 | Maybe, capped |
| `investment_thesis_approve` | 자기자본 검증 후보로 승격 | No |
| `capital_action_approve` | 실제 비용/투자/자본 집행 승인 | Yes |

`capital_action_approve`만 실제 돈 집행 승인이다.

---

## 8. Metrics

매주 추적:

- issue published count
- free subscribers
- paid subscribers
- free-to-paid conversion
- open/click/share/reply rate
- Vice President readability pass rate
- unsubscribe reason
- subscriber revenue
- memo revenue
- cost per issue
- LLM cost per useful signal

---

## 8.5 Data Model Target

Creator subscription 운영에 필요한 핵심 테이블:

- `newsletter_issues`: weekly issue draft, free/paid body, publish status, source signals
- `content_reviews`: 부대표 readability, shareability, paid hesitation review
- `subscriber_snapshots`: free/paid subscriber, revenue, opens, clicks, replies, shares
- `customer_profiles`: 고객별 언어, 지식수준, consent, tier
- `customer_memory_events`: 고객 피드백, 행동, 질문, 혼란 포인트, paid hesitation의 누적 memory
- `customer_interest_tags`: 고객 관심 주제와 weight
- `customer_watchlists`: 고객별 회사/기술/지표 watchlist
- `customer_questions`: 고객별 질문 이력과 답변 상태
- `product_upgrade_events`: 고객 피드백으로 실제 상품이 어떻게 개선되었는지 기록
- `artifact_memory_usage`: 특정 보고서/상품이 어떤 고객 memory와 upgrade event를 참조했는지 기록
- `research_reports`: optional memo 또는 internal report
- `ceo_decisions`: publish, paid experiment, capital action approval

Customer memory rule:

- 고객별 feedback과 상품 upgrade event는 DB에 누적한다.
- AI agent는 누적 memory를 다음 report, watchlist, paid memo, pricing, onboarding, language choice에 반영한다.
- 단, 보유종목, 매수/매도 의도, 자산규모 등 투자자문 또는 민감정보로 이어질 수 있는 데이터는 저장하지 않는다.
- personalization 동의가 없는 고객은 개인화 memory를 사용하지 않는다.
- QA는 고객-facing artifact가 관련 memory를 실제로 참조했는지 `artifact_memory_usage`로 검증한다.

---

## 9. 30-Day Objective

30일 목표:

- `Physical AI Weekly` 4회 발행
- 무료 구독자 50명
- paid subscriber 1명
- 부대표 content review 4회 완료
- weekly business review 4회 완료
- paid tier 가격 1회 이상 노출

이 목표가 B2B cold outreach, dashboard, Slack channel expansion보다 우선한다.

---

## 10. What Not To Optimize Yet

초기에는 다음을 최적화하지 않는다.

- 대규모 B2B sales
- 복잡한 dashboard
- 모든 논문 coverage
- 실시간 알림
- 주식/코인 자동매매
- 투자 자문
- 미통합 LLM service production화

초기 최적화 대상:

- 정기 발행 cadence
- 읽히는 한국어 콘텐츠
- 무료 구독자 증가
- paid 전환 실험
- 자동화된 수집/초안/검증 루프

---

## 11. Current Implementation Priority

1. `docs/CONTENT_OPERATING_PLAYBOOK.md` 작성 및 적용
2. 첫 issue template 확정
3. publishing platform 후보 선택: Substack/Maily/Brunch 중 하나
4. free subscriber capture path 구성
5. paid tier 가격 문구 작성
6. Vice President content review workflow 구성
7. Notion Operating System (NOS) 구축 및 archive 구성 (per `docs/operations/NOTION_OPERATING_SYSTEM.md`)
8. weekly business review 실행
9. optional memo request form은 2차로 검토

---

## 12. Governing Principle

Harness는 B2B SaaS가 아니라 creator subscription에서 시작한다.

자동화는 발행 cadence와 품질을 높이기 위한 수단이다. 콘텐츠가 독자에게 읽히지 않고 paid subscriber가 생기지 않으면 자동화 자체는 사업 가치가 없다.
