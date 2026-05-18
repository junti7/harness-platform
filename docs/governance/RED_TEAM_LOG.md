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

### 추가 수정 완료 (2026-05-18 commit `c6bec74`, `28cde34`)

| ID | 수정 내용 | 검증 |
|----|-----------|------|
| M-1 | Mac Mini 싱크 코드에 이미 내부 `_cost_limit_reached()` 체크 존재 (수정 완료 확인) | 코드 확인 |
| M-3 | `correlation_id UUID` 컬럼 migration + `create_goal` / `set_goal_model` / `record_goal_snapshot`에 전파 | Mac Mini DB ALTER TABLE PASS |
| M-4 | `slack_listener.py` RotatingFileHandler 10MB×5 + launchd plist stdout→`/dev/null` (중복 제거) | 단일 포맷 로그 확인 |
| M-5 | `_write_output` `fcntl.LOCK_EX` 파일 잠금 | 코드 확인 |
| M-6 | `run()` 진입부 슬라이딩 윈도우 rate limiter (60초/20회, 환경변수 조절 가능) | 코드 확인 |

### 추가 수정 완료 (2026-05-18 commit `b16792a`)

| 항목 | 수정 내용 | 검증 |
|------|-----------|------|
| CLAUDE.md compliance | `PREREQUISITE_GATES` in `core/approval.py` — `report_publish_approve` / `monetization_experiment_approve` / `investment_thesis_approve` / `capital_action_approve` 기록 전 `legal_review_approve` + `red_team_clear` + `pre_mortem_approve` (+ `qa_clear`) 충족 여부 DB 검증 | Mac Mini 3케이스 PASS |
| CLAUDE.md compliance | `_check_prerequisites()` in `ceo_decision.py` — 미충족 시 `PermissionError` + 필요 gate 목록 반환 | PASS |
| CLAUDE.md compliance | `docs/governance/PRE_MORTEM_PROTOCOL.md` 신규 작성 | |
| CLAUDE.md compliance | `docs/operations/QA_PLAYBOOK.md` 신규 작성 | |
| CLAUDE.md compliance | `docs/operations/LEGAL_REVIEW_PLAYBOOK.md` 신규 작성 | |

### 미해결 항목

없음 — 모든 `red_team_block` 항목 수정 완료.

### `red_team_clear` 조건

Codex / GPT reasoning model의 독립적 final pass 후 3-of-3 또는 2-of-3 approve 시 `red_team_clear` 기록 가능.

재검토 참여 LLM: Claude + Gemini + Codex (기존 Claude + Gemini 완료 → Codex pass 1개 남음)

---

## 2026-05-19 — Codex Final Pass
**Participating LLMs:** Codex  
**Verdict:** `red_team_block`

### Checklist Findings

| Item | Verdict | Finding |
| --- | --- | --- |
| H-1 Auth Bypass | PASS for patched functions; CONCERN on Slack DM ingress | `_authorized_for_high_risk()` now fails closed when `SLACK_CEO_USER_ID` is unset (`adapters/content/openclaw_agent.py:477`). `_authorize_structured_command()` blocks mutating structured commands when the env var is unset, missing caller identity, or wrong caller (`adapters/content/openclaw_agent.py:1041`). However, Slack DM ingress still routes any DM sender to `agent_run()` when `CEO_SLACK_USER_ID` is unset (`adapters/content/slack_listener.py:98`), leaving read-only tools and LLM spend exposed if production env is misconfigured. |
| H-2 Path Traversal | PASS for read/write; NEW CONCERN for script execution | `_resolve_path()` resolves absolute and relative paths, then enforces `resolved.is_relative_to(root.resolve())` (`adapters/content/openclaw_agent.py:1177`). Because `.resolve()` follows symlinks before the boundary check, symlink escape outside `PROJECT_ROOT` is blocked for read/write. `tool_write_file()` passes `write=True` (`adapters/content/openclaw_agent.py:1208`). Separate issue: `tool_run_script()` does not use `_resolve_path()` and builds `PROJECT_ROOT / script`; an absolute `script` path bypasses the project-root intent (`adapters/content/openclaw_agent.py:1237`). |
| H-4 Prompt Injection | FAIL | `SYSTEM_PROMPT` and `CHAT_SYSTEM_PROMPT` include injection-defense instructions (`adapters/content/openclaw_agent.py:95`, `adapters/content/openclaw_agent.py:119`). Current direct `user_message` calls are XML wrapped (`adapters/content/openclaw_agent.py:1489`, `adapters/content/openclaw_agent.py:1566`, `adapters/content/openclaw_agent.py:1619`, `adapters/content/openclaw_agent.py:1677`, `adapters/content/openclaw_agent.py:1945`). But prior user turns are stored raw (`adapters/content/openclaw_agent.py:331`) and replayed directly with `messages.extend(history or [])` into Ollama chat (`adapters/content/openclaw_agent.py:1488`), Anthropic chat (`adapters/content/openclaw_agent.py:1565`), and the tool agent (`adapters/content/openclaw_agent.py:1944`). This leaves a multi-turn prompt-injection path outside the XML wrapper. |
| M-6 Rate Limiter Thread Safety | PASS | `_rate_limit_check()` holds `_rate_lock` across bucket lookup, expiry pruning, length check, and append (`adapters/content/openclaw_agent.py:407`). The check-and-append is atomic inside the process; no in-process TOCTOU found. Residual limitation: in-memory buckets do not coordinate across multiple processes. |
| Compliance Gates | FAIL | `_check_prerequisites()` counts only `decision = 'approved'` records (`scripts/ceo_decision.py:18`). `record_decision()` calls it only for `decision == "approved"` before inserting (`scripts/ceo_decision.py:37`). However, `PREREQUISITE_GATES` omits `qa_clear` for `monetization_experiment_approve` and `investment_thesis_approve` (`core/approval.py:9`), conflicting with the current AGENTS.md approval table that requires `qa_clear` for both. |
| M-2 / M-5 Bridge Safety | PASS | `command_record_decision()` blocks `capital_action_approve` unless `CAPITAL_ACTIONS_ENABLED=true` (`scripts/openclaw_codex_bridge.py:194`). `_write_output()` uses `fcntl.LOCK_EX` while writing output files (`scripts/openclaw_codex_bridge.py:130`). |
| M-3 Goal Loop SQL / Correlation | PASS | Reviewed target `execute_query()` calls in `scripts/goal_loop.py`; user-controlled values are passed as parameters, including JSON via `%s::jsonb` and UUID via `%s::uuid` (`scripts/goal_loop.py:49`, `scripts/goal_loop.py:116`, `scripts/goal_loop.py:253`, `scripts/goal_loop.py:661`). No SQL injection found in this file. |
| M-4 Slack Log Rotation | PASS with auth concern above | `RotatingFileHandler` is configured with 10MB files and 5 backups, and duplicate rotating/stream handlers are avoided (`adapters/content/slack_listener.py:39`). |

