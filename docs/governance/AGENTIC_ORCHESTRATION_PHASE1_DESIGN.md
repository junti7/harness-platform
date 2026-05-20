# AGENTIC ORCHESTRATION — PHASE 1 DESIGN
# Version: 0.1 | Date: 2026-05-20 | Owner: Chief of Staff (Jarvis)
# 상위 규약: AGENTIC_ORCHESTRATION_CHARTER.md (ACTIVE 2026-05-20)

---

## 0. 목표 (2주)

CEO order가 OpenClaw를 거쳐 Jarvis에게 도달하고, Jarvis가 persona들에게 task를 배정하면, 각 persona가 자기 home 채널에서 의견을 내고 `#회의실`에서 토론·수렴해 Jarvis가 CEO decision card로 상신하는 **end-to-end 루프 1회**를 실제로 작동시킨다 (Charter §4.4).

Phase 1 범위 persona: **Jarvis(이미 정의)**, **Friday**, **KITT**. 나머지는 Phase 2+.

### Acceptance Criteria (Charter §10 kill-criteria 연동)
- [ ] CEO가 Slack에서 order 1건 → `#회의실`에 Friday+KITT 토론이 가시화됨
- [ ] Jarvis가 합의/미합의를 DB에 기록하고 CEO card 상신
- [ ] 전 과정이 단일 correlation_id로 묶임
- [ ] per-order LLM 비용이 cap($2.00) 이하로 측정·기록됨
- [ ] **이 2주간 weekly issue 발행이 중단되지 않음** (병행 의무)
- [ ] 로그 없는 채널 0건 (`check_slack_channel_log.py` green)

---

## 1. 재사용 맵 (이미 존재하는 부품)

새로 만들지 말고 아래를 확장한다.

| 기존 자산 | 역할 | Phase 1에서의 확장 |
|---|---|---|
| `scripts/dispatch_llm_task_packet.py` | provider(claude/gemini/copilot) CLI 호출 + 결과를 route에 포스트 | **persona-keyed**로 일반화 (provider 대신 persona) |
| `adapters/content/slack_router.py` | route→channel 매핑, bot/webhook 전송, Phase 1 collapse | persona home 채널 + 회의실 route 추가, collapse 해제 |
| `adapters/content/slack_listener.py` | CEO DM/mention 진입점 → `agent_run` | orchestration order 감지 시 Jarvis relay로 분기 |
| `scripts/openclaw_codex_bridge.py` | task-packet / route-note / record-decision | `orchestrate` 액션 추가 (relay 진입) |
| `agents/<handle>/` | persona 정의 (SYSTEM_PROMPT/MEMORY/CHANNEL) | Friday, KITT 추가 |
| `core.cost_alerts` | 일일 비용 경보 | per-order 누적 비용 집계 추가 |

---

## 2. 채널 계획 + SLACK_PHASE 결정 (핵심 설계 긴장)

### 문제
현재 `slack_router._active_route()`는 `SLACK_PHASE=phase1`(기본값)일 때 `PHASE1_ROUTE_ALIASES`로 모든 rich route를 3개 활성 채널로 collapse한다. 이 상태에서는 persona 채널·회의실이 별도로 존재할 수 없다 — 전부 `#ops-incidents` 등으로 합쳐진다.

### 결정
orchestration 채널은 collapse 대상에서 **제외**한다. 두 가지 방법 중 택1:

- **(A) 권장** — orchestration 전용 route 4개를 신설하고 `PHASE1_ROUTE_ALIASES`에 넣지 않는다 (collapse 안 됨). 기존 archived route collapse 정책은 그대로 유지.
- (B) `SLACK_PHASE=orchestration` 새 모드 도입 — 복잡도 증가. 비권장.

### 신설 채널 (각 SLACK_CHANNEL_CREATION_LOG.md entry 선행 필수)

| 채널 | route key | 환경변수 | data_class | owner |
|---|---|---|---|---|
| `#team-friday` | `team_friday` | `SLACK_CHANNEL_TEAM_FRIDAY` | public-internal | Friday |
| `#team-kitt` | `team_kitt` | `SLACK_CHANNEL_TEAM_KITT` | confidential (법률) | KITT |
| `#회의실` | `conference_room` | `SLACK_CHANNEL_CONFERENCE_ROOM` | public-internal | Jarvis |
| (Jarvis는 기존 `#exec-president-decisions` 사용) | — | — | confidential | Jarvis |

> **주의:** 실제 Slack 채널 생성은 visible/공유 상태 변경이므로 CEO 확인 후 실행한다. 본 설계는 채널 목록 + 로그 entry 초안을 제시할 뿐, 자동 생성하지 않는다.

---

## 3. 빌드 컴포넌트

