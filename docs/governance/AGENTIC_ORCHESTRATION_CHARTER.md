# AGENTIC ORCHESTRATION CHARTER
# Version: 0.1 (DRAFT — pending pre_mortem_approve + President confirm)
# Date: 2026-05-20
# Owner: Chief of Staff (Jarvis)
# 상위 규약: docs/product/PLATFORM.md > CLAUDE.md > AGENTS.md > 이 문서

---

## 0. 상태 및 전제

**ACTIVE (2026-05-20 대표 confirm).** 다음 두 조건이 충족되어 효력 발생:

1. ✅ `docs/governance/PRE_MORTEM_2026-05-20_agentic_orchestration.md` `pre_mortem_approve` — 대표 confirm 2026-05-20
2. ✅ Business Reality Constraint override 서면 confirm — 대표 confirm 2026-05-20 (weekly issue 병행 유지, 2주 체크포인트 kill-criteria 동의, 전략적 베팅임을 수용)

이 Charter는 기존 거버넌스를 **대체하지 않고 그 위에 orchestration layer를 추가**한다. 충돌 시 PLATFORM.md → CLAUDE.md → AGENTS.md가 우선한다.

---

## 1. 목적

harness-platform을 pipeline 실행기에서 **관찰 가능한 에이전트 조직**으로 전환한다. 핵심은 4가지다.

1. **Slack-as-workspace** — 팀 작업과 토론이 Slack 채널에서 가시화되어 CEO/VP가 실시간 관찰 가능.
2. **Autonomous CC** — 비서실장이 모든 라우팅을 독점하지 않고, 팀 에이전트가 맥락상 필요한 다른 팀을 직접 호출.
3. **Episodic memory** — 각 에이전트가 작업 경험을 일기로 축적하고 다음 작업에 활용.
4. **Persona** — 역할에 인격(handle)을 부여해 출력 일관성과 책임 추적성을 높임.

이 4가지는 **수단**이다. 목적은 변하지 않는다: artifact quality, factual trust, paid conversion. (CLAUDE.md Product-over-Pipeline Rule 계승)

---

## 2. 역할 경계 (R&R)

### 2.1 인간 (변경 없음)

| 역할 | 권한 | 이 Charter에서의 추가 책임 |
|---|---|---|
| President (CEO) | 최종 의사결정, 자본 집행, 전략 전환 | **Active Operator** (§7): 채널 관찰, 개입, 중재 권한 보유 |
| Vice President (VP) | content quality gate, reader empathy | 채널 관찰, content 관련 팀 토론에 직접 피드백 |

CEO/VP는 수동적 관찰자가 아니다. 언제든 어느 채널에든 개입·중단·재지시할 수 있다 (§7 override protocol).

### 2.2 비서실장 (Jarvis)

기존 AGENTS.md §3.-1 CEO Chief of Staff Agent와 동일 인격. 추가 orchestration 책임:

- CEO/VP order를 task로 분해하고 담당 persona의 채널에 할당.
- 팀 간 충돌 중재 (autonomous CC가 합의에 도달하지 못할 때).
- 최종 보고를 CEO decision card로 통합 (기존 cos_approve 게이트 유지).
- per-order 비용/시간 cap 감시 (§5).

비서실장은 **여전히 최종 게이트웨이**다 (AGENTS.md §3.-1). autonomous CC가 도입돼도 CEO/VP 상신 전 비서실장 approve는 생략 불가.

### 2.3 팀 에이전트 (Persona)

기존 AGENTS.md의 에이전트를 인격화한다. **신규 persona 신설은 첫 paid subscriber 확보 시까지 동결** (대표 지시 2026-05-19).

**런타임 source of truth는 `agents/registry.py`다.** 아래 표는 그 요약이며, 충돌 시 registry가 우선한다.

| Persona | 팀 (org chart) | 기존 AGENTS.md | Primary LLM | 상태 |
|---|---|---|---|---|
| **Jarvis** | 비서실장 (Chief of Staff) | §3.-1 | Codex | ✅ active (P0) |
| **Friday** | 사업운영팀 (Business Operations) | §3.14B | Claude | ✅ active (P1) |
| **Vision** | 상품기획팀 (Product Planning) | §3.12 | Claude | ✅ active (P1) |
| **KITT** | 법무팀 (Legal) | §3.11 | Claude (게이트는 +Gemini) | ✅ active (P1) |
| **C3PO** | 마케팅팀 (Marketing + Growth) | §3.13 + §3.10A | Claude | defined, inactive (P2) |
| **Coach** | 인사팀 (HR Training) | §3.7 | Claude | defined, inactive (P2) |
| **Watchman** | 리스크팀 (Red Team + BRM) | §3.8 + §3.16 | Claude (+Gemini) | defined, inactive (P2) |
| **Scribe** | QA팀 | §3.14A | Codex | defined, inactive (P2) |
| **TARS** | 엔지니어링팀 | Codex eng | Codex | defined, inactive (P2) |
| Eve / Data / Tron / Joi | (미매핑) | — | — | **frozen — 신설 금지** |

