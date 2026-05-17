# Marketing Strategy
# Version: 1.0
# Date: 2026-05-10
# Owner: Marketing Strategy Agent

---

## 1. Purpose

이 문서는 `Physical AI Weekly`의 *익명 고객 acquisition 전략*을 정의한다.

핵심 원칙:

- 수익 창출 대상은 *익명 독자*다. 부대표/대표 주변 인맥을 paid 캠페인 타깃으로 동원하지 않는다.
- Phase 1은 *organic-first*. paid spend는 default 0이며 `capital_action_approve` + `legal_review_approve` + `pre_mortem_approve` 통과 시에만 활성화.
- 모든 외부 발신 카피는 Legal Counsel `legal_review_approve` + Red Team cross-LLM `red_team_clear` + QA `qa_clear` 통과 후 발행.

상위 정책: `docs/MONETIZATION_STRATEGY.md`, `docs/LANGUAGE_POLICY.md`.

---

## 2. Phase 1 Constraints

| 항목 | Phase 1 정책 |
| --- | --- |
| 광고 예산 | $0 default. 변경은 `capital_action_approve` 필수 |
| 타깃 인구 | 익명 한국어 독자 (필요 시 영문 inbound) |
| 채널 | organic content + community seed + SEO. paid 보류 |
| 인맥 동원 | *금지* — 가족/친구/동료/동창 paid 권유 안 함 |
| 다국어 | `LANGUAGE_POLICY.md` Phase 1 = 한국어 + 영어 on-demand |
| 발신 빈도 | weekly issue 1회 + organic post 주 2~5회 |

---

## 3. Persona Definition

Phase 1 익명 독자 페르소나 4종.

### Persona A — "기술 호기심 직장인"
- 25~40대 한국 직장인
- IT/스타트업/제조/반도체/항공/바이오 분야 비전공 또는 인접
- AI 뉴스를 읽지만 영어 원문이 부담스럽다
- 동료/팀 대화에서 "Physical AI 어떻게 보세요?" 라고 묻고 싶어한다
- 월 ₩9,900 newsletter 구독 경험 있음 (미라클레터, 뉴닉 paid 등)
- **paid 전환 motive**: 회사에서 *아는 척* 할 수 있는 신호

### Persona B — "스타트업/투자 인근 실무자"
- VC junior, 스타트업 PM/전략, 액셀러레이터 직원
- Physical AI 트렌드를 *직무로* 따라가야 함
- 영문 source 일부 직접 본다
- **paid 전환 motive**: 직무 효율 (시간 절약 + 놓치는 신호 줄이기)

### Persona C — "엔지니어/연구자 인접"
- ML/SW 엔지니어, 학생, 연구원
- arXiv 직접 보지만 시장/투자 angle은 약함
- **paid 전환 motive**: 한국 시장/산업 implication 해석

### Persona D — "영문 inbound (custom memo only)"
- 영문 readers from X/LinkedIn
- 특정 회사/기술 deep dive를 paid memo로 의뢰
- **price point**: $300 single memo
- *정기 영문 발행은 Phase 1 X*

각 persona의 motive와 가격 민감도는 첫 30일 reader feedback으로 검증/수정한다.

---

## 4. Channel Mix

priority 순.

### Tier 1 (Phase 1 active)

**1. Organic Newsletter Platform**
- Substack primary
- 매주 1회 정기 발행
- Welcome page, free welcome email, Notes, Recommendations, subscriber dashboard를 함께 운영
- Free issue + Paid tier
- KPI: 무료 구독자 수, open rate, paid conversion

**2. X/Twitter (한국어)**
- weekly issue 발행 시 thread 형태 요약 1건 (3~7개 tweet)
- 매주 ad-hoc post 1~2건 (signal 짧은 reaction)
- 영문 X account는 별도 운영 (Persona D inbound용, weekly 1건)
- KPI: 팔로워 증가, profile click → newsletter sign-up rate

