# Current Staffing
# Version: 1.2
# Date: 2026-05-10

---

## 1. Official Role Mapping

Official documents use role titles rather than personal nicknames.

| Official Role | Current Staffing Status | Notes |
| --- | --- | --- |
| President/CEO | Filled (human) | 최종 의사결정권자 |
| Vice President | Filled (human) | content quality gate, reader empathy |
| HR Training Team | Agent-assisted internal function | 부대표 OJT 운영 |
| Engineering Agent | Codex | 코드/스키마/자동화 |
| Strategy/Research Agent | Claude or equivalent when configured | 전략 memo, 합성 |
| Long-context Review Agent | Gemini (roadmap, when CLI/API integrated) | 긴 논문/문서/멀티모달 |
| Independent Evaluator Agent | GPT reasoning models (roadmap) | scoring, ambiguous case |
| **Legal Counsel Agent** | Cross-LLM (Claude + Gemini or GPT) | 광고/규제/저작권/약관/개인정보 사전검토 |
| **Red Team Agent (Cross-LLM)** | Always pair of distinct reasoning LLMs | 코드/MD/의사결정 cross-verify |
| **Product Planning Agent** | Claude or GPT reasoning + Codex (data analysis) | 상품 정의, 패키징, 가격 ladder |
| **Marketing Strategy Agent** | Claude (전략) + GPT reasoning (persona/channel) | 익명 고객 acquisition 전략 |
| Subscriber Growth Agent | Claude (copy) + Codex (분포 도구) | Marketing Strategy 실행 arm |
| **Sales Agent** | GPT reasoning (funnel) + Claude (소통) + Codex (data) | paid funnel 운영, conversion 실험 |
| **QA Agent** | Codex (link/schema 자동검증) + Claude (factual 대조) + Gemini (long-context source 매핑) | 고객-facing 산출물 발행 직전 final 품질 gate. 다국어 콘텐츠는 cross-LLM 의무 |
| Publisher Agent | Codex + Notion API | 발행 및 archive |

Personal nicknames are intentionally excluded from official operating documents.

---

## 2. Cross-LLM Pairing Rule

Red Team과 Legal Counsel은 *항상 서로 다른 두 reasoning LLM의 독립 검토*로 운영한다. 동일 LLM 반복 호출은 cross-verification으로 인정하지 않는다.

권장 페어:

- 코드 변경 review: Claude + (Gemini or GPT reasoning)
- MD 문서 갱신 review: Claude + Gemini
- 전략/투자 memo: Claude + GPT reasoning
- Marketing/광고 copy: Claude + GPT reasoning
- Legal review: Legal Counsel Agent + Red Team second view (서로 다른 LLM)
- QA factual + source 대조: Claude + Gemini (long-context 원문 매핑)
- 다국어 번역 QA: Claude (1차 fluency) + Gemini (cultural localization) + 가능 시 native reviewer

리소스가 일시 미가용한 경우, agent는 사용 가능한 LLM 조합을 audit trail에 명시하고 high-impact 결정은 보류한다.

---

## 3. Language Coverage

| Language | Coverage | QA reviewer |
| --- | --- | --- |
| 한국어 | Phase 1 primary | 부대표 + QA Agent (Claude/Gemini) |
| English | Phase 1 secondary, on-demand | QA Agent cross-LLM (Claude + Gemini), 가능 시 native reviewer |
| 일본어 | Phase 2 후순위 | native reviewer 외주 확보 후 |
| 중국어 (간체/번체) | Phase 1/2 진입 금지 | N/A |
| 기타 (독일어/스페인어/프랑스어 등) | Phase 3 이후 검토 | N/A |

상세 정책은 `docs/governance/LANGUAGE_POLICY.md` 참조.