persona handle은 cosmetic layer다. 기존 에이전트의 권한·금지·decision boundary(AGENTS.md §3~§4)는 그대로 상속된다.

**확대 방법 (scalability):** 팀 추가는 코드 변경이 아니다 — registry 항목 `active=True` + persona 파일 3개 + 로그된 채널 1개. 회의실 소집은 `get_active_personas()`를 순회하므로 active 전환 시 자동 합류한다. 단, 상품기획팀을 사업운영팀에서 분리하려면 Friday를 두 persona로 split (활성화 시점에 결정).

---

## 3. Persona ≠ Gate (non-negotiable, M3)

**가장 중요한 안전 조항.**

persona 이름이 "Watchman(Red Team)", "KITT(Legal)", "Scribe(QA)"라 하더라도, 단일 persona 에이전트의 출력은 동명의 CLAUDE.md 거버넌스 게이트를 **충족하지 않는다**.

| Persona 출력 | ≠ | 거버넌스 게이트 | 게이트 충족 요건 |
|---|---|---|---|
| Watchman 의견 | ≠ | `red_team_clear` | 서로 다른 LLM 최소 2개 (AGENTS.md §3.8) |
| KITT 의견 | ≠ | `legal_review_approve` | 서로 다른 LLM 최소 2개 (AGENTS.md §3.11) |
| Scribe 의견 | ≠ | `qa_clear` | cross-LLM (다국어 의무, §3.14A) |

- 단일 LLM persona의 self-review를 cross-LLM 게이트로 기록하면 CLAUDE.md §6 위반.
- 게이트 통과는 기존 cross-LLM 절차(RED_TEAM_PROTOCOL.md, LEGAL_REVIEW_PLAYBOOK.md, QA_PLAYBOOK.md)를 그대로 따른다.
- persona는 게이트를 *준비·코디네이트*할 수 있으나 *충족 선언*은 못 한다.

---

## 4. Slack-as-Workspace

### 4.1 원칙
- 팀 작업 토론은 해당 persona의 home 채널에서 이루어진다.
- CEO/VP는 모든 채널을 read 가능 (관찰).
- **system of record 우선순위: DB > Slack.** Slack은 가시성 layer이지 진실의 원천이 아니다 (CLAUDE.md §5 계승). 의사결정·승인·산출물은 DB/bridge에 기록하고, Slack에는 그 요약·토론을 남긴다.
- 충돌 시 DB 기록이 Slack 대화를 이긴다.

### 4.2 채널 유형
| 유형 | 예 | 용도 |
|---|---|---|
| **Exec 채널** | `#exec-president-decisions` | CEO/VP 의사결정 surface (유지) |
| **VP review** | `#vp-content-review` | 부대표 content review (유지) |
| **Incident** | `#ops-incidents` | 장애·경보 (유지) |
| **Persona home 채널** | `#team-friday`, `#team-kitt` 등 | 각 persona가 *혼자* 의견·작업을 내는 공간 |
| **회의실 (Conference Room)** | `#회의실` / `#war-room` | 여러 persona가 *함께* 토론해 최적안을 도출하는 공간 |

기존 3개 활성 채널은 유지 (SLACK_OPERATING_SYSTEM.md). persona home 채널과 회의실은 §6 절차로 신설.

### 4.3 회의실 (Conference Room) — META 환경의 핵심

대표 비전 (2026-05-20): 각 에이전트가 자기 채널에서 개별 의견을 내고, **회의실에서는 함께 토론**하는 META 환경.

- **회의실**은 단일 order에 대해 여러 persona가 동시에 모여 의견을 교환·반박·수렴하는 공유 채널이다.
- persona home 채널 = 개인 작업/의견. 회의실 = 집단 토론.
- 회의실 토론은 CEO/VP가 read-only로 실시간 관찰 (META 환경).

