# OpenClaw Codex Integration
# Version: 1.0
# Date: 2026-05-10

---

## 1. Purpose

OpenClaw는 Harness의 command center, task router, mobile approval surface로 사용한다.
Codex는 codebase execution, schema/code changes, pipeline operations를 담당한다.

현재 브리지와 skill은 저장소에 정의되어 있고, 24/7 호스트에서는 OpenClaw CLI와 gateway까지 배치 가능한 상태다. Codex 측에는 `scripts/openclaw_codex_bridge.py`를 두어, OpenClaw가 붙는 표준 진입점을 고정한다.

이 문서의 목표는 다음 세 가지다.

- OpenClaw가 Codex 작업을 호출할 단일 command surface를 정의
- 대표/부대표 승인 흐름과 Slack/Notion archive 흐름을 우회하지 않게 보장
- OpenClaw 미설치 상태에서도 bridge smoke test를 수행 가능하게 유지

---

## 2. Current Integration State

| Layer | Status | Notes |
| --- | --- | --- |
| Codex execution | Active | 현재 세션에서 직접 실행 |
| Slack routing | Active | `adapters/content/slack_router.py` |
| Decision card JSON/text | Active | `adapters/content/decision_card.py` |
| President decision persistence | Active | `scripts/ceo_decision.py` + `ceo_decisions` |
| OpenClaw bridge surface | Active | `scripts/openclaw_codex_bridge.py` |
| OpenClaw CLI binary | Active on 24/7 host | `192.168.0.203`에 설치 및 onboard 완료 |
| OpenClaw gateway | Active on 24/7 host | local mode, loopback bind, token auth |
| `harness-control` skill | Active on 24/7 host | `openclaw skills info harness-control` 통과 |
| Cron automation | Active on 24/7 host | heartbeat + daily ops brief 등록 완료 |

따라서 현재 단계는 `operational-on-host` 상태다. 로컬 개발 머신은 authoring/debug, 24/7 호스트는 control plane 운영을 담당한다.

---

## 3. Supported Bridge Commands

### 3.1 Status

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py status --format json
```

확인 항목:

- OpenClaw / Claude / Gemini / Copilot / Ollama CLI 유무
- Postgres 연결 가능 여부
- Slack / Notion secret 유무
- Phase 1 active route

### 3.2 Decision Card

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py decision-card signal 1 --format json
```

출력 형식:

- `text`: 모바일 요약
- `json`: OpenClaw payload
- `slack-json`: Slack Block Kit payload

### 3.3 Record Decision

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py record-decision signal 1 approved signal_approve --reason "mobile approve"
```

제약:

- `approval_type`는 canonical enum만 허용
- `capital_action_approve`는 `CAPITAL_ACTIONS_ENABLED=true` 없이는 거부

### 3.4 Route Note

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py route-note agent_openclaw_routing "OpenClaw test message"
```

용도:

- OpenClaw 작업 시작/종료 기록
- 인간 승인 대기 상태 표시
- bridge heartbeat

### 3.5 Task Packet

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py task-packet research "Competitor benchmark refresh" \
  --objective "Collect and compare new competitor report samples" \
  --input-artifact docs/library/competitor_intelligence/index.md \
  --output-artifact docs/reports/competitor_refresh.md \
  --check "legal review required before external use" \
  --route agent_openclaw_routing
```

용도:

- OpenClaw가 다른 LLM/skill에 재배포할 표준 JSON 생성
- input artifact, output artifact, checks, callback command를 고정

### 3.6 Pipeline Run

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py run-pipeline --notify-slack
```

용도:

- OpenClaw command center에서 파이프라인 실행 요청
- 실행 시작 알림을 Slack route에 남김

### 3.7 Ops Brief Publish

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py publish-ops-brief --to-slack --to-notion --route exec_daily_brief
```

용도:

- OpenClaw control-plane 상태를 Slack daily brief와 Notion archive에 동시 반영
- 동일 결과를 `agent_reviews`에 ops health review로 적재

### 3.8 Approval Card Push

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py push-approval-card research_report 7 --route exec_president_decisions
```

