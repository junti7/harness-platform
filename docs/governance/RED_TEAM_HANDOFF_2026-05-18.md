# RED-TEAM Hand-off — harness-platform
**Date:** 2026-05-18  
**Issued by:** Claude (Sonnet 4.6) — single-LLM pass  
**Protocol status:** `red_team_block` — cross-LLM verification (Gemini / Codex) required before `red_team_clear`  
**Scope:** `adapters/content/openclaw_agent.py`, `scripts/goal_loop.py`, `scripts/openclaw_codex_bridge.py`, Mac Mini runtime env

---

## 지시사항 (수신 LLM에게)

아래 발견된 취약점과 컴플라이언스 갭을 독립적으로 검토하고, 각 항목에 대해:
1. Claude의 진단에 동의/반박 여부와 근거를 명시하라.
2. 동의하는 항목은 수정 방법을 코드 수준으로 제안하라.
3. Claude가 놓쳤다고 판단되는 추가 취약점이 있으면 새 항목으로 추가하라.
4. 검토 완료 후 `red_team_clear` 또는 `red_team_block` 최종 판정을 내려라.

참조 파일:
- `adapters/content/openclaw_agent.py`
- `scripts/goal_loop.py`
- `scripts/openclaw_codex_bridge.py`
- `CLAUDE.md` (governing rules)

---

## HIGH 등급 발견사항

### H-1: `SLACK_CEO_USER_ID` 미설정 → 뮤테이션 명령 auth bypass

**파일:** `adapters/content/openclaw_agent.py`  
**함수:** `_authorized_for_high_risk()`

**문제 코드:**
```python
def _authorized_for_high_risk(requester_user_id: str | None) -> bool:
    expected_user_id = os.environ.get("SLACK_CEO_USER_ID", "").strip()
    if not expected_user_id:
        return bool(requester_user_id)   # env 미설정 시 누구든 통과
    return requester_user_id == expected_user_id
```

**확인된 사실:** Mac Mini `.env`에 `SLACK_CEO_USER_ID` 키 없음 (grep 결과 0건).

**영향:** `ACTION_REGISTRY`에서 `requires_approval: True`인 모든 명령이 Slack에 접근한 임의 사용자에게 개방됨.
- `record-decision` (승인 기록)
- `run-pipeline` (파이프라인 실행)
- `goal-create` (목표 생성)
- `goal-snapshot` (KPI 기록)

**제안 수정:**
1. Mac Mini `.env`에 `SLACK_CEO_USER_ID=<실제 Slack user ID>` 추가
2. env 미설정 시 fail-closed:
```python
def _authorized_for_high_risk(requester_user_id: str | None) -> bool:
    expected_user_id = os.environ.get("SLACK_CEO_USER_ID", "").strip()
    if not expected_user_id:
        return False  # fail-closed
    return requester_user_id == expected_user_id
```

---

### H-2: `_resolve_path` 절대경로 PROJECT_ROOT 경계 미검사

**파일:** `adapters/content/openclaw_agent.py`  
**함수:** `_resolve_path()`

**문제 코드:**
```python
def _resolve_path(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p          # 절대경로 그대로 통과 — 경계 없음
    return PROJECT_ROOT / p
```

**영향:**
- `tool_read_file("/Users/juntaepark/.ssh/id_rsa")` → SSH 프라이빗 키 노출
- `tool_write_file("/etc/hosts", ...)` → 시스템 파일 덮어쓰기
- H-1이 해결되지 않으면 임의 사용자가 Sonnet tool-use를 통해 접근 가능

**제안 수정:**
```python
_ALLOWED_READ_ROOTS = [PROJECT_ROOT]
_ALLOWED_WRITE_ROOTS = [
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "reports",
    PROJECT_ROOT / "runtime",
]

def _resolve_path(path: str, write: bool = False) -> Path:
    p = Path(path)
    resolved = (p if p.is_absolute() else PROJECT_ROOT / p).resolve()
    roots = _ALLOWED_WRITE_ROOTS if write else _ALLOWED_READ_ROOTS
    if not any(resolved.is_relative_to(r.resolve()) for r in roots):
        raise PermissionError(f"경로 접근 거부: {resolved}")
    return resolved
```

---

### H-3: `_format_with_haiku` 오늘 날짜 미주입 → 날짜 오계산

**파일:** `adapters/content/openclaw_agent.py`  
**함수:** `_format_with_haiku()`

**확인된 사실:** 실제 Slack 테스트에서 기한 2026-06-16을 "약 1년 6개월 후"로 오계산 (실제 약 4주 남음).

**문제:** 포맷터 시스템 프롬프트에 오늘 날짜 없음. Haiku가 학습 데이터 기준 날짜 추론.

