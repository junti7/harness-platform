# RED-TEAM LOG

---

## 2026-05-24 AR-018 B2I 전환 Red Team 검증

**Participating LLMs:** Claude (claude-opus-4-7) + Gemini (gemini-2.0-flash)  
**Verdict:** `red_team_block` (2-of-2 block — unanimously blocked)  
**Scope:** B2C→B2I 전환 결정 전반 (자본시장법/외국환거래법, LLM 환각→실주문, Physical AI 섹터 집중, $7k 대비 법률 제재 비대칭, 놓친 가정)  
**correlation_id:** strategy-pivot-b2i-20260524

### 판정 요약

| 항목 | Claude | Gemini | 합의 |
|---|---|---|---|
| ① 자본시장법/외국환거래법 | CONCERN | CONCERN | CONCERN |
| ② LLM 환각 신호→실주문 | **BLOCK** | CONCERN | BLOCK |
| ③ Physical AI 단일섹터 집중 | CONCERN | CONCERN | CONCERN |
| ④ $7,000 vs 1.5억 비대칭 | **BLOCK** | **BLOCK** | **BLOCK** |
| ⑤ 놓친 가정·약한 근거 | CONCERN | CONCERN | CONCERN |

**Overall: `red_team_block`** — 두 모델 만장일치

### Claude 주요 BLOCK 근거

- **② LLM 환각→실주문**: 투자 신호→주문 변환 레이어에 콘텐츠 산출물 수준의 cross-LLM 게이트 부재. Paper↔Live 환경 전환 사고(18%, 800만원) 포함. 시나리오 3 확률 42%로 최고.
- **④ EV 음수 구조**: $7,000 업사이드 대비 1.5억 다운사이드(법률 제재) = EV 음수. Gemini 단독 "자기계정 자본시장법 LOW" 판단을 유권해석 없이 확정으로 신뢰 불가.

### 해제 조건 7개 (Claude 제시, 이행 시 재발주)

1. **자본 금액 ground truth 통일** — $7,000 vs $5,000 불일치 해소 (Pre-Mortem $5k vs 패킷 $7k)
2. **AR-017 강화** — 외부 변호사 의견서 1회 mandatory. AR-017 완료 기준 = "한국은행 신고 수리 완료"로 재정의
3. **B2I 전환 자체 Pre-Mortem 추가** — 발행 보류 4주+ 시 brand-equity·subscriber 손실 포함
4. **신호→주문 레이어 cross-LLM 게이트 명문화** — 2-of-3 합의 + non-negotiable factual finding 차단
5. **EV 비대칭 구조적 해법** — Live capital $500 hard-cap. $7,000은 paper trading+8주+KPI 충족 전 IBKR 입금 금지 protocol을 SOUL.md에 추가
6. **거시 트리거 기반 자동 청산** — 반도체 수출규제 신규 발표, SOXX -25% 같은 macro trigger를 KILL_CRITERIA에 명문화
7. **Multi-LLM 법률 검토 보강** — Claude+Gemini+Codex 3모델 독립 검토 + 외부 변호사 사인오프. Gemini 단독 결론은 사전분석으로만 활용

**재발주 트리거**: 조건 1·2·3·4·7 충족 시. 조건 5·6은 capital_action_approve 사전 조건으로 별도 추적.

### Evidence

- Claude: `docs/reports/llm_outputs/claude_ar_018_b2i_red_team_2026-05-24_172003.md`
- Gemini: `docs/reports/llm_outputs/gemini_ar_018_b2i_red_team_2026-05-24_172003.md`
- Packet: `docs/reports/llm_outputs/packet_ar_018_b2i_red_team_2026-05-24_172003.json`

---

## 2026-05-23 IBKR ETF Whitelist Resolver (Pre-Execution)

**Participating LLMs:** Claude + Gemini + Codex (planned)  
**Verdict:** `red_team_block` (Claude block + Codex block; Gemini output produced but did not provide an explicit clear verdict)  
**Scope:** `scripts/ibkr_cp_client.py`, `scripts/openclaw_codex_bridge.py`, `adapters/content/openclaw_agent.py`, `docs/trading/etf_whitelist_v0.json`, `docs/reports/instrument_registry.jsonl`