**발화 스타일 (대표 지시 2026-05-20, 2026-05-20 정정):** 채널·회의실에서는 **회사 동료처럼 공손한 존댓말 구어체로 자유롭게 토론**한다. **반말 금지** — 회사에서는 반말을 쓰지 않는다. 동의·반박·질문·되묻기는 허용되지만 항상 존댓말로 한다. 딱딱한 보고서 문체("~을 검토한 결과 다음과 같습니다") 금지. 다른 persona를 호칭할 때 **'님'을 붙인다** (예: "Friday님 말씀도 맞는데, 법적으로는 좀 걸립니다"). **단 두 가지는 말투와 무관하게 유지된다:**
- DB에 기록되는 *최종 산출물*(CEO decision card, legal_review_note, memo)은 정확·구조적으로 작성.
- 구어체 토론이라도 거버넌스(Persona≠Gate §3, PII §9, 게이트 precondition)는 절대 완화되지 않는다.
- 토론은 무한정 돌지 않는다: **autonomous CC 깊이 cap (order당 최대 3 hop, §5)** 과 비서실장 강제 수렴이 적용된다.
- 회의실의 결론은 비서실장이 **합의안(consensus) 또는 미합의(dissent) 기록**으로 정리하고, DB에 남긴 뒤 CEO decision card로 상신한다.
- 회의실 대화 자체는 system of record가 아니다 (§4.1). 결론·근거만 DB에 기록.

### 4.4 OpenClaw 명령 릴레이 + META 루프

OpenClaw는 CEO 명령의 **command center / relay**다 (CLAUDE.md §3 OpenClaw role 계승). 전체 흐름:

```
1. CEO order  ──(Slack/모바일)──▶  OpenClaw
2. OpenClaw   ──(bridge)──▶  Jarvis (비서실장): order 분해 + R&R 분석 + task 할당
3. Jarvis     ──▶  각 persona home 채널에 task 배정
4. 각 persona ──▶  자기 채널에서 분석·의견 작성 (개별)
5. 관련 persona ──▶  #회의실 소집 → 토론·반박·수렴 (집단, 자율 CC)
6. Jarvis     ──▶  회의실 합의/미합의 정리 + 비용·게이트 점검
7. Jarvis     ──▶  CEO decision card 상신 (#exec-president-decisions)
8. CEO        ──▶  approve / reject / hold / 개입 (§7 Active Operator)
```

- CEO/VP는 2~7 전 과정을 채널 관찰로 모니터링 가능.
- 단계 6에서 high-impact 결정이면 게이트(red_team_clear/legal/qa/pre_mortem)는 §3 Persona≠Gate 원칙에 따라 *별도 cross-LLM 절차*로 충족해야 한다 — 회의실 토론으로 대체 불가.
- 모든 단계는 correlation_id로 묶여 per-order 비용·감사 추적 (§5).

---

## 5. 비용·시간·규모 cap (M2, non-negotiable)

autonomous orchestration의 비용 폭주를 막는 강제 한도. 모든 값은 초기 보수값이며 대표가 조정한다.

| Cap | 초기값 | 초과 시 |
|---|---|---|
| per-order LLM 비용 | $2.00 / single CEO order | 자동 중단 + `expensive_run_approve` 요청 |
| 일일 LLM 비용 | 기존 `DAILY_COST_LIMIT_USD` 계승 | cost_alerts 경보 (core.cost_alerts) |
| active persona 작업 채널 수 | 8 | 초과 신설 차단, 비서실장 검토 |
| autonomous CC 깊이 | order당 최대 3 hop | 초과 시 비서실장 중재로 강제 수렴 |
| 주간 founder 개편 시간 | 대표가 설정 | 초과 시 체크포인트 강제 |

- `expensive_run_approve`는 이 Charter가 도입하는 **내부 운영 게이트**(자본 집행 아님). canonical approval type 아님 — DB capital gate와 무관.
- per-order 비용 추적은 correlation_id 단위로 집계 (CLAUDE.md §5 Must: 모든 action에 correlation_id).

---

## 6. Channel Creation Log Gate (M5, non-negotiable)

각 persona(팀장)는 Slack 채널을 자율 신설할 수 있다. **단, 신설 전 `docs/operations/SLACK_CHANNEL_CREATION_LOG.md`에 entry를 먼저 기록해야 한다.** (대표 지시 2026-05-19: "왜, 무슨 이유로 channel을 신설했는지 log 필수")

