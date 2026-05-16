# QA Playbook
# Version: 1.1
# Date: 2026-05-10
# Owner: QA Agent

---

## 1. Purpose

이 문서는 *고객-facing 산출물*의 발행 직전 final 품질 검증 절차다.

QA Agent는 다음과 *분리*된다:

- **Vice President content review** — readability + reader empathy (일반 독자가 이해/공유 가능한가)
- **Red Team Agent** — adversarial (hallucination / hype / weak evidence / worst-case)
- **Legal Counsel Agent** — regulatory (광고/저작권/약관/개인정보)
- **QA Agent** — *fact accuracy + format/schema + link integrity + terminology + brand voice + multi-language fluency*

QA는 위 셋을 통과한 산출물을 *마지막 기술적 점검*만 수행한다.

출력: `qa_clear` 또는 `qa_block`.

Paid product QA는 단순 오류 검사가 아니다. 경쟁사 world-best benchmark와 비교해 고객이 실제로 돈을 낼 만한지 평가한다.

특히 부대표 또는 비전문가 persona가 이해하지 못하는 유료 리포트는 quality pass가 아니다.

또한 QA는 "파이프라인이 복잡하다"는 이유로 산출물의 약한 통찰을 용인하지 않는다. 고객이 돈을 내는 대상은 자동화 구조가 아니라 결과물의 판단 효용이다.

---

## 2. When QA Runs

다음 산출물이 발행/발송되기 *직전*에 QA gate 의무.

| Artifact | QA 의무 | Cross-LLM 의무 |
| --- | --- | --- |
| Free weekly issue | Yes | 권장 |
| Paid weekly issue | Yes | Yes (cross-LLM) |
| Custom paid memo | Yes | Yes (cross-LLM) |
| Marketing copy (X thread, post, email) | Yes | 권장 |
| Paid landing page | Yes | Yes |
| 환불/약관 페이지 | Yes (Legal과 동행) | Yes |
| 다국어 번역본 | Yes | **Yes (의무)** |
| Pre-Mortem memo (high-impact 결정) | No (별도 절차) | N/A |
| Internal docs (CLAUDE.md, AGENTS.md 갱신) | No (Red Team 영역) | N/A |

QA가 작동하는 시점: VP review + Red Team + Legal review가 모두 통과한 *직후*. 대표 publish 결정 *직전*.

---

## 3. QA Checklist Categories

### 3.1 Factual Accuracy

| 점검 | 방법 |
| --- | --- |
| 모든 factual claim에 source 존재 | 문장별 source URL 매핑 |
| source 원문이 claim을 *실제로* 지지함 | Claude/Gemini로 source 본문과 claim 대조 |
| 숫자/통계가 source와 일치 | numerical extraction + 원문 비교 |
| 인용문 정확성 | exact quote 일치 확인 |
| 회사명/제품명/인물명 표기 정확 | 공식 표기 DB 참조 |
| 날짜 정확 (announcement, paper, IPO 등) | 원문 source date 확인 |
| 추정/예측은 *추정/예측으로* 명시됨 | "predict", "expect", "likely" 표현 명확 |
| claim posture 명시 | `verified / company-self-report / speculative` 분류 확인 |

block 사유:
- source 없는 factual claim
- source 원문이 claim을 지지하지 않음
- 인용문 변형 (paraphrase를 quote로 표기)
- 연도/날짜 오류
- `company-self-report`를 독립 검증처럼 서술

### 3.2 Format / Schema

| 점검 | 방법 |
| --- | --- |
| issue template의 필수 필드 모두 존재 | schema validation script |
| 헤딩 hierarchy 일관 (H1 → H2 → H3) | markdown lint |
| 코드/링크/이미지 marker 정상 렌더링 | rendering preview |
| disclaimer 포함 (`docs/operations/LEGAL_REVIEW_PLAYBOOK.md §7`) | string match |
| paid teaser 위치 일관 | template diff |
| publication metadata 정확 (date, author, issue number) | metadata field |
| 유료 상품이면 한국어+영어 edition 존재 | edition check |