### 3.1 Persona Registry (`agents/registry.py` 신규)
`agents/README.md` 매핑표를 코드로 노출. persona handle → {provider, slack_route, channel_env, system_prompt_path, memory_path}.

```
PERSONAS = {
  "jarvis":  {provider: "codex",  route: "exec_president_decisions", ...},
  "friday":  {provider: "claude", route: "team_friday", ...},
  "kitt":    {provider: "claude", route: "team_kitt", ...},
}
```

### 3.2 Persona Runner (`scripts/run_persona.py` 신규, dispatch_llm_task_packet 일반화)
- 입력: persona handle, task packet, correlation_id
- persona의 SYSTEM_PROMPT.md를 로드해 provider CLI 호출 (claude/gemini/codex)
- 출력을 persona home 채널에 포스트 + `docs/reports/llm_outputs/`에 저장
- 비용을 correlation_id에 누적 (cost guard)
- MEMORY.md에 일기 append (Charter §8 형식)

### 3.3 Orchestration Relay (`adapters/content/orchestrator.py` 신규)
Jarvis의 핵심. 흐름:
```
1. CEO order + correlation_id 수신 (slack_listener / bridge orchestrate)
2. Jarvis(Codex)가 order 분해 → 어느 persona 필요한지 결정
3. 각 persona를 run_persona로 호출 → home 채널에 개별 의견
4. 2개 이상 persona면 #회의실 소집 (3.4)
5. Jarvis가 합의/미합의 정리 → DB 기록 → CEO card 상신
```

### 3.4 회의실 Convening (orchestrator 내부)
- 관련 persona 의견을 모아 `#회의실`에 포스트
- 라운드제: 각 persona가 다른 persona 의견에 1회 반응 (autonomous CC)
- **CC 깊이 cap 3 hop** (Charter §5) — 초과 시 Jarvis 강제 수렴
- 결론: consensus / dissent를 DB에 기록 (대화 자체는 SoR 아님, §4.1)

### 3.5 Cost Guard
- correlation_id별 누적 LLM 비용 추적 (기존 log_api_cost 확장)
- $2.00 초과 시 추가 persona 호출 차단 + `expensive_run_approve` 요청 메시지
- 일일 cap은 기존 `DAILY_COST_LIMIT_USD` 유지

---

## 4. DB 레코드 (최소 신규)

기존 테이블 재사용 우선. 신규는 최소화.

| 레코드 | 용도 | 신규/재사용 |
|---|---|---|
| `orchestration_runs` | order별 correlation_id, 상태, 누적 비용, 결론 | 신규 (migration) |
| `persona_opinions` | persona별 의견 + 출력 artifact path | 신규 또는 `agent_reviews` 재사용 검토 |
| `ceo_decisions` | 최종 CEO 결정 | 재사용 (기존) |

> migration은 Phase 1 구현 착수 시 작성. 스키마 누락 상태로 실행 금지 (CLAUDE.md preflight).

---

## 5. 2주 작업 순서

| 일자 | 작업 | 산출물 |
|---|---|---|
| D1-2 | persona registry + Friday/KITT 정의 파일 | `agents/registry.py`, `agents/{friday,kitt}/` |
| D3-4 | 채널 4개 로그 entry 작성 + (CEO 확인 후) 생성 + route 추가 | SLACK_CHANNEL_CREATION_LOG.md, slack_router route |
| D5-6 | run_persona.py (단일 persona end-to-end) | persona 1명 의견이 home 채널에 포스트됨 |
| D7-8 | orchestrator relay (Jarvis 분해 + 다중 persona 호출) | 다중 persona 의견 |
| D9-10 | 회의실 convening + CC cap + 합의 정리 | #회의실 토론 가시화 |
| D11-12 | cost guard + orchestration_runs migration + DB 기록 | per-order 비용 측정 |
| D13 | bridge `orchestrate` 액션 + slack_listener 분기 | CEO Slack → end-to-end |
| D14 | 2주 체크포인트: kill-criteria 점검 + goal_health_brief | continue/pause/rollback 결정 |

---

## 6. CEO 결정 (2026-05-20 확정)

1. ✅ **채널 생성** — `#team-friday`, `#team-kitt`, `#회의실` 지금 생성 진행 (로그 entry 선행).
2. ✅ **SLACK_PHASE 정책** — 방법 A (orchestration route는 collapse 제외).
3. ✅ **per-order 비용 cap** — $2.00 유지.
4. ✅ **회의실 토론 라운드** — 다라운드 (고품질, CC 3 hop 한도 내).
5. ✅ **발화 스타일** — 채널·회의실은 구어체 자유 토론 (Charter §4.3). DB 산출물은 구조적.

---

## 7. Phase 1 → Phase 2 진입 조건
Acceptance Criteria 전부 충족 + D14 체크포인트에서 대표 continue 결정. 미충족 시 Charter §10에 따라 pause/rollback.