용도:

- 모바일 승인용 decision card를 executive route로 직접 전달

### 3.9 External LLM Task Packet Dispatch

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py dispatch-task-packet benchmark "Competitor report benchmark" \
  --objective "Collect competitor report evidence and summarize product gaps" \
  --input-artifact docs/COMPETITIVE_LANDSCAPE.md \
  --provider gemini \
  --provider copilot
```

용도:

- Claude, Gemini, Copilot CLI로 packetized delegation
- output artifact와 dispatch status를 `docs/reports/llm_outputs`에 보존

---

## 4. Operational Rules

1. OpenClaw는 approval semantics를 재해석하지 않는다. canonical rules는 `CLAUDE.md §4`, `core/approval.py`를 따른다.
2. OpenClaw는 고위험 의사결정에서 원문 생성자가 아니다. task routing, visible audit trail, mobile action surface를 담당한다.
3. Slack route는 직접 channel name을 하드코딩하지 않고 route name을 통해 전달한다.
4. President 또는 Vice President에게 올라가는 card/payload는 비서실장(Codex) 검토를 거친다.
5. 외부 발행 전에는 Legal, Red Team, QA precondition이 충족되어야 한다.

---

## 5. Recommended OpenClaw Attachment

OpenClaw가 설치되면 가장 먼저 붙일 액션은 아래 세 가지다.

1. `/harness status`
   - 내부적으로 `openclaw_codex_bridge.py status --format json`
2. `/harness decision-card <target_type> <id>`
   - 내부적으로 `openclaw_codex_bridge.py decision-card ... --format json`
3. `/harness approve <target_type> <id> <approval_type>`
   - 내부적으로 `openclaw_codex_bridge.py record-decision ...`

이 세 가지만 연결돼도 모바일 승인과 task routing의 핵심 루프가 열린다.

---

## 6. Next Steps

1. `runtime/openclaw_status.json`을 Notion ops DB 또는 Slack digest와 연결
2. cron 결과를 `agent_reviews` 또는 전용 audit log schema에 적재
3. `harness-control`에서 approval card push와 daily brief routing을 분리
4. Claude/Gemini/Copilot CLI 인증이 풀리면 task-packet 배포를 실운영으로 연결

---

## 7. 24/7 Deployment Principle

OpenClaw는 노트북의 보조 도구가 아니라 대표/부대표 승인과 agent routing의 control plane으로 취급한다. 따라서 기본 배치 원칙은 다음과 같다.

1. OpenClaw는 24/7 상시 전원이 유지되는 장비에 둔다.
2. Codex 작업 브리지는 같은 장비 또는 같은 LAN의 항상 켜진 호스트에서 실행한다.
3. 개인 노트북은 authoring/debug 용도이고, 운영 허브는 아니다.

권장 호스트:

- Mac mini
- 사내 24/7 Linux host
- 항상 켜진 workstation

현재 저장소는 24/7 배치를 위해 다음 파일을 포함한다.

- `scripts/openclaw_bridge_heartbeat.py`
- `infra/com.harness.openclaw-bridge.plist.template`
- `infra/setup_mac_mini.sh` 내 OpenClaw bridge heartbeat 등록 단계

Heartbeat 목적:

- bridge dependency 상태를 `runtime/openclaw_status.json`에 주기적으로 기록
- 대표 승인 허브가 내려갔는지 빠르게 감지
- OpenClaw CLI 설치 전에도 control-plane readiness를 유지

현재 등록된 OpenClaw cron:

- `harness-control-heartbeat`
  - 주기: 30분
  - 세션: `isolated`
  - delivery: `none`
- `harness-daily-ops-brief`
  - 주기: 매일 09:05 `Asia/Seoul`
  - 세션: `isolated`
  - delivery: `none`
- `harness-weekly-competitor-benchmark`
  - 주기: 매주 월요일 10:15 `Asia/Seoul`
  - 세션: `isolated`
  - delivery: `none`
  - 현재 provider: `gemini`
  - 비고: Claude/Copilot 원격 인증 완료 전까지는 Gemini-only로 운영