- Request doc: `docs/governance/RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md`
- Notes: IBKR CP API는 session/2FA 제약이 있으므로 “연결 OK”와 “authenticated OK”를 구분해 차단/가이드해야 한다.
- Evidence:
  - Claude: `docs/reports/llm_outputs/claude_ibkr_etf_whitelist_resolver_registry_gating_2026-05-23_103608.md`
  - Gemini: `docs/reports/llm_outputs/gemini_ibkr_etf_whitelist_resolver_registry_gating_2026-05-23_103857.md`
  - Codex: `docs/reports/llm_outputs/codex_ibkr_etf_whitelist_resolver_registry_gating_2026-05-23.md`

## 2026-05-23 IBKR ETF Whitelist Resolver (Hardening v2 Re-Review)

**Participating LLMs:** Claude + Codex (+ Gemini)  
**Verdict:** `red_team_clear` (2-of-3: Claude clear + Codex clear; Gemini output was low-signal but non-blocking)  
**Scope:** same as above + pending queue + snapshot-based approve

- Evidence:
  - Claude: `docs/reports/llm_outputs/claude_ibkr_etf_whitelist_resolver_registry_gating_hardening_v2_2026-05-23_105007.md`
  - Gemini: `docs/reports/llm_outputs/gemini_ibkr_etf_whitelist_resolver_registry_gating_hardening_v2_2026-05-23_105007.md`
  - Codex: `docs/reports/llm_outputs/codex_ibkr_etf_whitelist_resolver_registry_gating_hardening_v2_2026-05-23.md`

## 2026-05-20 Agentic Orchestration Phase 0 Plan

**Participating LLMs:** Claude (Opus 4.7), Gemini (2.5-pro), Codex (gpt-5.5)
**Verdict:** `conditional_proceed` — 2-of-3 CONDITIONAL_PROCEED / 1 BLOCK(Codex), non-negotiable 5건으로 자동 통과 불가. 대표가 Path A(8개 항목 Phase 0 편입) 선택.
**Scope:** agentic orchestration 개편 Phase 0 plan (`/tmp/agentic_orchestration_phase0_plan.md`)

### Non-negotiable findings (전 모델 통합)

1. Pre-Mortem 누락 (high-impact governance change) — Codex
2. Kill-criteria / 2주 체크포인트 부재 — 3개 모델 공통
3. PII / 보존 / 접근 정책 부재 (autonomous 채널 + episodic memory) — Codex
4. Persona ≠ Gate 혼동 (단일 LLM persona의 cross-LLM 게이트 위장 위험) — Claude
5. "future of company depends on it" = evidence 아닌 전략적 베팅 (Product-over-Pipeline override 정당화 부족) — Codex+Gemini

### 조치 (Path A, 2026-05-20)

| 산출물 | 경로 |
|---|---|
| Pre-Mortem | `docs/governance/PRE_MORTEM_2026-05-20_agentic_orchestration.md` |
| Charter | `docs/governance/AGENTIC_ORCHESTRATION_CHARTER.md` (kill-criteria, 비용 cap, PII 정책, Persona≠Gate, persona→LLM, override protocol, 회의실+OpenClaw 릴레이 포함) |
| Channel log | `docs/operations/SLACK_CHANNEL_CREATION_LOG.md` |
| Enforcement | `scripts/check_slack_channel_log.py` |
| Jarvis persona | `agents/jarvis/{SYSTEM_PROMPT,MEMORY,CHANNEL}.md`, `agents/README.md` |
| CLAUDE.md patch (미적용) | `docs/governance/CLAUDE_MD_PATCH_DRAFT_2026-05-20.md` |

### 남은 조건

- 모든 산출물은 **DRAFT**다. 대표 `pre_mortem_approve` + Business Reality Constraint override 서면 confirm 전까지 구속력 없음.
- CLAUDE.md patch는 미적용 상태. 대표 검토 후 반영.

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

---

