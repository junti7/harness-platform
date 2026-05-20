# CLAUDE.md PATCH DRAFT — Agentic Orchestration

# Status: DRAFT, NOT APPLIED. 대표 검토 + pre_mortem_approve 후에만 CLAUDE.md에 반영.
# Date: 2026-05-20 | Author: Claude (Opus 4.7) | Red Team: Claude+Gemini+Codex 2026-05-20

---

## 적용 조건

이 patch는 다음 충족 전까지 **적용 금지**다.

1. `PRE_MORTEM_2026-05-20_agentic_orchestration.md`에 대한 대표 `pre_mortem_approve`
2. Business Reality Constraint override에 대한 대표 서면 confirm

아래는 CLAUDE.md에 가할 변경의 before/after 제안이다.

---

## 변경 1 — §1 Business Reality Constraint (override 명시 + 안전장치)

### Before
> 첫 paid subscriber가 발생하기 전까지 B2B sales infra, dashboard, channel 확장, 미통합 LLM 자동화는 revenue-critical blocker가 아닌 한 보류한다.

### After (추가)
> 첫 paid subscriber가 발생하기 전까지 B2B sales infra, dashboard, channel 확장, 미통합 LLM 자동화는 revenue-critical blocker가 아닌 한 보류한다.
>
> **[2026-05-20 임시 예외 — Agentic Orchestration]** 대표 지시로 agentic orchestration 개편(`docs/governance/AGENTIC_ORCHESTRATION_CHARTER.md`)을 한시적 최우선 순위로 격상한다. 이는 **고위험 전략적 베팅**이며 evidence 기반 결론이 아님을 명시적으로 수용한다 (Red Team non-negotiable). 다음 안전장치가 강제된다:
> - 개편 기간에도 weekly issue 발행은 **중단하지 않는다**.
> - Charter §10 kill-criteria + 2주 체크포인트가 적용된다. 충족 시 개편을 pause/rollback한다.
> - per-order LLM 비용 cap(Charter §5)을 초과하면 자동 중단한다.

---

## 변경 2 — §1 Product-over-Pipeline Rule (정합성 단서 추가)

### Before
> 이 조건을 충족하지 않는 Tier 확장, 채널 증설, control-plane polish는 보류한다.

### After (추가)
> 이 조건을 충족하지 않는 Tier 확장, 채널 증설, control-plane polish는 보류한다.
>
> **Agentic orchestration 예외 단서:** 개편은 이 규칙의 *예외*가 아니라 *시한부 베팅*이다. orchestration 인프라가 artifact quality / factual trust / paid conversion을 직접 개선하지 못하면, Charter §10 체크포인트에서 성공으로 보고하지 않고 중단 검토한다. "에이전트 수 늘리기"는 목적이 될 수 없다.

---

## 변경 3 — §5 Must (channel creation log Must rule 추가)

### After (신규 항목 추가)
> - Slack 채널 신설 전 `docs/operations/SLACK_CHANNEL_CREATION_LOG.md`에 entry(왜·근거·data_class·owner·retention 포함)를 먼저 기록한다. 로그 없는 채널 생성은 금지된다 (`scripts/check_slack_channel_log.py` 일일 검증).
> - persona의 단일 LLM 의견을 cross-LLM 거버넌스 게이트(`red_team_clear`/`legal_review_approve`/`qa_clear`)로 기록하지 않는다 (Charter §3 Persona ≠ Gate).

---

## 변경 4 — §6 Never (항목 추가)

### After (신규 항목 추가)
> - persona 인격(Watchman/KITT/Scribe 등)을 동명의 거버넌스 게이트 충족으로 위장하지 않는다.
> - 로그 entry 없이 Slack 채널을 신설하지 않는다.
> - agentic orchestration 개편으로 weekly issue 발행을 대체하거나 중단하지 않는다.

---

## 변경 5 — §10 문서 역할 테이블 (신규 문서 등록)

### After (테이블에 행 추가)
> | `docs/governance/AGENTIC_ORCHESTRATION_CHARTER.md` | persona orchestration layer 헌법. Slack-as-workspace, 회의실, autonomous CC, episodic memory, 비용/PII/kill-criteria |
> | `docs/operations/SLACK_CHANNEL_CREATION_LOG.md` | persona의 Slack 채널 신설 로그 (Charter §6 gate) |
> | `docs/governance/PRE_MORTEM_2026-05-20_agentic_orchestration.md` | 개편 결정의 worst-case 분석 (pre_mortem_approve 대상) |

---

## 변경 6 — §9 Environment Variables (검토 항목, 신규 cap 변수 후보)

orchestration cap을 환경변수로 외부화할 경우 후보 (Phase 1에서 구현 시):
> - `ORCHESTRATION_PER_ORDER_COST_LIMIT_USD` (기본 2.00)
> - `ORCHESTRATION_MAX_ACTIVE_CHANNELS` (기본 8)
> - `ORCHESTRATION_MAX_CC_HOPS` (기본 3)

이 변수들은 Phase 1 구현 시점에 추가 검토. Phase 0에서는 Charter 문서값으로만 운영.

---

## 미해결 / 대표 결정 필요

- 변경 1의 override는 대표 서면 confirm이 있어야 효력 발생. 그 전까지 CLAUDE.md 원문 유지.
- cap 수치(§5)는 초기 보수값. 대표가 운영 데이터 보고 조정.
