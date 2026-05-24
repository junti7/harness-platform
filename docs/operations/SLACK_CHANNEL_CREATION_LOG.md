# SLACK CHANNEL CREATION LOG
# Owner: Chief of Staff (Jarvis) | Gate: AGENTIC_ORCHESTRATION_CHARTER §6
# 상위 규약: CLAUDE.md (Must rule), docs/operations/SLACK_OPERATING_SYSTEM.md

---

## 목적

각 persona(팀장)는 Slack 채널을 자율 신설할 수 있다. **단, 신설 전 이 파일에 entry를 먼저 기록해야 한다.**

대표 지시 (2026-05-19): "각 팀장이 개별적으로 판단하면 되는데 그 log는 반드시 남겨야 해. 왜, 무슨 이유로 channel을 신설했는지."

**로그 entry 없이 생성된 채널은 정책 위반이다.** `scripts/check_slack_channel_log.py`가 매일 Slack 실제 채널 목록과 이 로그를 대조해, 로그 없는 채널을 `#ops-incidents`에 경보한다.

---

## 네이밍 컨벤션

persona/팀 채널은 `team-<handle>-<팀명한글>` 형식을 쓴다 (예: `team-friday-사업운영팀`). Slack은 채널명에 괄호·공백을 허용하지 않으므로 하이픈으로 팀명을 붙인다. `#회의실` 등 비-팀 채널은 예외.

## Entry 작성 절차

1. 채널을 만들기 **전에** 아래 표에 행을 추가한다.
2. 모든 필수 필드를 채운다 (빈 칸 금지).
3. PII/confidentiality class를 반드시 선언한다 (Charter §9).
4. 그 다음 Slack에서 채널을 생성한다.
5. 생성 후 channel_id를 entry에 보강한다.

---

## 필수 필드 정의

| 필드 | 설명 |
|---|---|
| `date` | 신설 일자 (YYYY-MM-DD) |
| `creator` | 신설 persona handle (예: Jarvis, Friday, KITT) |
| `channel_name` | `#` 포함 채널명 |
| `channel_id` | Slack channel ID (생성 후 보강) |
| `why` | 왜 이 채널이 필요한가 (목적) |
| `basis` | 무슨 근거로 신설을 판단했나 (어떤 order/task/규약) |
| `participants` | 예상 참여 persona / 인간 |
| `data_class` | `public-internal` / `confidential` / `PII` (Charter §9) |
| `owner` | 채널 운영 책임 persona |
| `retention` | 보존/폐기 trigger (예: "프로젝트 종료 시 archive", "30일 무활동 시 archive") |

---

## Log

| date | creator | channel_name | channel_id | why | basis | participants | data_class | owner | retention |
|---|---|---|---|---|---|---|---|---|---|
| 2026-05-20 | Jarvis | `#example-do-not-create` | _(EXAMPLE ONLY)_ | 스키마 사용 예시. 실제 채널 아님. | Charter §6 예시 행 | Jarvis, CEO | public-internal | Jarvis | 예시 — 생성 금지 |

> 위 행은 **형식 예시**다. 실제 채널이 아니며 생성하지 않는다.

### Phase 1 채널 (2026-05-20, 대표 confirm "지금 생성 진행")

| date | creator | channel_name | channel_id | why | basis | participants | data_class | owner | retention |
|---|---|---|---|---|---|---|---|---|---|
| 2026-05-20 | Jarvis | `#team-friday-사업운영팀` | `C0B5VKL6PTJ` (public) | Friday(PM/BizOps) persona의 home 채널 — 사업/제품 개별 의견·분석을 가시화 | Phase 1 Design §2 + Charter §4.2 | Friday, Jarvis, CEO/VP(관찰) | public-internal | Friday | Phase 1 종료 시 재평가, 90일 무활동 시 archive |
| 2026-05-20 | Jarvis | `#team-kitt-법무팀` | `C0B4Z950J4W` (private) | KITT(Legal) persona의 home 채널 — 법적 리스크 검토·자문 | Phase 1 Design §2 + Charter §9 | KITT, Jarvis, CEO/VP(관찰, 초대 필요) | confidential | KITT | 법률 검토 보존: 90일 무활동 시 archive, 상세 자문 원문은 채널 외 보관 |
| 2026-05-20 | Jarvis | `#회의실` | `C0B5VKLRFNC` (public) | persona 집단 토론 공간 (META 환경) — 구어체 자유 토론·수렴 | Charter §4.3 + Phase 1 Design | Jarvis, Friday, KITT, CEO/VP(관찰) | public-internal | Jarvis | 상시 운영 |
| 2026-05-20 | Jarvis | `#team-vision-상품기획팀` | `C0B4V5PJ5R9` (public) | Vision(상품기획팀) persona home — 사업운영팀과 성격이 달라 분리 (대표 지시) | Charter §2.3 split + AGENTS.md §3.12 | Vision, Jarvis, CEO/VP(관찰) | public-internal | Vision | Phase 1 종료 시 재평가, 90일 무활동 시 archive |
| 2026-05-21 | Jarvis | `#team-c3po-마케팅팀` | `C0B4YSALX3P` (public) | C3PO(마케팅팀) persona home — 전 팀 활성화 (대표 지시) | AGENTS.md §3.13+§3.10A | C3PO, Jarvis, CEO/VP(관찰) | public-internal | C3PO | 90일 무활동 시 archive |
| 2026-05-21 | Jarvis | `#team-coach-인사팀` | `C0B4LQANT0F` (public) | Coach(인사팀) persona home | AGENTS.md §3.7 | Coach, Jarvis, CEO/VP(관찰) | public-internal | Coach | 90일 무활동 시 archive |
| 2026-05-21 | Jarvis | `#team-watchman-리스크팀` | `C0B5065J5EJ` (public) | Watchman(리스크팀) persona home | AGENTS.md §3.8+§3.16 | Watchman, Jarvis, CEO/VP(관찰) | public-internal | Watchman | 90일 무활동 시 archive |
| 2026-05-21 | Jarvis | `#team-scribe-qa팀` | `C0B4YSB7B0V` (public) | Scribe(QA팀) persona home | AGENTS.md §3.14A | Scribe, Jarvis, CEO/VP(관찰) | public-internal | Scribe | 90일 무활동 시 archive |
| 2026-05-21 | Jarvis | `#team-tars-엔지니어링팀` | `C0B506653M4` (public) | TARS(엔지니어링팀) persona home | AGENTS.md Codex eng | TARS, Jarvis, CEO/VP(관찰) | public-internal | TARS | 90일 무활동 시 archive |
| 2026-05-23 | Jarvis | `#team-ledger-cfo` | `C0B6JN0PL2C` (private) | Ledger(CFO) persona home — burn/runway, budget guard, unit economics, capital readiness 개별 의견 | User request 2026-05-23 + AGENTS.md §3.14C | Ledger, Jarvis, CEO/VP(관찰, 초대 필요) | confidential | Ledger | 90일 무활동 시 archive |

---

## 위반 처리

- 로그 없는 채널 탐지 시: 해당 채널 동결 + 생성 persona 추적 + `#ops-incidents` 기록.
- 반복 위반: HR_PENALTY_SYSTEM.md / STAFF_PENALTY_LEDGER.md 절차 적용.
