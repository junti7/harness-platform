# Slack Operating System
# Version: 1.4
# Date: 2026-05-10

---

## 1. Purpose

Slack은 Harness의 모바일 command surface다.

현재 사업 단계에서는 채널 수를 늘리지 않는다. 첫 외부 매출 전까지 Slack은 3개 채널만 active로 사용한다.

---

## 2. Active Channels

| Channel | Purpose | Posting Rule |
| --- | --- | --- |
| `#exec-president-decisions` | 대표 승인, 유료 제안, 자본 집행 후보 | high-impact decision only |
| `#vp-content-review` | 부대표 콘텐츠 검토, 한국어 자연스러움, 독자 공감, paid hesitation | concise review notes only |
| `#ops-incidents` | 실패, 권한, 비용, 보안 incident | incident and run exception only |

아카이브된 세부 채널을 다시 만들지 않는다. 세부 분리는 첫 paying customer 이후 필요성이 확인될 때만 재검토한다.

---

## 3. Phase 1 Routing

`SLACK_PHASE=phase1`에서는 기존 route가 아래 3개 active channel로 흡수된다.

| Original Intent | Active Channel |
| --- | --- |
| executive decisions, reports, paid offer, capital action | `#exec-president-decisions` |
| Vice President content review, training, reader-empathy notes | `#vp-content-review` |
| agent runs, engineering, model tasks, permissions, failures | `#ops-incidents` |

`adapters/content/slack_router.py`는 archived route로 들어온 메시지에 Phase 1 routing context를 붙여 active channel로 보낸다.

신규 거버넌스/상업 agent의 routing은 다음과 같이 active channel로 흡수한다. 별도 채널은 첫 paying customer 이후 필요성이 입증될 때 재검토한다.

| Agent / Source | Intended Future Channel | Phase 1 Active Channel |
| --- | --- | --- |
| Legal Counsel Agent (`legal_review_approve` / `legal_review_block` / regulatory memo) | `#legal-reviews` | `#exec-president-decisions` (high-impact) / `#ops-incidents` (block) |
| Red Team Agent (`red_team_clear` / `red_team_block`, cross-LLM audit trail) | `#red-team-cross-checks` | `#exec-president-decisions` (block on high-impact) / `#ops-incidents` (others) |
| Pre-Mortem memo (worst-case 첨부) | `#exec-president-decisions` | `#exec-president-decisions` (대표 승인 카드와 함께) |
| Product Planning Agent (product_brief, packaging, pricing ladder) | `#product-planning` | `#exec-president-decisions` |
| Marketing Strategy Agent (marketing_plan, persona, channel mix, content calendar) | `#marketing-strategy` | `#exec-president-decisions` (전략 변경) / `#vp-content-review` (카피) |
| Subscriber Growth Agent (organic post draft, distribution status) | `#growth-experiments` | `#vp-content-review` (카피 review) / `#ops-incidents` (실행 실패) |
| Sales Agent (funnel metrics, conversion experiment, churn) | `#sales-funnel` | `#exec-president-decisions` |
| QA Agent (`qa_clear` / `qa_block`, fact/format/link/schema/terminology issues, 다국어 fluency) | `#qa-final-gate` | `#vp-content-review` (revise 요청) / `#ops-incidents` (block) |
| Language Policy 변경 (Phase 진입 트리거 발동 등) | `#exec-president-decisions` | `#exec-president-decisions` |

모든 routing payload는 `intended_channel` metadata를 보존해 추후 채널 분리 시 자동 마이그레이션 가능하게 한다.

---

## 4. Environment Variables

Required:

- `SLACK_DELIVERY_MODE=bot`
- `SLACK_PHASE=phase1`
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS`
- `SLACK_CHANNEL_VP_CONTENT_REVIEW`
- `SLACK_CHANNEL_OPS_INCIDENTS`

Archived channel IDs should not remain in `.env`.

---

## 5. Rules

- 대표 채널에는 중간 로그를 보내지 않는다.
- 부대표 채널에는 긴 원문과 agent transcript를 기본 노출하지 않는다.
- secret, webhook, API key 값은 어떤 채널에도 쓰지 않는다.
- Codex 혼자 수행한 분석을 multi-model 검토가 완료된 것처럼 표시하지 않는다.
- 반복 LLM 작업은 CLI/API command trail 없이 완료 처리하지 않는다.
- 빈 채널 수를 운영 성숙도의 신호로 착각하지 않는다.

---

## 6. Archived Channels

다음 채널들은 Phase 1 운영 단순화를 위해 아카이브했다.

- `#exec-capital-actions`
- `#exec-daily-brief`
- `#vp-customer-narratives`
- `#vp-relationship-map`
- `#hr-vp-ojt`
- `#hr-vp-assessments`
- `#hr-president-reports`
- `#intel-evidence-feed`
- `#intel-signals`
- `#intel-opportunities`
- `#intel-research-reviews`
- `#revenue-experiments`
- `#customer-validation`
- `#product-reports`
- `#eng-codex`
- `#agent-github-copilot`
- `#agent-claude-strategy`
- `#agent-gemini-research`
- `#agent-gpt-evaluation`
- `#agent-local-gate`
- `#agent-openclaw-routing`
- `#ops-agent-runs`
- `#security-permissions`