**3. 한국 Tech Community**
- geeknews, disquiet, 클리앙 IT, 페이스북 AI 그룹
- weekly issue 발행 후 *직접 홍보 X* — 자연스러운 토론 시작 (post 자체는 분석 인용)
- spammy posting 절대 금지
- KPI: community-referred sign-up rate

**4. SEO (slow burn)**
- newsletter platform의 SEO 활용
- 한국어 brand keyword: "Physical AI 한국어", "임바디드 AI", "휴머노이드 분석", "robotics 뉴스레터"
- 첫 4주 issue를 SEO 최적화된 제목/요약으로 작성 (단, 기술적 정확성 우선)
- KPI: search-referred sign-up rate (3개월 lag)

### Tier 2 (Phase 1 보류, Phase 2 검토)

- LinkedIn (영문 Persona D 보조 채널)
- Brunch (한국어 long-form 백업 채널)
- YouTube/Podcast 부속 콘텐츠

### Tier 3 (Phase 1 금지)

- 광고 (Google/Meta/X paid)
- 인플루언서 페어드 컨텐츠
- 검색엔진 광고
- 가족/지인/동창 직접 권유

---

## 5. Content Calendar

### Weekly Rhythm

| 요일 | 활동 | Owner |
| --- | --- | --- |
| 월 | 지난주 결과 review (`docs/WEEKLY_BUSINESS_REVIEW.md`) | 대표 |
| 화 | issue 후보 선정 + draft 시작 | Editor + Codex |
| 수 | draft 완성, 부대표 review 요청 | Editor → 부대표 |
| 목 | 부대표 review → Red Team cross-LLM → Legal Counsel → QA | Multi-agent |
| 금 (오전) | 대표 publish decision | 대표 |
| 금 (오후) | issue 발행 + X thread + 커뮤니티 인용 | Subscriber Growth |
| 토 | reader 반응 수집 | Subscriber Growth |
| 일 | 다음 주 plan + product backlog update | Marketing + Product Planning |

### Monthly Rhythm

- Week 1: 첫째 주 issue 발행 + 신규 source 후보 review
- Week 2: 두번째 issue + paid tier 노출 실험
- Week 3: 세번째 issue + reader survey (옵션)
- Week 4: 네번째 issue + 월간 BR + 다음 달 plan

### Ad-Hoc Triggers

긴급 발행 가능 trigger (대표 승인 후):
- 주요 funding/exit event (>$500M)
- 정책/규제 큰 변화 (한국/미국)
- 해당 도메인의 *paradigm shift* 수준 announcement

긴급 발행도 *동일한 검증 게이트* (VP → Red Team → Legal → QA → 대표) 통과 의무.

---

## 6. Brand Voice / Tone

### Voice 원칙

- 한국어 native, 직장인 일상어 + 일부 전문용어 (해설 동반)
- *"전문가 흉내내기"* 금지 — 모르는 건 모른다고 명시
- 단정적 예측 *금지* (자본시장법 risk)
- "신호 해석" 프레임. "예측" 프레임 회피
- 1인칭 *"우리"* 또는 publisher 지칭 — *"전문가"* 자칭 금지

### Tone 가이드 (예시)

좋은 예:
> "Figure AI가 이번 주 Series C funding을 발표했다. 12B 밸류에이션은 18개월 전의 4배다. 이 funding 패턴은 humanoid manipulation의 IPO timeline을 *2027년대까지* 앞당길 수 있는 신호로 해석된다. 단, foundation model 학습 데이터의 부족은 여전히 미해결이다."

나쁜 예 (legal/voice 위반):
> "Figure AI는 반드시 2027년 IPO할 것이다. 지금 관련주를 사두면 좋다." (단정 + 투자 권유)
> "전문가들이 분석한 결과..." (없는 전문가 인용)
> "혁신적인 기술이 미래를 바꿀 것입니다." (공허한 hype)

### Brand Voice Reference (외부 모델)

- 톤 reference: 미라클레터 (직장인 친화 + 일부 전문성)
- 깊이 reference: SemiAnalysis (반도체 기술 핵심)
- 한국 시장 angle: 자체 (공급 부족 영역)

---

