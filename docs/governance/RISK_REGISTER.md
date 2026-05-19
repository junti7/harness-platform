# RISK REGISTER
# Owner: Business Risk Management Team
# Cadence: 주간 업데이트 (매주 월요일 CEO risk_brief 발행)
# Version: 1.0 | Created: 2026-05-19

---

## 리스크 레지스터 구조

| 필드 | 설명 |
| --- | --- |
| ID | 고유 리스크 ID (예: FIN-001, OPS-001) |
| 유형 | 재무 / 운영 / 전략 / 법적·규제 / 평판 / 기술 |
| 설명 | 리스크 내용 요약 |
| 발생 확률 | low / medium / high |
| 영향도 | low / medium / high / critical |
| 현재 상태 | open / mitigating / resolved / accepted |
| 완화 조치 | 현재 취해진 또는 계획된 행동 |
| Owner | 담당 팀/에이전트 |
| 감지일 | YYYY-MM-DD |
| 해소일 | YYYY-MM-DD 또는 — |

---

## 임계값 (자동 escalation 기준)

| 유형 | 임계값 | 대응 |
| --- | --- | --- |
| 재무 | 일일 LLM 비용 ≥ `DAILY_COST_LIMIT_USD` × 80% | `risk_escalation_note` → CEO 즉시 |
| 재무 | 30일 runway 미만 | `risk_escalation_note` → CEO 즉시 |
| 전략 | 30-day target 달성 가능성 < 50% | `risk_escalation_note` → CEO + Business Operations |
| 법적 | 미결 `legal_review_block` 존재 | 외부 발행 자동 차단, CEO 알림 |
| 기술 | HIGH 등급 보안 취약점 open 7일 초과 | `risk_escalation_note` → CEO + Red Team |
| 평판 | 사실 오류 미수정 24시간 초과 (발행 후) | `risk_escalation_note` → CEO + QA |
| KILL | `docs/governance/KILL_CRITERIA.md` 트리거 감지 | CEO 즉시 + Business Operations 동시 통보 |

---

## 현재 리스크 레지스터

> 최초 등록: 2026-05-19. BRM Team 신설 시점 기준 초기 식별 리스크.

| ID | 유형 | 설명 | 확률 | 영향 | 상태 | 완화 조치 | Owner | 감지일 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIN-001 | 재무 | Anthropic API 비용 예산 초과 (고강도 multi-LLM 사용 시) | medium | high | open | `DAILY_COST_LIMIT_USD` budget gate, Tier 2 local model 우선 사용 | Business Operations | 2026-05-19 |
| OPS-001 | 운영 | Mac Mini 단독 프로덕션 — 하드웨어 장애 시 전체 파이프라인 중단 | low | critical | open | MBP fallback 가능, launchd 자동 재시작 설정 | Codex | 2026-05-19 |
| OPS-002 | 운영 | Slack Socket Mode 의존 — Slack API 장애 시 CEO 승인 채널 단절 | low | high | open | OpenClaw 대체 승인 경로 존재 | Codex | 2026-05-19 |
| STR-001 | 전략 | 30일 내 paid subscriber 0명 — 사업 모델 재검토 트리거 | medium | high | open | 무료 구독자 50명 우선 확보, paid tier 노출 1회 이상 | Business Operations | 2026-05-19 |
| STR-002 | 전략 | 콘텐츠 발행 cadence 미달 (주 1회 미만) — 구독자 이탈 가속 | low | high | open | 자동화 파이프라인 안정화, VP review SLA 설정 | Chief of Staff | 2026-05-19 |
| LEG-001 | 법적·규제 | `legal_review_approve` 누락 시 외부 발행 진행 위험 | low | critical | mitigating | PREREQUISITE_GATES DB 강제 검증 구현 완료 (2026-05-19) | Legal Counsel | 2026-05-19 |
| REP-001 | 평판 | LLM 생성 사실 오류가 paid 콘텐츠에 포함되어 구독 취소 급증 | medium | high | mitigating | QA Agent `qa_clear` gate 필수화, Red Team cross-LLM 검증 | QA Team | 2026-05-19 |
| TECH-001 | 기술 | LLM 벤더 단일 의존 (Anthropic) — 서비스 중단/가격 급등 | low | high | open | Ollama local model Tier 2 운영, 다중 LLM 아키텍처 유지 | Codex | 2026-05-19 |
| TECH-002 | 기술 | Prompt injection 잔존 위험 — C-1~C-5 수정 완료, 신규 입력 경로 감시 필요 | low | high | mitigating | XML 캡슐화, SSRF 차단, script path boundary 완료 (commit `182635d`) | Red Team | 2026-05-19 |

---

## 해소된 리스크

| ID | 유형 | 설명 | 해소일 | 해소 방법 |
| --- | --- | --- | --- | --- |
| TECH-003 | 기술 | Auth bypass (H-1~H-4) — SLACK_CEO_USER_ID 미설정 시 뮤테이션 허용 | 2026-05-18 | fail-closed + XML 캡슐화 + SSRF guard 구현 |
| TECH-004 | 기술 | Path traversal (H-2) — PROJECT_ROOT 경계 미검사 | 2026-05-18 | `_resolve_path` boundary 강제 |
| TECH-005 | 기술 | DM fail-open (C-4) — SLACK_CEO_USER_ID 미설정 시 모든 DM 라우팅 | 2026-05-19 | `CEO_SLACK_USER_ID and user == CEO_SLACK_USER_ID` 조건 수정 |
| TECH-006 | 기술 | Compliance gate 누락 (C-5) — monetization/investment_thesis에 qa_clear 미요구 | 2026-05-19 | PREREQUISITE_GATES 업데이트 |

---

## 업데이트 이력

| 날짜 | 변경 내용 | 담당 |
| --- | --- | --- |
| 2026-05-19 | BRM Team 신설, 초기 리스크 레지스터 작성 | Claude (Sonnet 4.6) |