block 사유:
- 필수 필드 누락
- disclaimer 누락
- broken markdown rendering

### 3.3 Link Integrity

| 점검 | 방법 |
| --- | --- |
| 모든 외부 link HTTP 200 | automated link checker |
| paywall source 인용 부적합 (FT/Bloomberg 등) | source allowlist 비교 |
| 내부 archive link 정상 | platform routing test |
| affiliate / tracker 미포함 (Phase 1에서는 사용 안 함) | URL pattern match |
| 잘못된 redirect 없음 | follow-redirect check |

block 사유:
- 404 link
- paywall behind 인용 (저작권 risk)
- 의도치 않은 affiliate parameter

### 3.4 Terminology Consistency

| 점검 | 방법 |
| --- | --- |
| 같은 회사명을 issue 내 일관 표기 (예: "Boston Dynamics" vs "보스턴 다이나믹스") | terminology DB |
| 기술 용어 한국어 표기 일관 (예: "임바디드 AI" vs "embodied AI") | terminology DB |
| 단위 일관 (₩, $, %, MW 등) | unit lint |
| 약어 첫 등장 시 풀이 (예: "RLHF (Reinforcement Learning from Human Feedback)") | first-occurrence check |

권장 terminology DB 위치: `docs/product/TERMINOLOGY.md` (roadmap, 후속 작성).

### 3.5 Brand Voice / Tone

| 점검 | 방법 |
| --- | --- |
| 단정적 투자/예측 표현 *없음* | 표현 pattern match (`docs/strategy/MARKETING_STRATEGY.md §6` 참조) |
| 1인칭 일관 (지나친 "전문가" 자칭 X) | tone classifier |
| 직장인 일상어 + 일부 전문용어 (해설 동반) | readability score |
| paid 콘텐츠도 free와 같은 voice 유지 | sample diff |

### 3.5.1 Vice President / Non-Expert Hurdle

유료 산출물은 부대표 또는 비전문가 persona가 이해할 수 있어야 한다.

| 점검 | 방법 |
| --- | --- |
| 1분 내 제품 가치 이해 | 부대표가 "이걸 왜 읽는지" 한 문장으로 설명 |
| 어려운 용어 차단 | jargon list + 쉬운 설명 존재 여부 |
| 투자 관련 의미의 안전한 설명 | buy/sell 없이 company/technology watchlist 제공 |
| 무료 글과 유료 상품 차이 | paid value table 존재 |
| 일반 독자 신뢰감 | 과장/사기성/허세 표현 표시 |
| 개인화 가치 | 고객 관심사 또는 watchlist 반영 여부 |

block 사유:

- 부대표가 핵심 thesis를 이해하지 못함
- 비전문가 persona가 "돈 낼 이유"를 찾지 못함
- 전문용어가 설명 없이 반복됨
- 투자 권유처럼 보임
- 고객별 가치가 전혀 없음

### 3.6 Multi-Language Fluency (다국어 발행 시)

| 점검 | 방법 |
| --- | --- |
| native fluency (LLM A 단독 평가 *부족*) | LLM A draft → LLM B independent review |
| terminology 한국어 ↔ 번역 언어 매핑 일관 | bilingual terminology DB |
| 문화적 맥락 적절 (영문에서 한국 직장 문화 표현 부적합 등) | LLM B cultural fit review |
| 통화/단위/날짜 형식 적합 | format check by language |
| disclaimer 해당 언어로 작성 (직역 X) | template per language |

자세한 절차: `docs/governance/LANGUAGE_POLICY.md §7 Translation Workflow`.

### 3.7 Competitive Benchmark Quality

유료 산출물은 경쟁사 공개 샘플 또는 승인된 유료 벤치마크와 비교해야 한다.