- **로그 없는 채널 = 정책 위반.** `scripts/check_slack_channel_log.py`가 일일 reconciliation으로 로그 없는 채널을 탐지해 `#ops-incidents`에 경보.
- 로그 필수 필드: date, creator(persona), channel name, why, basis, expected participants, PII/confidentiality class, owner, expiry/retention trigger.
- 이 규칙은 CLAUDE.md Must rule로 승격 예정 (Task #6 patch).

---

## 7. Active Operator Override Protocol (Gemini gap)

CEO/VP는 언제든 다음을 행사할 수 있다.

| 행동 | 방법 | 효과 |
|---|---|---|
| **관찰** | 모든 채널 read | 제약 없음 |
| **개입** | 해당 채널에 직접 메시지/지시 | persona는 즉시 반영, 진행 중 작업 조정 |
| **중단(halt)** | `@Jarvis halt <order-id>` 또는 채널 지시 | 해당 order의 모든 persona 작업 즉시 정지 |
| **중재(arbitrate)** | 충돌 사안에 대표 결정 | persona 합의보다 우선 (AGENTS.md §8 계승) |
| **override** | RED_TEAM_PROTOCOL §3.2 절차 | non-negotiable finding 기각 시 서면 사유 필수 |

- 비서실장은 halt 신호를 받으면 진행 중 LLM 호출을 중단하고 상태를 DB에 기록.
- 대표 결정이 에이전트 권고와 충돌하면 대표 결정 우선, 단 에이전트는 risk memo 첨부 가능 (AGENTS.md §8).

---

## 8. Episodic Memory (일기) 표준

각 persona는 `agents/<handle>/MEMORY.md`에 작업 reflection을 append한다.

### 8.1 일기 entry 형식
```
## <YYYY-MM-DD> <correlation_id> <one-line task>
- what_i_did:
- what_worked:
- what_failed:
- lesson:
- confidence: low | medium | high
```

### 8.2 메모리 규칙 (M4 + Codex gap)
- **검증되지 않은 주장을 operational fact로 승격 금지.** 일기의 `lesson`은 가설이며, 거버넌스 게이트를 거치지 않은 내용을 사실처럼 인용할 수 없다.
- **PII 평문 기록 금지.** subscriber 개인정보, 결제정보, 대표/부대표 사적 정보는 일기·채널에 평문 저장 불가 (AGENTS.md §3.14/§3.14B 계승).
- 일기는 append-only. 과거 entry 수정 시 정정 entry를 새로 추가.
- 다음 작업 시작 시 관련 일기 검색은 Phase 3에서 구현 (초기 키워드 매칭, vector는 추후).

---

## 9. PII / 보존 / 접근 정책 (M4, non-negotiable)

| 데이터 등급 | 정의 | Slack 채널 | agent memory |
|---|---|---|---|
| **public-internal** | 일반 작업 토론, 기술 분석 | 허용 | 허용 |
| **confidential** | 미발행 전략, 가격, 투자 thesis | 제한 채널만, expiry 명시 | 요약만, 원문 금지 |
| **PII** | subscriber 개인정보, 결제, 사적 정보 | **평문 금지** | **평문 금지** |

- 채널·일기의 데이터 등급은 channel creation log의 PII/confidentiality class 필드로 선언.
- confidential 채널은 expiry/archival trigger 필수.
- 삭제 정책: PII 오기록 발견 시 즉시 삭제 + ops-incidents 기록.

---

## 10. Kill-Criteria & 2주 체크포인트 (M1, non-negotiable)

개편이 사업을 잠식하지 않도록 강제 off-ramp를 둔다.

### 10.1 병행 의무
개편 기간에도 **weekly issue 발행은 중단하지 않는다.** 개편은 issue 발행을 대체하지 못한다.

### 10.2 2주 체크포인트 (Phase 1 종료 시점)
다음 중 **하나라도** 해당하면 개편을 중단하고 재평가한다.

- 직전 2주간 weekly issue 발행 0회
- 무료 구독자 순증 0
- 누적 LLM 비용이 사전 합의 cap 초과
- daily ops brief 연속 실패 (운영 안정성 붕괴, CLAUDE.md §8)

### 10.3 재평가 결과
체크포인트에서 BizOps(Friday)가 goal_health_brief를 작성하고, 대표가 continue / pause / rollback 결정. 결과는 DB + 이 Charter changelog에 기록.

---

## 11. Phase 로드맵

| Phase | 기간 | 산출물 | 진입 조건 |
|---|---|---|---|
| **0** | 1주 | 이 Charter, channel log, enforcement script, Jarvis persona, CLAUDE.md patch draft, Pre-Mortem | pre_mortem_approve + 대표 confirm |
| **1** | 2주 | Slack 관찰 가능성, persona home 채널 + **회의실** 가동, 첫 팀(Friday/KITT) 인격화, OpenClaw 릴레이 루프(§4.4) 1차 연결 | Phase 0 완료 |
| **2** | 2주 | autonomous CC, 회의실 집단 토론·수렴, 비서실장 중재자화 | Phase 1 체크포인트 통과 |
| **3** | 3주 | episodic memory 검색, 일기 자동화 | Phase 2 안정화 |
| **4** | 보류 | drift 모니터링, 신규 persona(Eve/Data/Tron/Joi) | **첫 paid subscriber 후** |

각 Phase는 이전 Phase 안정화 후 진행 (한 번에 하나).

---

## 12. Changelog

| Date | Version | Change |
|---|---|---|
| 2026-05-20 | 0.1 | Initial draft. Red Team (Claude+Gemini+Codex) non-negotiable 5건 반영. pre_mortem_approve 대기. |
| 2026-05-20 | 1.0 | 대표 confirm. ACTIVE 전환. 회의실(§4.3) + OpenClaw 릴레이(§4.4) 반영. Phase 1 진입. |
