# 비용 최적화 보고서: Claude API 의존성 제거

- **Date:** 2026년 5월 23일
- **Owner:** Jarvis (Chief of Staff)
- **Status:** 완료 (DONE)

---

### 1. 문제 정의 (Problem)

Anthropic (Claude) API에서 원인 불명의 '자동 충전 크레딧'으로 인한 비용이 지속적으로 발생함. 수익이 없는 현 단계에서, 예측 및 통제가 어려운 불필요한 비용을 반드시 최소화해야 할 필요성이 제기됨.

### 2. 원인 분석 (Analysis)

`harness-platform` 전체 아키텍처 분석 결과, Claude API 비용은 다음 세 가지 주요 영역에서 발생하고 있었음.

1.  **Tier 3 Premium AI 정제:** `PLATFORM.md`에 정의된 핵심 데이터 정제 파이프라인(`adapters/content/refiner.py`)이 Claude API(`claude-sonnet-4-6`)를 하드코딩하여 사용하고 있었음.
2.  **핵심 에이전트의 주력 LLM:** `KITT`, `Watchman`, `Vision` 등 다수의 핵심 페르소나들이 `SYSTEM_PROMPT.md`에 `Primary LLM: Claude`로 설정되어, 일상적인 작업 수행 시 비용을 발생시킴.
3.  **Red-Team 검증:** 프로토콜에 따라 Claude를 검증 과정에 포함하여 비용이 발생.

### 3. 해결 조치 (Resolution)

위 분석에 따라, Claude API에 대한 의존성을 제거하고 비용 효율적인 Gemini 중심으로 아키텍처를 변경하는 아래 조치들을 수행함.

#### 3.1. 핵심 에이전트 LLM 교체
- **조치:** `KITT`를 제외한 모든 핵심 에이전트의 `SYSTEM_PROMPT.md` 파일에서 `Primary LLM`을 `Claude`에서 `Gemini`로 변경함.
- **영향:** 에이전트의 일상적인 작업은 더 이상 Claude API 비용을 발생시키지 않음.

#### 3.2. KITT 아키텍처 변경
- **조치:** `KITT`의 경우, 법률 검토 등 높은 수준의 Reasoning이 필요할 수 있는 점을 감안하여 Claude 접근성을 유지하되, API 직접 호출을 금지함. 대신 `run_shell_command`를 통해 `claude` CLI를 호출하도록 `SYSTEM_PROMPT.md`에 명시하고 가이드라인을 추가함.
- **영향:** KITT의 Claude 사용을 API 과금 체계에서 분리하여 비용을 최소화하거나, 최소한 별도로 추적/관리할 수 있게 됨.

#### 3.3. Tier 3 정제 파이프라인 교체
- **조치:** `adapters/content/refiner.py`의 코드를 전면 수정하여, `anthropic` 라이브러리 대신 `google-generativeai` 라이브러리를 사용하도록 변경.
    - 모델을 `claude-sonnet-4-6`에서 `gemini-1.5-pro-latest`로 교체.
    - Gemini 가격 정책에 맞게 비용 계산 및 로깅 로직을 모두 업데이트.
- **영향:** 가장 비용이 많이 발생하던 데이터 정제 파이프라인을 비용 효율적인 Gemini API로 이전함.

#### 3.4. 의존성 추가
- **조치:** `requirements.txt`에 `google-generativeai` 라이브러리를 추가하여, 변경된 코드가 정상적으로 실행될 수 있도록 환경을 구성함.

### 4. 최종 요약 및 다음 단계 (Summary & Next Steps)

**모든 조치가 완료되었습니다.**

이제 harness-platform은 대부분의 클라우드 LLM 작업을 Gemini API를 통해 수행하며, Claude API로 인한 자동 결제 비용은 발생하지 않거나 현저히 줄어들 것으로 예상됩니다.

**필수 후속 조치:**
- 시스템 운영을 위해 `.env` 파일에 `GOOGLE_API_KEY`가 올바르게 설정되어 있는지 반드시 확인해야 합니다.
- 앞으로 며칠간 API 사용량 및 비용을 모니터링하여, 변경된 아키텍처가 의도대로 작동하는지 검증하는 것이 좋습니다.