| 점검 | 방법 |
| --- | --- |
| report anatomy | SemiAnalysis / Stratechery / ARK / CB Insights 등 benchmark와 비교 |
| decision utility | 독자가 다음에 무엇을 tracking할지 알 수 있는지 |
| chart/table quality | 최소 1개 표, chart, scorecard, market map 포함 |
| customer memory | 고객 관심사/질문/watchlist 반영 |
| paid/free boundary | 무료와 유료 차이가 명확한지 |
| delivery readiness | web/email/PDF 중 어떤 방식으로 전달되는지 명확한지 |
| local pain-point connection | 한국 독자/현장 관점의 실질적 pain point 또는 decision implication 존재 |

block 사유:

- 단순 뉴스 요약 수준
- 표/scorecard/watchlist 없음
- benchmark 대비 paid value 약함
- delivery method 불명확
- 고객별 personalization 없음
- 로컬 컨텍스트를 지어내거나, 반대로 전혀 연결하지 못함

### 3.8 Customer Memory / Upgrade Reuse Verification

고객별 feedback, watchlist, question, paid hesitation, product upgrade event가 누적된 뒤 생성되는 산출물은 해당 데이터를 실제로 참조했는지 QA가 검증한다.

| 점검 | 방법 |
| --- | --- |
| memory usage record 존재 | `artifact_memory_usage`에 artifact_type/artifact_id 기록 |
| 고객 관심사 반영 | 관련 `customer_interest_tags` 또는 segment summary 참조 |
| watchlist 반영 | 관련 `customer_watchlists` 참조 |
| 고객 질문 반영 | 관련 `customer_questions` 중 open/high-priority 질문 처리 |
| product upgrade 반영 | 관련 `product_upgrade_events` 참조 |
| consent 확인 | `customer_profiles.consent_personalization=true` 확인 |
| 금지정보 미사용 | 보유종목, 매매의도, 자산규모 등 민감/투자자문성 정보 미사용 |
| 다른 상품 재사용 가능성 | upgrade event가 적용 가능한 다른 product에 연결되었는지 확인 |

block 사유:

- 개인화 상품인데 memory usage record가 없음
- 고객 feedback을 참조했다고 주장하지만 DB 근거가 없음
- consent 없는 고객 data로 개인화
- 민감 투자정보를 저장 또는 사용
- 동일한 고객 pain이 누적됐는데 product upgrade backlog에 반영되지 않음

---

## 4. Cross-LLM Workflow

### 4.1 단일 LLM 사용 가능 (저-위험 산출물)

- weekly issue (free)
- 짧은 marketing post (X thread, 미디어 출처 명확)

### 4.2 Cross-LLM 의무 (고-위험 산출물)

- paid weekly issue
- custom paid memo
- 다국어 번역본
- 결제 페이지 / 환불 약관 / paid landing
- 첫 발행되는 새 format (template change)

### 4.3 권장 페어

| Artifact | LLM A (primary) | LLM B (independent) |
| --- | --- | --- |
| 한국어 paid issue | Claude | Gemini |
| 영문 paid memo | Claude | GPT reasoning |
| 다국어 번역 | Claude | Gemini (cultural localization) |
| 결제 페이지 카피 | Claude | GPT reasoning (Legal과 동행) |
| 광고 카피 | Claude | GPT reasoning |

### 4.4 절차

1. QA Agent가 산출물을 LLM A에 *§3 체크리스트*와 함께 전달
2. LLM A의 issue list 수집
3. *동일 산출물*을 LLM B에 *LLM A 결과 보지 않은 상태로* 독립 검토
4. 두 결과 머지
5. 두 LLM 모두 issue 없음 → `qa_clear`
6. 한 LLM 이상이 critical issue → `qa_block` + 원작성 agent로 회송
7. 두 LLM 결과 충돌 → third LLM 또는 인간(부대표/대표) 결정

### 4.5 Audit Trail

- 검토 LLM 이름 + 모델 버전
- prompt path
- 두 검토 결과 path (Notion 저장)
- 최종 결정자 (자동 또는 인간)
- decision timestamp

audit trail 누락 시 `qa_clear` 부여 *금지*.

---

## 5. Output Templates