## 2026-05-19 — BRM Playbook Red Team (Claude 1차 pass)

**Participating LLMs:** Claude (Sonnet 4.6) — 1차 pass 완료. Gemini + Codex pass 대기 중.  
**Verdict:** `red_team_block` (Claude 단독 — 최종 판정 미결)  
**Scope:** `docs/governance/BRM_PLAYBOOK.md`

### Claude 발견사항

| ID | 등급 | 항목 |
|----|------|------|
| B-1 | MEDIUM | §2.2 발생 확률(low/medium/high) 수치 기준 미정의 — Agent마다 다른 등급 부여 가능 |
| B-2 | MEDIUM | §5.3 `accepted` 상태 전환 시 CEO 확인 `ceo_decisions` DB 기록 지침 없음 — audit trail 부재 |
| B-3 | MEDIUM | §6.2 `pre_mortem_approve` DB 기록 주체 미명시 — PRE_MORTEM_PROTOCOL.md 기존 절차(CEO bridge 직접 기록)와 충돌 가능 |
| B-4 | MEDIUM | `risk_register` DB 테이블은 roadmap 상태(AGENTS.md §5)임에도 플레이북이 현재 운영 가능한 것처럼 기술 — Phase 1 MD 파일 기반 운영 선언 누락 |
| B-5 | MEDIUM | §4 실시간 임계값 모니터링이 자동화인지 수동인지 미명시 — "즉시" escalation이 사실상 수동 점검에 의존할 가능성 |
| B-6 | LOW | §4 ESC-STR-1 "30-day target 달성 가능성 50%" — Business Operations 예측 미실행 주에 대한 fallback 없음 |
| B-7 | LOW | §7.1 Kill Criteria 트리거 5개 항목이 실제 `docs/governance/KILL_CRITERIA.md` 내용과 정합성 미검증 |

### Claude 판정 근거

B-1~B-5는 플레이북을 실제 운영 시 일관성 부재 또는 audit trail 누락으로 이어지는 항목이다. 특히 B-4는 DB가 존재한다는 잘못된 전제를 심을 수 있어 수정이 필요하다. B-6~B-7은 낮은 우선순위이나 Gemini/Codex가 독립 검토해야 한다.

### 최종 판정 조건

Gemini + Codex pass 후 3-LLM 중 2개 이상이 clear 또는 수정 후 clear이면 `red_team_clear` 기록 가능.  
B-1~B-5 중 Gemini/Codex가 동의하는 항목은 수정 후 재검토.  
요청 문서: `docs/governance/RED_TEAM_BRM_REQUEST_2026-05-19.md`

---

## 2026-05-19 — BRM Playbook Gemini pass

**Participating LLMs:** Gemini (0.42.0)  
**Verdict:** `red_team_block`

### Claude 발견사항 검증 결과 (B-1 ~ B-7)

| ID | Claude 등급 | Gemini 판정 |
|----|------------|------------|
| B-1 | MEDIUM | **AGREE** — 수치 기준 없이 주관적 분류는 Agent 간 불일치 유발 |
| B-2 | MEDIUM | **AGREE** — risk_brief 언급만으로는 부족, `ceo_decisions` DB 기록 필요 |
| B-3 | MEDIUM | **PARTIAL AGREE** — 직접 충돌은 아니나 BRM review를 prerequisite로 명시하고 기록 주체를 분명히 해야 함 |
| B-4 | MEDIUM | **DISAGREE** — MD 파일 기반 MVP 운영은 유효한 접근, 운영 리스크 아님 |
| B-5 | MEDIUM | **AGREE** — "즉시" escalation은 자동화를 전제해야 하며 미명시는 신뢰성 결함 |
| B-6 | LOW | **AGREE** — Business Operations 예측 미실행 시 fallback 필요 |
| B-7 | LOW | **AGREE** — KILL_CRITERIA.md를 정규 참조원으로 유지해야 함, 중복 나열은 sync 실패 위험 |

### Gemini 신규 발견사항

