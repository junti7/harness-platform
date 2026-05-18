# RED-TEAM LOG

---

## 2026-05-18

**Participating LLMs:** Claude (Sonnet 4.6), Gemini (0.42.0)  
**Verdict:** `red_team_block`  
**Scope:** `adapters/content/openclaw_agent.py`, `scripts/openclaw_codex_bridge.py`, `scripts/goal_loop.py`, Mac Mini runtime env

### 판정 근거

두 LLM 모두 `red_team_block`에 동의. 수정 전 production 배포 불가.

### 합의된 발견사항

| ID | 등급 | 항목 | Claude | Gemini |
|----|------|------|--------|--------|
| H-1 | HIGH | `SLACK_CEO_USER_ID` 미설정 → 뮤테이션 auth bypass | 발견 | 동의 (함수명 정정: `_authorize_structured_command`) |
| H-2 | HIGH | `_resolve_path` 절대경로 경계 미검사 (path traversal) | 발견 | 동의, `tool_write_file`에 `write=True` 명시 추가 |
| H-3 | HIGH | `_format_with_haiku` 날짜 미주입 → 오계산 | 발견 | 동의 |
| H-4 | HIGH | **Prompt Injection** (신규 — Gemini 발견) | 미발견 | 발견 |
| M-1 | MEDIUM | budget gate Haiku 경로 미적용 | 발견 | 동의 |
| M-2 | MEDIUM | `CAPITAL_ACTIONS_ENABLED` bridge 차단 미수행 | 발견 | 동의 |
| M-3 | MEDIUM | `correlation_id` goal_loop.py 미전파 | 발견 | 동의 (파일 경로 차이로 직접 검증 불가) |
| M-4 | MEDIUM | log rotation 미설정 | 발견 | 동의 |
| M-5 | MEDIUM-LOW | **Race condition** `_write_output` 동시 쓰기 (신규 — Gemini 발견) | 미발견 | 발견 |
| M-6 | MEDIUM | **클라이언트 Rate Limiting 부재** (신규 — Gemini 발견) | 미발견 | 발견 |

### Gemini 신규 발견사항 요약

**H-4: Prompt Injection (HIGH)**
- `_build_chat_system_prompt`, `_build_tool_system_prompt`, `_format_with_haiku`, `_classify_intent_with_haiku` 전부 user_message를 프롬프트에 직접 주입
- 악의적 입력으로 시스템 프롬프트 우회, 민감 정보 추출, 의도치 않은 tool-use 유발 가능
- 수정 방향: XML 태그로 사용자 입력 캡슐화, 시스템 프롬프트에 injection 방어 지침 추가

**M-5: Race Condition (MEDIUM-LOW)**
- `_write_output` 파일 잠금 없이 동시 쓰기 시 데이터 손상 가능
- 수정 방향: `fcntl` 또는 `filelock` 기반 파일 잠금 추가

**M-6: Rate Limiting 부재 (MEDIUM)**
- Anthropic/Slack API 클라이언트 측 rate limit 없음
- Prompt Injection + 연쇄 API 호출 시 비용 급증 위험
- 수정 방향: 인메모리 또는 Redis 기반 rate limiter 추가

### 수정 완료 항목 (2026-05-18 commit `2e522a2`)

| ID | 수정 내용 | 검증 |
|----|-----------|------|
| H-1 | `_authorized_for_high_risk` fail-closed + `_authorize_structured_command` env 미설정 차단 + Mac Mini `.env` `SLACK_CEO_USER_ID=U0B2P25NR6Y` 추가 | Mac Mini 4개 케이스 PASS |
| H-2 | `_resolve_path` `_ALLOWED_READ_ROOTS`/`_ALLOWED_WRITE_ROOTS` boundary 강제, `tool_write_file` `write=True` | SSH key / /etc/hosts 차단 PASS |
| H-3 | `_format_with_haiku` `datetime.now()` system prompt 주입 | 코드 확인 |
| H-4 | 모든 LLM 호출 user_message XML 캡슐화, SYSTEM_PROMPT/CHAT_SYSTEM_PROMPT injection 방어 지침 추가 | 코드 확인 |
| M-2 | `command_record_decision` `capital_action_approve` gate 추가 | 코드 확인 |

### 미해결 항목 (`red_team_clear` 조건)

1. M-1: budget gate Haiku 경로 적용
2. M-3: correlation_id goal_loop.py 전파 (DB migration 포함)
3. M-4: log rotation 구현
4. M-5: 파일 잠금 추가
5. M-6: Rate Limiting 구현
6. CLAUDE.md 컴플라이언스: qa_clear / pre_mortem / legal_review_approve 구현

### 다음 단계

이번 주: M-1 (budget gate)  
다음 스프린트: M-3~M-6, compliance  

재검토 시 참여 LLM: Claude + Gemini + Codex (3개 full pass 후 `red_team_clear` 가능)