### 5.1 qa_clear

```markdown
# QA Report — qa_clear

- Date:
- Artifact: (issue / memo / copy / page / 약관 / 번역본)
- Artifact path:
- Reviewer LLM A:
- Reviewer LLM B (if cross-LLM):
- Cross-LLM mandatory: yes / no

## Findings
- Factual: clear
- Format/Schema: clear
- Link integrity: clear (N links checked)
- Terminology: clear
- Brand voice: clear
- (Multi-language) Fluency: clear

## Recommendations (non-blocking)
- (있을 경우 minor 개선 제안)

## Decision
- [x] qa_clear

## Audit trail
- LLM A output: notion://...
- LLM B output: notion://...
- Timestamp:
```

### 5.2 qa_block

```markdown
# QA Report — qa_block

- Date:
- Artifact:
- Artifact path:
- Reviewer LLM A:
- Reviewer LLM B (if cross-LLM):

## Critical issues (block 사유)
- 1.
- 2.

## Required corrections
- 1. [원작성 agent에게] ...
- 2. ...

## Non-blocking suggestions
- 1.
- 2.

## Decision
- [x] qa_block
- Returned to: (originating agent)
- Re-submission needed after corrections

## Audit trail
- LLM A output: notion://...
- LLM B output: notion://...
- Timestamp:
```

---

## 6. Distinct from Other Reviews

| Review | Question Asked | Block Authority |
| --- | --- | --- |
| Vice President content review | "일반 독자가 *읽고 공유*할 수 있나?" | recommend revise (final 결정은 대표) |
| Red Team Agent | "*거짓/과장/약한 근거/worst case*가 있는가?" | block recommendation (final 결정은 대표) |
| Legal Counsel Agent | "*규제/저작권/약관/개인정보* 위반인가?" | hard block (`legal_review_block`) |
| **QA Agent** | "*사실/형식/링크/용어/언어*가 정확한가?" | hard block (`qa_block`) |

QA의 핵심: *사실과 형식*. *해석과 의도*는 다른 review의 영역.

QA가 *읽고 어색하다*고 느껴도 readability 영역은 부대표에게 넘긴다. *팩트 오류*가 있으면 block.

---

## 7. Detailed Checklist by Artifact

### 7.1 Weekly Issue (free)

- [ ] 5~7개 신호 모두 source 매핑
- [ ] 각 신호의 "왜 중요한가" 1~2문장
- [ ] "한국 산업 implication" 단락 존재
- [ ] disclaimer 포함 (`docs/operations/LEGAL_REVIEW_PLAYBOOK.md §7.1`)
- [ ] paid tier teaser 포함 (template 위치)
- [ ] 모든 외부 link 200 응답
- [ ] terminology DB 일관
- [ ] issue number / publication date metadata 정확

### 7.2 Paid Issue / Custom Memo

- 7.1 모두 +
- [ ] cross-LLM verification 통과
- [ ] paid-only deep dive 단락 존재
- [ ] paid disclaimer 포함 (`§7.2` 또는 `§7.3`)
- [ ] paid subscriber list 외 노출 방지 metadata (paywall flag)

### 7.3 Marketing Copy (X thread, post, email)

- [ ] thread 흐름 자연 (LLM A read-through)
- [ ] CTA 명확 (sign-up URL 포함)
- [ ] disclaimer 또는 "정보 제공" 명시 (Legal copy)
- [ ] image alt text 또는 미사용
- [ ] terminology 일관

### 7.4 Paid Landing Page

- [ ] 가격 명시 (`docs/strategy/PRICING.md` active price 일치)
- [ ] 환불 정책 링크 (한국 소비자보호법 7일)
- [ ] 약관 / 개인정보 처리방침 링크
- [ ] disclaimer (§7.4)
- [ ] CTA 명확 (단일 결제 버튼)
- [ ] 결제 PG 통합 정상 (sandbox test)

### 7.5 Multi-Language Translation

