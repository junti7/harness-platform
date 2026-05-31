# LLM Fallback System — 운영 가이드

## 개요

페르소나의 LLM(Claude, Gemini, Codex 등)이 크레딧 부족 또는 사용량 초과로 실패할 경우, **자동으로 fallback LLM으로 전환**하고, 원래 LLM이 복구되면 **자동으로 복구**하는 시스템입니다.

## 작동 원리

### 1. Primary LLM 실패 시 Fallback

```
TARS(엔지니어링팀) calls Codex → ❌ "Usage limit exceeded"
↓
Fallback manager detects usage_limit_exceeded error
↓
Auto-switch to Claude (fallback provider)
↓
Claude responds successfully ✅
↓
Response shows: "[⚠️ codex 크레딧 부족 → claude 사용]"
```

### 2. 상태 추적

Fallback 상태는 `runtime/persona_llm_fallback.json`에 저장됩니다:

```json
{
  "tars": {
    "primary_provider": "codex",
    "current_provider": "claude",
    "switched_at": "2026-05-31T10:03:21.515078+00:00",
    "reason": "usage_limit_exceeded",
    "last_retry": "2026-05-31T10:10:00Z"
  }
}
```

### 3. 자동 복구

5분마다 실행되는 `check_llm_fallback_status.py`가:
- Primary LLM이 다시 사용 가능한지 체크
- 가능하면 자동으로 fallback 상태 제거
- Primary LLM으로 원복

```
Primary LLM 체크 (5분 주기)
  ↓
✓ Codex 다시 사용 가능?
  ↓
Yes → fallback 상태 제거, TARS는 다시 Codex 사용
No → fallback 상태 유지, 5분 후 재시도
```

## 페르소나별 설정

### Primary LLM과 Fallback LLM

| 페르소나 | Primary | Fallback |
|---------|---------|----------|
| Jarvis | Claude | Gemini |
| Friday | Claude | Gemini |
| Vision | Claude | Gemini |
| Ledger | Claude | Gemini |
| KITT | Claude | Gemini |
| C3PO | Gemini | Claude |
| Coach | Gemini | Claude |
| Watchman | Claude | Gemini |
| Scribe | Claude | Gemini |
| TARS | Codex | Claude |

### 설정 방법 (agents/registry.py)

```python
Persona(
    handle="tars",
    team_ko="엔지니어링팀",
    role="codebase, schema, automation, tests",
    provider="codex",           # Primary LLM
    escalation="claude",        # (다른 용도)
    fallback_provider="claude", # ← Fallback LLM
    ...
)
```

## 수동 조작

### 1. Fallback 상태 확인

```bash
source .venv/bin/activate
python scripts/llm_fallback_manager.py status              # 전체 상태
python scripts/llm_fallback_manager.py status tars        # 특정 페르소나
```

### 2. Fallback 강제 설정

```bash
python scripts/llm_fallback_manager.py record tars codex claude "manual_test"
```

### 3. Fallback 상태 제거

```bash
python scripts/llm_fallback_manager.py clear tars
```

### 4. 복구 상태 확인

```bash
python scripts/check_llm_fallback_status.py
```

## Cron 설정 (자동 복구)

매 5분마다 복구 체크를 실행하려면 crontab에 추가:

```bash
# Edit crontab
crontab -e

# Add this line:
*/5 * * * * cd /path/to/harness-platform && source .venv/bin/activate && python scripts/check_llm_fallback_status.py >> logs/llm_fallback_cron.log 2>&1
```

## 로그

- **Fallback 상태 변화**: `runtime/persona_llm_fallback.json`
- **복구 체크 결과**: `logs/llm_fallback_check.log` (JSON 형식, 한 줄씩)

```bash
# 최근 복구 시도 확인
tail -5 logs/llm_fallback_check.log | jq .
```

## 사용자가 볼 메시지

### Fallback 사용 중

```
[⚠️ codex 크레딧 부족 → claude 사용]
refiner.py(Tier 3) 코드를 봤습니다. 느린 원인 짚어드릴게요.
```

### 복구 완료

Fallback 상태가 제거되면 자동으로 원래 LLM으로 복구됩니다. 사용자 입장에서는:
- 다음 호출부터 다시 Primary LLM 사용
- 별도의 메시지 없음 (투명한 복구)

## 문제 해결

### Q1: Fallback이 계속 나타나요

```bash
# 1. Primary LLM의 크레딧이 정말 복구되었는지 확인
python scripts/llm_fallback_manager.py status

# 2. 다음 복구 체크 시간을 기다리거나 수동 트리거
python scripts/check_llm_fallback_status.py

# 3. 여전히 실패하면 Primary LLM 수동 확인
echo "test" | /opt/homebrew/bin/codex exec --sandbox read-only -
```

### Q2: Fallback은 싫고 실패 메시지가 보고 싶어요

Fallback을 비활성화하려면 `agents/registry.py`에서 `fallback_provider=None`으로 설정:

```python
Persona(
    handle="tars",
    ...
    fallback_provider=None,  # Fallback 비활성화
    ...
)
```

### Q3: Fallback을 자동으로 하지 말고 수동 승인 받고 싶어요

현재는 자동입니다. 수동 승인 모드로 변경하려면:
- `scripts/run_persona.py`의 `call_llm()` 함수에서 fallback 자동 호출 제거
- 대신 로그에만 기록하고 사용자에게 보고

## 기술 상세

### Fallback 감지 로직 (run_persona.py)

```python
is_credit_error = (
    "usage_limit_exceeded" in output.lower()
    or "usage limit" in output.lower()
    or "credit" in output.lower()
    or "you've hit your usage limit" in output.lower()
)

if is_credit_error and fallback_provider:
    # Fallback으로 재시도
```

### Primary 복구 체크 (check_llm_fallback_status.py)

```python
is_available = _is_provider_available(primary, timeout=5)
# CLI --version 호출로 간단한 가용성 테스트
```

### Retry 쿨다운

- 첫 복구 체크: 즉시
- 이후 재시도: 5분 주기
- 목적: Primary LLM에 과부하 주지 않기