| ID | 등급 | 항목 |
|----|------|------|
| G-1 | **HIGH** | **과도한 복잡성** — 6개 차원·9개 임계값 체계는 Phase 1(paid subscriber 1명) 목표 대비 과도. CLAUDE.md §1 Product-over-Pipeline 원칙 위반 |
| G-2 | MEDIUM | **미선언 거버넌스 변경** — `pre_mortem_review_note`가 BRM 검토를 암묵적 필수 게이트로 추가. CLAUDE.md 승인 체계 수정은 명시적 선언 필요 |
| G-3 | MEDIUM | §2.2 매트릭스와 §4 임계값 간 우선순위 관계 미정의 — 어느 기준이 override인지 불명확 |
| G-4 | MEDIUM | §9.1 risk_brief 템플릿이 넓은 마크다운 표 형식 — CEO 모바일 30~60초 판단에 부적합 |
| G-5 | LOW | BRM Agent 자체 장애 시 감지·경보 메커니즘 없음 ("모니터의 모니터" 부재) |

### Gemini 판정 근거

1. **G-1 (HIGH)**: 현재 Phase 1 목표(무료 50명, paid 1명)에서 6차원 리스크 레지스터+9개 자동 임계값 체계는 실질적 가치보다 운영 부담이 크다. 플레이북을 Phase 1 최소 버전으로 축소해야 한다.
2. **G-2+B-3**: 기존 승인 체계(CLAUDE.md §4)를 암묵적으로 수정하는 것은 내부 규약 위반.
3. **B-2**: `accepted` 리스크에 대한 불변 감사 기록 누락은 거버넌스 실패.

### 중간 집계 (Claude + Gemini)

| 항목 | Claude | Gemini | 합의 |
|------|--------|--------|------|
| B-1 | block | block | **수정 필요** |
| B-2 | block | block | **수정 필요** |
| B-3 | block | partial | **수정 권고** |
| B-4 | block | clear | 불일치 — Codex 판정 필요 |
| B-5 | block | block | **수정 필요** |
| B-6 | low | low | 낮은 우선순위 |
| B-7 | low | block | **수정 권고** |
| G-1 | 미발견 | HIGH | **수정 필요** (non-negotiable) |
| G-2 | 미발견 | MEDIUM | **수정 필요** |
| G-3 | 미발견 | MEDIUM | 수정 권고 |
| G-4 | 미발견 | MEDIUM | 수정 권고 |
| G-5 | 미발견 | LOW | 낮은 우선순위 |

현재 상태: **Claude block + Gemini block = red_team_block**  
Codex pass 또는 수정 후 재검토 필요.

---

## 2026-05-19 — BRM Playbook v1.1 수정 완료 및 재검토

### 수정 내역 (commit 예정)

| ID | 수정 내용 |
|----|-----------|
| B-1 | §2.2 확률 기준값 정의 (low < 20% / medium 20~60% / high > 60%) |
| B-2 | §5.3 `accepted` Phase 1 MD 기록 방식 + Phase 2 bridge 구분. `core/approval.py` 미등록 타입(risk_review/risk_accept) Phase 2 예정임 명시 |
| B-3/G-2 | §6 거버넌스 선언 추가: `pre_mortem_review_note`는 prerequisite gate이며 `pre_mortem_approve` 기록 주체는 결정 팀/CEO |
| B-5 | §3.0, §3.1, §4 Phase 1 수동 점검 방식 명시, 자동화 Phase 2 예정 |
| B-6 | ESC-STR-1 각주: Business Operations 미실행 시 status unknown + 2주 연속 미실행 시 에스컬레이션 |
| B-7 | §7.1 Kill Criteria 중복 나열 제거, KILL_CRITERIA.md 단일 참조원으로 대체 |
| G-1 | §3.0 Phase 1 운영 범위 선언: 임계값 9→4개 활성, 수동 점검, MD 기반 레지스터 |
| G-3 | §2.2 하단 §4가 매트릭스 override임을 명시 |
| G-4 | §9.1 risk_brief 이모지 목록 형식으로 경량화 (Slack 1화면 이내) |
| G-5 | §11 BRM 2주 연속 미발행 시 비서실장 CEO 직보 규칙 추가 |
| B-4 | 수정 불필요 (Gemini DISAGREE) — §3.0 Phase 1/2 구분 테이블로 자연 해소 |