## 7. KPIs by Channel

| Channel | Primary KPI | Secondary KPI | Phase 1 Target (30일) |
| --- | --- | --- | --- |
| Newsletter platform | 무료 구독자 | open rate / share | 50명 / 35%+ |
| X/Twitter (한국어) | profile click → sign-up | 팔로워 | 200/20 |
| Community | community → newsletter | post engagement | 10/post |
| SEO | search → newsletter | brand keyword rank | (3개월 lag, 측정만) |
| Email referral | invite → sign-up | viral coefficient | 측정만 |

각 KPI는 `docs/WEEKLY_BUSINESS_REVIEW.md`에서 매주 reviewed.

Substack-specific 운영 규칙은 `docs/operations/SUBSTACK_SYSTEM_PLAYBOOK.md`를 따른다.

trigger:
- 무료 구독자 < 20명 (4주차) → channel mix 재검토
- open rate < 25% → 제목/lead 구조 재검토 (부대표 review 강화)
- 무료 → paid 전환 0% (8주차) → paid tier 가치 재정의

---

## 8. Outbound Restrictions

다음은 *절대 금지*:

- 부대표/대표의 카카오톡, 직접 DM, 가족/친구 group chat에 newsletter 광고
- 동창/직장 동기/이웃 direct 권유 (자발적 구독은 허용, *권유 X*)
- LinkedIn cold DM mass campaign
- 무차별 community spam
- "유료 가입하면 X 드립니다" 식 inducement (legal risk)
- 가짜 후기/리뷰 작성
- 다른 newsletter의 구독자 명단 활용

위반 발견 시 즉시 Marketing Strategy Agent 책임자(대표)에게 escalation + 해당 행위 중단.

---

## 9. Phase 2 Paid Acquisition Trigger

다음 *모두* 충족 시 paid 광고 검토:

- 무료 구독자 200명 이상
- paid subscriber 10명 이상 (organic으로 검증된 가치)
- LTV / CAC 추정 가능한 데이터 누적 (3개월+)
- `capital_action_approve` + `legal_review_approve` + `pre_mortem_approve` 통과
- 광고 예산 cap 사전 설정

광고 채널 우선순위 (Phase 2 진입 시):
1. X/Twitter promoted post (페르소나 fit 좋음)
2. LinkedIn (Persona B/D)
3. Google search (brand keyword)
4. 한국 newsletter cross-promotion (paid sponsorship)

---

## 10. Compliance Reference

이 전략의 모든 외부 발신은 다음 게이트를 통과한다.

| Gate | 책임 | 참조 |
| --- | --- | --- |
| Legal review | Legal Counsel Agent | `docs/LEGAL_REVIEW_PLAYBOOK.md` |
| Red Team cross-LLM | Red Team Agent | `AGENTS.md §3.8` |
| Pre-Mortem (광고 캠페인 등) | President Decision Agent | `docs/PRE_MORTEM_PROTOCOL.md` |
| QA final gate | QA Agent | `docs/QA_PLAYBOOK.md` (roadmap) |
| Language policy | Product Planning + 대표 | `docs/LANGUAGE_POLICY.md` |
| Capital action (paid spend) | 대표 only | `CAPITAL_ACTIONS_ENABLED=true` |

---

## 11. Quick Reference

| 상황 | 행동 |
| --- | --- |
| 새 organic post 작성 | Marketing Strategy 카피 → 부대표 review → 발행 |
| 광고 시작하고 싶다 | Phase 2 trigger 충족 확인 → 4-gate 전체 통과 → 대표 승인 |
| 가족이 newsletter 자랑하고 싶어한다 | 자발적 공유는 OK. *권유 시작은 X* |
| 영문 inbound DM 도착 | Persona D 분류 → custom memo flow (Sales Playbook §custom_memo) |
| 다른 뉴스레터 cross-promotion 제안 | Legal review + 대표 승인 후 검토 (Phase 2 권장) |
| 갑자기 큰 뉴스 발생 | ad-hoc trigger 적용 가능, 동일 4-gate 의무 |
