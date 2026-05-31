# 페르소나 Fallback 통합 검증

## 📋 **중앙 집약점: `call_persona()`**

모든 페르소나 호출이 `scripts/run_persona.py`의 **`call_persona()` 함수를 통합**됩니다.

### 핵심 로직 (라인 604-629)

```python
def call_persona(
    persona: Persona,
    task: str,
    correlation_id: str,
    extra_context: str = "",
) -> tuple[str, bool]:
    """Build the persona prompt and call its primary LLM (or fallback). Returns (text, ok)."""
    # ✅ 라인 612: Fallback 적용!
    effective_provider = get_current_provider(
        persona.handle, 
        persona.provider, 
        persona.fallback_provider
    )
    
    prompt = _build_prompt(persona, task, correlation_id, extra_context)
    # ✅ 라인 615: Fallback이 적용된 LLM으로 호출
    text, ok = call_llm(effective_provider, prompt, persona.handle, persona)
    
    # OOC 감지 후 재시도 로직
    if ok and _OOC_PATTERNS.search(text):
        retry_prompt = ...
        text, ok = call_llm(effective_provider, retry_prompt, persona.handle, persona)
    
    if ok:
        text = format_persona_output(persona, text)
    return text, ok
```

---

## ✅ **모든 페르소나 호출 경로**

### 1. 오케스트레이션 (회의실 flow)

**파일**: `adapters/content/orchestrator.py`

| 경로 | 라인 | 설명 |
|------|------|------|
| `respond_as_persona()` → `call_persona()` | 213 | CEO가 특정 페르소나 언급 (예: "Friday님 ...") |
| `orchestrate()` 라운드 1 → `call_persona()` | 267 | 각 팀이 CEO 주제에 대한 의견 제시 |
| `orchestrate()` 라운드 N → `call_persona()` | 286 | 다른 팀의 의견을 본 후 재논의 (extra_context) |

**예시**:
```python
# orchestrator.py, 라인 267
text, ok = call_persona(persona, subtask, correlation_id)
# → call_persona() → get_current_provider(fallback 적용) → call_llm()
```

---

### 2. Slack DM & 멘션

**파일**: `adapters/content/slack_listener.py`

**경로**: 
- DM 수신 → `run_persona.py` 직접 호출 또는 orchestrator 거침
- `@마케팅팀장님 ...` → `respond_as_persona()` → `call_persona()` → fallback 적용

**라인 291** (Slack 내 일부 Jarvis 호출):
```python
from scripts.run_persona import call_llm  # Jarvis용 직접 호출은 예외 처리
```

⚠️ 참고: `call_llm()` 직접 호출도 **fallback 로직을 포함**하고 있습니다 (라인 482-548).

---

### 3. CLI 직접 실행

**파일**: `scripts/run_persona.py`

**명령**:
```bash
python scripts/run_persona.py <persona_name> "<task>"
# → call_persona() → get_current_provider(fallback 적용) → call_llm()
```

---

## 🔄 **Fallback 작동 흐름**

```
User/orchestrator calls call_persona(persona, task)
    ↓
call_persona() calls get_current_provider()
    ↓
get_current_provider() 로직:
    1. Primary LLM 확인 (persona.provider)
    2. runtime/persona_llm_fallback.json 체크
    3. Fallback 중이면? → fallback_provider 반환
    4. 정상이면? → primary provider 반환
    5. 5분 cooldown: 최근 재시도한 지 < 5분이면 fallback 유지
    ↓
call_llm(effective_provider, prompt, ...)
    ↓
LLM 호출 성공? → 응답 반환
LLM 호출 실패 (credit exceeded)? → record_fallback() 기록 → retry with fallback LLM
    ↓
Response: "[⚠️ primary_llm 크레딧 부족 → fallback_llm 사용]"
```

---

## ✨ **중요: `call_llm()` 함수도 이미 fallback 포함**

**파일**: `scripts/run_persona.py`, 라인 482-548

```python
def call_llm(
    provider: str,
    prompt: str,
    caller: str = "unknown",
    persona: Persona | None = None,
    fallback_provider_override: str | None = None,
) -> tuple[str, bool]:
    """Call an LLM with fallback support."""
    
    # Primary 호출 시도
    result, success = _run_llm_command(provider, prompt)
    
    # 실패하고 fallback이 있으면
    if not success and persona and persona.fallback_provider:
        # 에러 패턴 감지 (usage_limit_exceeded, credit 등)
        if _is_credit_error(result):
            record_fallback(
                persona.handle, 
                provider, 
                persona.fallback_provider, 
                "credit_exhausted"
            )
            # Fallback LLM 재시도
            result, success = _run_llm_command(persona.fallback_provider, prompt)
            if success:
                result = f"[⚠️ {provider} 크레딧 부족 → {persona.fallback_provider} 사용]\n{result}"
    
    return result, success
```

---

## 🧪 **검증 방법**

### 1. 전체 fallback 상태 확인
```bash
source .venv/bin/activate
python scripts/llm_fallback_manager.py status
```

### 2. 특정 페르소나 상태
```bash
python scripts/llm_fallback_manager.py status tars
```

### 3. 페르소나 호출 테스트 (Fallback 적용 확인)
```bash
# 일반 호출 (fallback 적용됨)
python scripts/run_persona.py c3po "마케팅 전략을 제시해줘"

# 출력에 다음이 포함되면 fallback 작동함:
# [⚠️ gemini 크레딧 부족 → claude 사용]
```

### 4. 수동 Fallback 트리거 (테스트용)
```bash
# TARS를 Claude fallback으로 전환
python scripts/llm_fallback_manager.py record tars codex claude "test_fallback"

# TARS 호출 시 Claude로 응답 반환
python scripts/run_persona.py tars "파이프라인 설계해줘"

# 5분 후 자동 복구
python scripts/check_llm_fallback_status.py

# TARS 호출 시 Codex로 다시 응답
python scripts/run_persona.py tars "파이프라인 설계해줘"
```

---

## 📊 **페르소나별 Fallback 매핑**

| 페르소나 | Primary | Fallback | 상태 |
|---------|---------|----------|------|
| Jarvis | Claude | Gemini | ✅ 정상 |
| Friday | Claude | Gemini | ✅ 정상 |
| Vision | Claude | Gemini | ✅ 정상 |
| Ledger | Claude | Gemini | ✅ 정상 |
| KITT | Claude | Gemini | ✅ 정상 |
| C3PO | Gemini | Claude | ✅ 정상 |
| Coach | Gemini | Claude | ✅ 정상 |
| Watchman | Claude | Gemini | ✅ 정상 |
| Scribe | Claude | Gemini | ✅ 정상 |
| TARS | Codex | Claude | ✅ 정상 |

---

## 🎯 **결론**

**모든 페르소나가 이미 공통적으로 fallback 로직을 적용하고 있습니다.**

- ✅ 중앙 집약점: `call_persona()` 함수
- ✅ 모든 호출 경로: orchestrator, Slack, CLI 모두 `call_persona()` 통과
- ✅ 이중 게이트: `call_persona()` + `call_llm()` 두 단계 모두 fallback 체크
- ✅ 자동 복구: `check_llm_fallback_status.py` (5분 주기)

어떤 페르소나를 호출하든, **Primary LLM이 부족하면 자동으로 Fallback LLM으로 전환**됩니다.
