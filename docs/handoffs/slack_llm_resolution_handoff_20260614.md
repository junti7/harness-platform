# Slack 리스너 무응답 및 로컬 LLM Fallback 장애 해결 핸드오프 (2026-06-14)

이 문서는 `/clear`로 대화 세션을 초기화하고 Fresh Start를 하기 위해, 직전까지 진행된 Slack 무응답 오류 해결 및 로컬 LLM Fallback 최적화 작업 내역을 정리한 핸드오프 파일입니다.

---

## 1. 작업 개요 및 주요 성과
* **목표**: 사용자가 Slack에서 "백엔드 에러 로그 보여줘" 등의 명령어를 내렸을 때 무응답이었던 장애를 조치하고, Google Gemini API 429(한도 초과) 상황에서도 로컬 모델 Fallback이 오류 없이 정상 동작하도록 인프라를 튜닝하는 것.
* **성과**:
  * 백그라운드에서 중단되었던 **Slack Socket Mode Listener (`slack_listener.py`)를 재기동**하여 연결 정상화.
  * 추론 능력이 결여되어 엉뚱한 스크립트를 호출하던 `qwen2.5:1.5b` 모델을 **`qwen2.5:7b` 모델로 업그레이드**하여 로컬 Fallback 적용 완료.
  * M5 (32GB RAM) 사양에 최적화된 최상위 성능의 로컬 LLM 추천 리포트 마련.

---

## 2. 장애 원인 및 조치 상세

### 🛠️ 장애 1: Slack 지시에 대해 아예 무반응인 현상
* **원인**: 백그라운드 데몬 목록 및 프로세스 모니터링 결과, `slack_listener.py` 프로세스가 완전히 꺼져 있었습니다.
* **조치**: 프로젝트 가상환경(`.venv`)을 활용해 백그라운드로 리스너를 재기동 완료했습니다.
  ```bash
  nohup .venv/bin/python adapters/content/slack_listener.py > logs/slack_listener.stdout.log 2> logs/slack_listener.stderr.log &
  ```
  현재 PID `7016`으로 활성화되어 `⚡️ Bolt app is running!` 연결 수립이 완료된 상태입니다.

### 🛠️ 장애 2: 로컬 LLM Fallback 시 엉뚱한 Tool Call을 날리는 현상
* **원인**: `qwen2.5:1.5b` 모델의 지능(1.5B 파라미터) 부족으로 인해 OpenClaw의 거대한 15k 시스템 프롬프트를 해석하지 못하고, "백엔드 에러 로그 보여줘"라는 말에 엉뚱하게 `restart-crons.js` 스크립트를 도구로 호출하려 하는 환각(Hallucination)이 발생했습니다.
* **조치**:
  1. Ollama를 통해 훨씬 더 정교한 도구 호출이 가능한 **`qwen2.5:7b` (Instruct)** 모델을 로컬 다운로드 완료했습니다.
  2. `.env` 파일의 로컬 폴백 모델 설정을 `qwen2.5:7b`로 수정했습니다.
     * `GEMINI_LOCAL_FALLBACK_MODEL=qwen2.5:7b`
  3. OpenClaw 글로벌 설정 파일(`~/.openclaw/openclaw.json`)의 `fallbacks` 및 `models`를 `ollama/qwen2.5:7b`로 편입하고 40k Context Window를 구성 완료했습니다.
  4. 변경된 설정을 적용하기 위해 `ai.openclaw.gateway` 서비스 및 `slack_listener` 프로세스를 모두 재시작하였습니다.

---

## 3. 하드웨어 최적화 로컬 LLM 제안 (M5, 32GB RAM 기준)

현재 Mac Mini의 하드웨어 스펙은 **Apple M5 (32GB RAM)**로 매우 뛰어납니다. PostgreSQL DB, Uvicorn 백엔드, 실시간 트레이딩 봇 등의 다른 핵심 프로세스에 방해를 주지 않는 안전한 예산 내에서 최상의 성능을 낼 수 있는 모델을 제안합니다.

* **최종 제안: `Qwen2.5-14B-Instruct` (Q4_K_M 양자화)**
  * **메모리 점유**: 약 `9.0 GB` (전체 32GB 중 28%만 차지하여 다른 Job에 OOM이나 병목을 전혀 주지 않음)
  * **성능적 가치**: 7B 체급 대비 JSON/Tool-calling 구조의 안정성이 대폭 강화되었으며, 한국어 지시 이행 능력이 최고 수준입니다.
  * **반영법**: 
    ```bash
    ollama pull qwen2.5:14b
    ```
    이후 `.env` 및 `openclaw.json` 내 Fallback 모델명을 `qwen2.5:14b`로 변경하고 재시작하면 됩니다.

---

## 4. Fresh Start 이후 액션 아이템
1. **Slack 연동 확인**: 세션 초기화 이후 Slack을 통해 다시 `"백엔드 에러 로그 보여줘"`를 전송하여, `qwen2.5:7b` Fallback 모델이 정상적으로 Uvicorn의 로그(`logs/harness-os-backend.error.log`)를 요약해서 반환하는지 검증합니다.
2. **14B 모델 업그레이드 (선택)**: 7B 모델보다 더욱 정교한 Chief of Staff 대행을 위해 `qwen2.5:14b` 모델을 추가로 다운받아 Fallback 대상 모델로 업그레이드하는 것을 권장합니다.
