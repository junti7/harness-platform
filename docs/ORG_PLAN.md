# Organization Plan
# Version: 2.3
# Date: 2026-05-10

---

## 1. Current Organization

| Function | Owner | Notes |
| --- | --- | --- |
| Editor-in-chief, final publishing, pricing, capital decisions | President/CEO | 모든 high-impact 의사결정 최종 승인 |
| **CEO Chief of Staff** | Codex | 대표/부대표 지시사항 checklist 관리, 누락 방지, LLM 병렬 작업 분배, 검토 패킷/PDF/Slack brief 생성 |
| Content quality, reader empathy, Korean readability | Vice President | 발행 전 readability + shareability gate |
| Training and readiness | HR Training Team | 부대표 OJT, assessment, 대표 보고 |
| Code / schema / automation | Codex | production 변경은 Red Team cross-LLM 후 진행 |
| Local filtering | Ollama / local models | Tier 2 gate |
| Strategy / research synthesis | Claude or equivalent when configured | high-context 분석, 전략 memo |
| Long-context document review | Gemini (roadmap) | 긴 논문/PDF/멀티모달 |
| Independent evaluator / scoring | GPT reasoning (roadmap) | scoring rubric, ambiguous case |
| **Legal Counsel** | Legal Counsel Agent (cross-LLM) | 광고/규제/저작권/약관/개인정보 사전검토. high-risk 시 외부 변호사 자문 권고 |
| **Red Team (Cross-LLM)** | Red Team Agent | 코드 + MD 문서 + high-impact 의사결정의 서로 다른 LLM 2개 이상 cross-verify |
| **Product Planning** | Product Planning Agent | 상품 정의, 패키징, 가격 ladder, 기능 priority |
| **Marketing Strategy** | Marketing Strategy Agent | 익명 고객 acquisition 전략, persona, 채널 mix, content calendar |
| **Subscriber Growth (execution)** | Subscriber Growth Agent | Marketing Strategy의 실행 arm, organic content 발행, copy distribution |
| **Sales** | Sales Agent | paid funnel, conversion 실험, 가격 테스트, onboarding, churn |
| **QA** | QA Agent | 고객-facing 산출물의 발행 직전 fact + format + schema + link + terminology + 다국어 fluency 검증 (`qa_clear`/`qa_block`) |
| **Language Policy** | Product Planning Agent + 대표 | `docs/governance/LANGUAGE_POLICY.md` Phase 정책 운영. Phase 1 = 한국어 + 영어 on-demand 만 허용 |
| Publisher | Publisher Agent | Notion/Slack/PDF 발행 및 system of record 유지 |
| Mobile decision routing | OpenClaw + `scripts/openclaw_codex_bridge.py` on 24/7 host | 대표/부대표 모바일 승인 surface |

수익 창출 대상 원칙:

- 부대표 또는 대표의 주변 인맥은 paid acquisition target이 아니다.
- 모든 결제 매출은 Marketing Strategy → Subscriber Growth → Sales 파이프라인을 통해 유입되는 *익명 독자*에서 발생해야 한다.

---

## 2. 12-Month Target Organization

| Function | Future Need |
| --- | --- |
| Editorial | weekly issue, paid issue, memo quality |
| Research | Physical AI / robotics analyst network |
| Engineering | collection, filtering, archive, publishing automation |
| Growth | subscriber acquisition, distribution, retention |
| Product | subscription, memo, archive, possible dashboard |
| Marketing Strategy | persona refinement, paid acquisition test, brand 운영 |
| Sales | paid retention, custom memo lead 처리, B2B inbound qualification |
| Legal Counsel | 외부 변호사 자문 retainer (필요 시), 약관/광고 update |
| Red Team | LLM diversification (Claude + Gemini + GPT 셋 다 active) |
| HR Training | Vice President domain growth and future editor onboarding |

Hiring, contractor spend, paid distribution, 외부 변호사 자문, or new tooling requires President approval and, if money moves, `capital_action_approve` + `legal_review_approve` + `pre_mortem_approve`.