**제안 수정:**
```python
def _format_with_haiku(user_message: str, raw_output: str) -> str:
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    system = (
        f"오늘 날짜는 {today_str}입니다. "
        "당신은 Harness의 AI 비서 OpenClaw입니다. "
        "아래 데이터를 CEO가 바로 이해할 수 있는 자연스러운 한국어로 설명하세요. "
        "날짜 계산 시 오늘 날짜를 기준으로 남은 기간을 정확히 계산하세요. "
        "key=value 형식이나 영문 필드명을 나열하지 말고, 의미 있는 해석과 함께 전달하세요."
    )
    ...
```

---

## MEDIUM 등급 발견사항

### M-1: `_cost_limit_reached()` Haiku classifier/formatter 경로 미적용

**파일:** `adapters/content/openclaw_agent.py` → `run()`

**문제:** budget gate가 Sonnet tool-use 직전에만 존재. Haiku classifier + formatter는 일 예산 초과 시에도 무조건 2회 호출.

**제안 수정:** intent classifier 진입 전 budget check 추가:
```python
if risk_scan["risk_level"] == "low" and not _should_skip_intent_classifier(...):
    if _cost_limit_reached():
        return _budget_block_message()
    intent = _classify_intent_with_haiku(user_message)
```

---

### M-2: `CAPITAL_ACTIONS_ENABLED` 브리지에서 실행 차단 미수행

**파일:** `scripts/openclaw_codex_bridge.py`

**문제:** `status` 응답에 `capital_actions_enabled` 값을 reporting만 할 뿐, `capital_action_approve` 타입 명령 실행 시 실제로 차단하지 않음.

**CLAUDE.md 요건:** "`capital_action_approve`는 `CAPITAL_ACTIONS_ENABLED=true`일 때만 기록 또는 실행할 수 있다."

**제안 수정:** `command_record_decision()` 내:
```python
if approval_type == "capital_action_approve":
    if os.getenv("CAPITAL_ACTIONS_ENABLED", "false").lower() != "true":
        _write_output("❌ CAPITAL_ACTIONS_ENABLED=false — 자본 집행 명령 차단.", args.output)
        return
```

---

### M-3: `correlation_id` goal_loop.py 전체 미전파

**파일:** `scripts/goal_loop.py`

**CLAUDE.md 요건:** "모든 action에 `correlation_id`를 포함한다."

**현황:** `record_goal_snapshot()`, `create_goal()`, `set_goal_model()`, `diagnose_goal()` 등 모든 DB write에 `correlation_id` 없음.

**제안:** migration으로 관련 테이블에 `correlation_id UUID` 컬럼 추가 + 모든 write 함수에 인자로 전파.

---

### M-4: `slack_listener.log` rotation 미설정

**위치:** Mac Mini `~/Library/LaunchAgents/com.harness.slack-listener.plist`

**문제:** 로그 파일 무한 증가. 장기 운영 시 디스크 고갈 위험.

**제안:** Python `RotatingFileHandler` 적용 (10MB × 5개 rotation).

---

## CLAUDE.md 컴플라이언스 갭

| 요건 | 현황 | 위험도 |
|------|------|--------|
| `qa_clear` — 고객-facing 산출물 QA gate | 미구현 | HIGH (발행 시 즉시 차단) |
| `pre_mortem` — high-impact 결정 전 분석 | 전체 미수행 | MEDIUM |
| `red_team_clear` — 2개 이상 LLM cross-verification | 미충족 | HIGH (이 파일이 그 요청) |
| `legal_review_approve` — 외부 발행 전 법률 검토 | 미수행 | HIGH (발행 시 차단) |

---

## 수정 우선순위

```
즉시 (오늘):
  H-1a: Mac Mini .env에 SLACK_CEO_USER_ID 추가
  H-1b: _authorized_for_high_risk fail-closed 수정
  H-3:  _format_with_haiku 날짜 주입

이번 주:
  H-2:  _resolve_path PROJECT_ROOT boundary 강제
  M-1:  budget gate Haiku 경로 적용
  M-2:  CAPITAL_ACTIONS_ENABLED bridge 차단 추가

다음 스프린트:
  M-3:  correlation_id migration + goal_loop 전파
  M-4:  log rotation 설정
  compliance: qa_clear 구현 계획 수립
```

---

## 수신 LLM 검토 요청사항

1. H-1 ~ H-3 진단의 정확성을 코드 직접 열람으로 확인하라.
2. H-2 `_resolve_path` exploit이 Sonnet tool-use를 통해 실제로 가능한지 검증하라.
3. M-2 브리지 코드에서 `CAPITAL_ACTIONS_ENABLED` 실제 차단 로직 존재 여부를 확인하라.
4. Claude가 놓쳤을 수 있는 취약점 (SQL injection, prompt injection, rate limiting, race condition) 독립 스캔.
5. 최종 판정: `red_team_clear` 또는 `red_team_block` (이유 포함).
6. 판정을 `docs/governance/RED_TEAM_LOG.md`에 날짜, 참여 LLM 목록, 미해결 항목과 함께 기록하라.

---

*Prepared by Claude Sonnet 4.6 | 2026-05-18 | Single-LLM — NOT a final red_team_clear*