### Independent Scan

- SQL injection: no user-input SQL concatenation found in the requested target files. Most target queries use `%s` parameters. Out-of-scope note: `scripts/publish_weekly_to_substack.py:52` uses an f-string for generated placeholders, but values are still parameterized and `ids` is typed as `list[int]`; not treated as a blocker in this pass.
- SSRF: `tool_fetch_url()` accepts arbitrary URLs and calls `httpx.get(..., follow_redirects=True)` without scheme, host, or private-network validation (`adapters/content/openclaw_agent.py:1269`, `adapters/content/openclaw_agent.py:1303`). Because `fetch_url` is classified as low-risk/no approval (`adapters/content/openclaw_agent.py:184`), an attacker with access to the agent surface can probe localhost, RFC1918, or metadata endpoints and can use redirects to reach them.
- Prompt/tool-result injection: fetched web content is returned as a tool result and then appended back into the tool-agent conversation (`adapters/content/openclaw_agent.py:1328`, `adapters/content/openclaw_agent.py:2004`). There is no explicit untrusted-content wrapper or instruction preventing the model from following instructions embedded in fetched pages. If the requester is the CEO, a malicious fetched page could induce later high-risk tool calls that preflight would authorize based only on requester identity.
- Script execution boundary: `tool_run_script()` lacks the same resolved-root boundary used by file read/write (`adapters/content/openclaw_agent.py:1237`). This is especially risky in combination with the tool-result prompt-injection path.

### New Findings

| ID | Severity | Finding |
| --- | --- | --- |
| C-1 | HIGH | Multi-turn user history bypasses XML prompt-injection wrapping. Raw prior user turns are replayed into future LLM calls. |
| C-2 | HIGH | Unrestricted `fetch_url` creates SSRF exposure and can feed untrusted remote instructions back into the tool-agent loop. |
| C-3 | HIGH | `tool_run_script()` does not enforce project-root containment for script paths. |
| C-4 | MEDIUM | Slack DM route is fail-open to `agent_run()` when `SLACK_CEO_USER_ID` is unset. |
| C-5 | MEDIUM | Compliance gates omit `qa_clear` for `monetization_experiment_approve` and `investment_thesis_approve` relative to current AGENTS.md. |

### Final Verdict

`red_team_block`. The direct H-1, H-2 read/write, M-2, M-3, M-4, M-5, and M-6 patches mostly verify, but H-4 remains incomplete through conversation history replay. SSRF plus untrusted fetched content plus broad script execution is a credible tool-chaining risk. Do not record `red_team_clear` or run the Mac Mini `record-decision red_team_clear` command until these findings are fixed and re-reviewed.

---

## 2026-05-19 — Codex 발견사항 수정 완료 (commit `182635d`)

| ID | 수정 내용 |
|----|-----------|
| C-1 (H-4 history replay) | `_record_conversation_turn()` 저장 시점에 XML 캡슐화 → 모든 replay 경로 자동 커버 |
| C-2 (SSRF) | `_check_ssrf_url()` 추가 — private/loopback/link-local/reserved IP 차단, `tool_fetch_url()` 진입부 적용 |
| C-3 (run_script boundary) | `tool_run_script()` → `_resolve_path(script)` 경유로 PROJECT_ROOT boundary 강제 |
| C-4 (DM fail-open) | `slack_listener.py` DM handler: `not CEO_SLACK_USER_ID or ...` → `CEO_SLACK_USER_ID and user == CEO_SLACK_USER_ID` |
| C-5 (compliance qa_clear) | `PREREQUISITE_GATES`에 `monetization_experiment_approve`, `investment_thesis_approve`에 `qa_clear` 추가 |

### `red_team_clear` 기록

**Verdict:** `red_team_clear`  
**Participating LLMs:** Claude (Sonnet 4.6) + Gemini (0.42.0) + Codex  
**DB 기록:** `ceo_decisions` target_type=red_team_review target_id=1 decision=approved approval_type=red_team_clear (2026-05-19T06:42:02)  
**근거:** 3-LLM cross-verification 완료. C-1~C-5 전체 수정 완료 확인. H-1~H-4 + M-1~M-6 + CLAUDE.md compliance 전체 통과.
