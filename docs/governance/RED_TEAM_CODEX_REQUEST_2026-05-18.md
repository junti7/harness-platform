# RED-TEAM Final Pass — Codex 검토 요청
**Date:** 2026-05-18  
**Issued by:** Claude (Sonnet 4.6)  
**Protocol status:** Claude + Gemini 완료 → Codex final pass 필요  
**Scope:** `adapters/content/openclaw_agent.py`, `scripts/openclaw_codex_bridge.py`, `scripts/goal_loop.py`, `core/approval.py`, `scripts/ceo_decision.py`

---

## 배경

Harness 플랫폼에 대한 RED-TEAM 진단을 Claude와 Gemini가 각각 수행했다.
두 LLM 모두 `red_team_block` 판정을 내렸고, 이후 H-1~H-4 + M-1~M-6 + CLAUDE.md compliance 항목이 수정되었다.

CLAUDE.md 규약: "정례 운영 기준 기본 통과 조건은 **세 모델 중 최소 2개가 approve/clear**"
Claude + Gemini 2개 완료. Codex의 독립적 final pass가 남았다.

---

## 수정된 내용 요약 (commit `2e522a2` ~ `c02c45a`)

### H-1: Auth Bypass 수정 (`adapters/content/openclaw_agent.py`)
- `_authorized_for_high_risk()`: env 미설정 시 `return False` (fail-closed)
- `_authorize_structured_command()`: `SLACK_CEO_USER_ID` 미설정 시 명시적 차단 추가
- Mac Mini `.env`에 `SLACK_CEO_USER_ID=U0B2P25NR6Y` 추가

### H-2: Path Traversal 수정 (`adapters/content/openclaw_agent.py`)
- `_ALLOWED_READ_ROOTS = [PROJECT_ROOT]`
- `_ALLOWED_WRITE_ROOTS = [PROJECT_ROOT/docs, PROJECT_ROOT/reports, PROJECT_ROOT/runtime]`
- `_resolve_path(path, write=False)`: `resolved.is_relative_to(root)` 검사, 위반 시 `PermissionError`
- `tool_write_file` → `_resolve_path(path, write=True)` 호출

### H-3: Date Injection 수정 (`adapters/content/openclaw_agent.py`)
- `_format_with_haiku()` system prompt에 `datetime.now().strftime("%Y년 %m월 %d일")` 주입

### H-4: Prompt Injection 수정 (`adapters/content/openclaw_agent.py`)
- `SYSTEM_PROMPT`, `CHAT_SYSTEM_PROMPT`에 injection 방어 지침 추가
- `_classify_intent_with_haiku()`, `_format_with_haiku()`, Ollama chat, Anthropic chat, Sonnet tool-use 경로 전부:
  `{"role": "user", "content": f"<user_message>{user_message}</user_message>"}` 로 캡슐화

### M-2: Capital Action Gate (`scripts/openclaw_codex_bridge.py`)
- `command_record_decision()`: `capital_action_approve` 시 `CAPITAL_ACTIONS_ENABLED=true` 아니면 차단

### M-3: correlation_id (`scripts/goal_loop.py`)
- `create_goal`, `set_goal_model`, `record_goal_snapshot`에 `correlation_id` 파라미터 추가
- DB migration: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS correlation_id UUID DEFAULT gen_random_uuid()`

### M-4: Log Rotation (`adapters/content/slack_listener.py`)
- `RotatingFileHandler` 10MB×5 추가, launchd plist stdout → `/dev/null`

### M-5: File Lock (`scripts/openclaw_codex_bridge.py`)
- `_write_output()`: `fcntl.LOCK_EX` 적용

### M-6: Rate Limiting (`adapters/content/openclaw_agent.py`)
- `_rate_limit_check(user_id)`: 슬라이딩 윈도우 60초/20회
- `run()` 진입부에서 호출

### CLAUDE.md Compliance (`core/approval.py`, `scripts/ceo_decision.py`)
- `PREREQUISITE_GATES`: high-impact 유형별 필수 사전 gate 맵
- `record_decision()`: `decision='approved'` 시 `_check_prerequisites()` 호출, 미충족 시 `PermissionError`
- 새 플레이북: `PRE_MORTEM_PROTOCOL.md`, `QA_PLAYBOOK.md`, `LEGAL_REVIEW_PLAYBOOK.md`

---

## Codex에게 요청하는 검토 사항

1. **H-1 재검증**: `_authorized_for_high_risk`와 `_authorize_structured_command` 수정이 실제로 auth bypass를 막는지 코드 경로 추적.
2. **H-2 재검증**: `_resolve_path`의 symlink 우회 가능성 검토 (`.resolve()`가 symlink를 따르는지, `is_relative_to()`가 충분한지).
3. **H-4 재검증**: XML 캡슐화가 모든 LLM 호출 경로를 빠짐없이 커버하는지 확인. 누락된 주입 경로가 있는지 코드 전체 grep.
4. **M-6 재검증**: rate limiter가 thread-safe한지 (`_rate_lock`, `defaultdict(deque)`) 검토.
5. **Compliance gate 재검증**: `_check_prerequisites()`가 `hold`/`rejected` 레코드를 통과시키지 않는지 (`decision = 'approved'` 필터 확인).
6. **신규 취약점 독립 스캔**: Claude와 Gemini가 놓쳤을 취약점 (SQL injection, SSRF, insecure deserialization, dependency confusion 등).
7. **최종 판정**: `red_team_clear` 또는 `red_team_block` (이유 포함).

---

## 참조 파일

- `adapters/content/openclaw_agent.py` (주 수정 파일)
- `scripts/openclaw_codex_bridge.py`
- `scripts/goal_loop.py`
- `core/approval.py`
- `scripts/ceo_decision.py`
- `CLAUDE.md` (governing rules)
- `docs/governance/RED_TEAM_LOG.md` (Claude + Gemini 결과)

---

*Codex final pass 후 판정을 `docs/governance/RED_TEAM_LOG.md`에 날짜, 모델명, 미해결 항목과 함께 기록해 주세요.*