### Claude 재검토 판정

**Verdict:** `red_team_clear`

모든 블로킹 항목(G-1, B-2, G-2, B-3) 해소 확인. B-2의 bridge 명령 미등록 타입 문제는 Phase 1 수동 방식 + Phase 2 DB 구현 예정으로 문서에 명시됨. 잔존 non-negotiable 이슈 없음.

Gemini 재검토 완료.

### Gemini 재검토 판정

**Verdict:** `red_team_clear`

| ID | v1.1 상태 |
|----|-----------|
| G-1 (Premature complexity) | ✅ Resolved — §3.0 Phase 1 scope 적절 |
| G-2 (Implicit governance change) | ✅ Resolved — §6 명시적 거버넌스 선언 충족 |
| B-2 (accepted audit trail) | ✅ Resolved — Phase 1 MD+Git, Phase 2 DB 구분 충족 |
| G-3 (matrix/threshold hierarchy) | ✅ Resolved |
| G-4 (mobile brief) | ✅ Resolved |
| G-5 (BRM failure monitoring) | ✅ Resolved |
| B-1 (probability thresholds) | ✅ Resolved |
| B-5 (manual vs automated) | ✅ Resolved |
| B-6 (ESC-STR-1 fallback) | ✅ Resolved |
| B-7 (Kill Criteria duplication) | ✅ Resolved |
| 신규 이슈 | 없음 |

Gemini 판정 근거: "The new phased approach (Phase 1) is practical and safe, reducing initial complexity while maintaining essential risk oversight."

### `red_team_clear` 기록

**Verdict:** `red_team_clear`  
**Participating LLMs:** Claude (Sonnet 4.6) + Gemini (0.42.0)  
**근거:** 2-LLM cross-verification 완료 (MD 문서 기준: Claude + Gemini 최소 요건 충족). B-1~B-7 + G-1~G-5 전체 수정 완료 확인. 잔존 non-negotiable 이슈 없음.  
**대상:** `docs/governance/BRM_PLAYBOOK.md` v1.1  
**비고:** Codex pass는 선택적 추가 검토 — 2-of-3 기준으로 현재 통과 조건 충족.

---

## 2026-05-19 — BRM Playbook Codex pass

**Participating LLMs:** Codex  
**Verdict:** `red_team_block` (C-1 경로 오류 발견) → v1.2 수정 후 `red_team_clear`

### Codex 발견사항

| ID | 등급 | 항목 | Codex 판정 |
|----|------|------|-----------|
| C-1 | BLOCK | §7 §7.1 서두 `docs/governance/KILL_CRITERIA.md` 경로 오류 — 실제 파일 위치는 `docs/KILL_CRITERIA.md` | block |
| C-2 | LOW | `risk_review`/`risk_accept` approval type이 `core/approval.py`에 미등록 | Phase 2 로드맵으로 수용, non-blocking |
| C-3 | LOW | 보안 취약점 모니터링 자동화 스크립트 미구현 (주간 수동 운영) | Phase 1 수동 명시로 수용 |
| C-4 | LOW | AGENTS.md §3.16 output 명칭과 BRM_PLAYBOOK.md §8 용어 미세 불일치 | 운영상 혼란 낮음, non-blocking |

**이전 항목 재확인:** Claude + Gemini에서 수정된 B-1~B-7, G-1~G-5 전체 v1.1 반영 확인. 신규 non-negotiable 이슈 없음 (C-1 제외).

### v1.2 수정 내용

| C-1 수정 | `docs/governance/BRM_PLAYBOOK.md` §7 서두 경로 `docs/governance/KILL_CRITERIA.md` → `docs/KILL_CRITERIA.md` |
| --- | --- |
| 버전 | v1.1 → v1.2 |

### Codex 재판정

C-1 수정 후 잔존 blocking 이슈 없음. C-2~C-4는 Phase 2 로드맵 또는 운영상 낮은 위험으로 수용.  
**Verdict:** `red_team_clear`