- 7.1 또는 7.2 모두 +
- [ ] **cross-LLM verification 의무**
- [ ] terminology bilingual DB 일관
- [ ] 통화/단위/날짜 형식 해당 언어 적합
- [ ] disclaimer 해당 언어 native (`docs/governance/LANGUAGE_POLICY.md §7`)
- [ ] cultural localization 점검 (LLM B)
- [ ] 가능 시 native reviewer 추가 검토

---

## 8. Failure Handling

### 8.1 qa_block 시

```
QA Agent qa_block
    ↓
원작성 agent로 회송 (correction request)
    ↓
원작성 agent가 수정
    ↓
QA Agent 재검토 (rerun §3 체크리스트)
    ↓
qa_clear 또는 second qa_block
    ↓
2회 연속 qa_block → 부대표 또는 대표에게 escalate
```

### 8.2 Cross-LLM 충돌 시

- LLM A: clear / LLM B: block → 인간(부대표/대표) 결정
- LLM A: block / LLM B: clear → block (안전 default)
- 둘 다 block (다른 사유) → 두 사유 모두 원작성에 전달

### 8.3 LLM 일시 미가용

- cross-LLM 의무 산출물에 대해 LLM B 미가용 시: *qa_clear 보류*
- single-LLM 허용 산출물은 LLM A 단독 진행 + audit trail에 명시

### 8.4 Time Pressure (긴급 발행)

- 긴급 발행이라도 QA 단계 *생략 불가*
- 단, abbreviated checklist 사용 가능 (factual + link + disclaimer만, format/terminology는 후처리)
- abbreviated 사용 시 발행 후 24시간 내 full QA 의무 + correction 발행

---

## 9. Tooling

### 9.1 자동화 가능 항목

- link integrity check (curl + status code)
- markdown lint (markdownlint)
- schema validation (jsonschema or Codex script)
- terminology DB lookup (단순 string match)
- numerical claim extraction (Codex regex)

이 항목들은 QA Agent (Codex)가 자동 실행. 결과는 audit trail에 첨부.

### 9.2 LLM 평가 항목

- factual claim과 source 대조 (Claude / Gemini)
- 인용문 정확성 (Claude)
- multi-language fluency (Claude + Gemini)
- brand voice 일관 (Claude)

### 9.3 인간 review 항목 (선택적)

- 첫 paid memo 발송 시 (대표 직접 read-through)
- 다국어 native reviewer 외주 (Phase 2)

---

## 10. KPIs

| KPI | Target | Trigger |
| --- | --- | --- |
| qa_clear pass rate (1차) | 80%+ | 70% 미만 시 원작성 agent 품질 강화 |
| qa_block 사유 분포 | factual 30% 이하 | 30% 초과 시 source 검증 강화 |
| broken link incidents (post-publish) | 0 | 1건 이상 발생 시 link checker 강화 |
| factual error reported by reader (post-publish) | 0 | 1건 이상 발생 시 cross-LLM 의무 확대 |
| QA cycle time (artifact 도착 → 결정) | <30 min (single-LLM) / <60 min (cross-LLM) | 초과 시 자동화 강화 |

---

## 11. Quick Reference

| 상황 | 행동 |
| --- | --- |
| 새 weekly issue 발행 직전 | §7.1 checklist + LLM A review → qa_clear 또는 회송 |
| paid memo 발행 직전 | §7.2 + cross-LLM 의무 |
| 다국어 번역 발행 | §7.5 + cross-LLM 의무 + 가능 시 native reviewer |
| factual error 발견 | qa_block + 원작성에 회송, *publish 차단* |
| broken link만 있고 factual 정상 | qa_block (link 수정 후 재검토) |
| LLM B 응답 없음 (cross-LLM 의무 산출물) | qa_clear 보류, LLM B 응답 받을 때까지 대기 |
| 긴급 발행 요청 | abbreviated QA 가능 + 24시간 내 full QA 의무 |
| 같은 issue가 2회 연속 qa_block | 부대표/대표 escalate, 원작성 agent 재훈련 검토 |