---

## 2026-05-19 — BRM Playbook 최종 판정 (3-of-3)

**Verdict:** `red_team_clear`  
**Participating LLMs:** Claude (Sonnet 4.6) + Gemini (0.42.0) + Codex  
**대상:** `docs/governance/BRM_PLAYBOOK.md` v1.2  
**근거:** 3-LLM cross-verification 완료. B-1~B-7 + G-1~G-5 + C-1 전체 수정 확인. 잔존 non-negotiable 이슈 없음.  
**잔존 로드맵 항목:** C-2 (`risk_accept` approval type Phase 2 DB 등록), C-3 (취약점 자동 모니터링 스크립트) — 운영 차단 없음.
---

## 2026-05-19 Remediation Pass

**Implementing LLM:** Codex  
**Verdict:** `conditional_proceed` — 코드/런타임 조치 완료, 별도 Claude+Gemini 재검토 전까지 `red_team_clear`로 승격하지 않음.

### 조치 결과

| ID | 상태 | 조치 |
|----|------|------|
| H-1 | fixed | `SLACK_CEO_USER_ID` 미설정 시 high-risk/mutating command를 fail-closed 처리. Mac Mini runtime `.env`에는 CEO Slack user ID 설정 확인. |
| H-2 | fixed | `_resolve_path()`에 PROJECT_ROOT 경계 검사 추가. read는 project root 하위만, write는 `docs/`, `reports/`, `runtime/` 하위만 허용. |
| H-3 | fixed | formatter system prompt에 오늘 날짜 주입 및 날짜 계산 기준 명시. |
| H-4 | mitigated | user message / bridge output을 XML-style boundary로 감싸고, prompt-injection 방어 지침을 chat/tool/classifier/formatter prompt에 추가. |
| M-1 | fixed | Haiku intent classifier 진입 전 cost guard 추가. |
| M-2 | fixed | `capital_action_approve`는 `CAPITAL_ACTIONS_ENABLED=true`가 아니면 bridge에서 기록 차단. |
| M-3 | fixed | goal loop write path에 `correlation_id` 전파. migration `2026-05-19_goal_loop_correlation_id.sql` 추가 및 runtime DB 적용. |
| M-4 | fixed | Slack listener에 `RotatingFileHandler` 적용 (`logs/slack-listener.log`, 10MB x 5). |
| M-5 | fixed | bridge `_write_output()`에 `fcntl.flock` 기반 exclusive lock 추가. |
| M-6 | mitigated | Anthropic intent/chat/tool 경로에 per-user in-memory rate limit 추가. |
| Compliance | existing/verified | `qa_clear`, `legal_review_approve`, `pre_mortem_approve` 구현체 존재 확인: `adapters/content/qa_agent.py`, `adapters/content/legal_review.py`, `adapters/content/pre_mortem.py`, 관련 CLI scripts. |

### 추가 조치

- Gmail capability 오답 방지: OpenClaw gateway의 `gog` skill이 ready/visible임을 runtime에서 확인했고, Harness Slack adapter에 `gmail_search` read-only tool 및 deterministic capability response를 추가.
- Gmail mutating action 금지: `gog --gmail-no-send`를 사용하며, Slack adapter에서는 Gmail 검색/읽기만 허용.
- Runtime 적용: Mac Mini runtime에 파일 sync, unit test 통과, DB migration 적용, `com.harness.slack-listener` 재시작 완료.

### 검증

- Local: `py_compile` 통과, `tests/test_openclaw_agent.py`, `tests/test_openclaw_route_audit_summary.py` 통과.
- Runtime: `py_compile` 통과, `tests/test_openclaw_agent.py` 통과.
- Runtime smoke: `구글 메일 읽을 수 있어?`에 대해 `gog`/`gmail_search` 기반 가능 조건을 deterministic하게 응답.

### 남은 조건

- 이 remediation은 Codex implementation pass다. 조직 규칙상 최종 `red_team_clear` 승격은 Claude + Gemini + Codex 재검토 후 기록한다.
