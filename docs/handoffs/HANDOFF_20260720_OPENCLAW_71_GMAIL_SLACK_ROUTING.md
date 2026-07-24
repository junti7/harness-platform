# HANDOFF_20260720: OpenClaw 7.1 기능 이식, Gmail OAuth 갱신, Slack DM 응답 보장 및 글로벌 시황 라우팅 고도화

- 작성일: 2026-07-20
- 작성자: Antigravity AI (Pair Programming Assistant)
- 대상 시스템: Harness Platform (Local MBP & Mac Mini Production)

> **운영 규칙**: Codex CLI 사용 시 caveman ultra 응답 규칙을 적용하되, 코드 변경 요약은 정확하게 유지한다.

---

## 1. 작업 개요 (Executive Summary)

OpenClaw 2026.7.1 업그레이드 기능 이식, Harness OS 관제 대시보드 연동, Gmail OAuth2 인증 복구, Slack DM 응답 불능 버그 수정, 그리고 글로벌 증시 시황 질의 처리 파이프라인 고도화를 완료하고 Mac Mini 프로덕션 서버에 성공적으로 배포하였습니다.

---

## 2. 세부 코드 변경 사항 및 파일 목록 (Code Changes Summary)

### ① OpenClaw 2026.7.1 기능 이식 및 대시보드 연동
1. **[adapters/content/openclaw_agent.py](file:///Users/juntae.park/projects/harness-platform/adapters/content/openclaw_agent.py)**
   - `SESSION_PERSIST_DIR` (`runtime/openclaw_sessions`) 및 JSONL 기반 세션 보존/복구 로직 (`_persist_session_message`, `_restore_session`) 구현
   - Sonnet 5 A/B 실험 세션 단위 50/50 분크 라우팅 (`OPENCLAW_AB_ENABLED`, `OPENCLAW_AB_MODEL_B`) 추가
   - ClawRouter 동적 모델 선택 연동 (`_query_clawrouter`, `OPENCLAW_CLAWROUTER_ENABLED`) 추가

2. **[harness-os/backend/main.py](file:///Users/juntae.park/projects/harness-platform/harness-os/backend/main.py)**
   - `/api/costs/unified-usage` 엔드포인트 신설 (Harness DB `api_cost_log` + OpenClaw Gateway telemetry 통합)

3. **[harness-os/frontend/src/pages/OpenClawMonitorPage.tsx](file:///Users/juntae.park/projects/harness-platform/harness-os/frontend/src/pages/OpenClawMonitorPage.tsx)** & **[SettingsPage.tsx](file:///Users/juntae.park/projects/harness-platform/harness-os/frontend/src/pages/SettingsPage.tsx)**
   - 통합 LLM 사용량 카드 및 OpenClaw 7.1 상태 뱃지(300s watchdog, session persistence, Sonnet 5 A/B) 추가
   - SettingsPage에서 관제 센터로 바로 이동하는 숏컷 버튼 연동 (`App.tsx` `onNavigate` 전달)

4. **[scripts/openclaw_watchdog.sh](file:///Users/juntae.park/projects/harness-platform/scripts/openclaw_watchdog.sh)** & **[setup_openclaw_watchdog_mac_mini.sh](file:///Users/juntae.park/projects/harness-platform/scripts/setup_openclaw_watchdog_mac_mini.sh)**
   - 왓치독 실행 주기 120초 → 300초 경량화
   - 크래시 원인 분류 (`oom_kill`, `gateway_unresponsive`, `process_died`) 및 활성 세션수 로그 채록 기능 추가

---

### ② Gmail OAuth2 토큰 갱신 및 키링 환경 설정
1. **Gmail OAuth2 재인증**
   - Mac Mini `gog` CLI (`/opt/homebrew/bin/gog`) remote OAuth 승인 및 새 refresh token 교환 완료
   - `GOG_KEYRING_BACKEND=file`, `GOG_KEYRING_PASSWORD` 환경변수로 non-interactive SSH 환경 동작 보장

2. **GitHub PAT (`GITHUB_TOKEN`) 설정**
   - [.env.example](file:///Users/juntae.park/projects/harness-platform/.env.example), 로컬 `.env`, Mac Mini `.env`에 `GITHUB_TOKEN=ghp_...` 반영 완료

---

### ③ Slack DM 응답 보장 및 UI/UX 개선
1. **[adapters/content/openclaw_agent.py](file:///Users/juntae.park/projects/harness-platform/adapters/content/openclaw_agent.py)**
   - `_GMAIL_SUMMARY_RE` 정규식을 확장하여 자연스러운 한국어 메일 요청 표현("오늘 나에게 온 메일", "메일 제목은?", "어제/최근/금일 이메일" 등 8개 패턴) 100% 매칭 보장

2. **[adapters/content/slack_listener.py](file:///Users/juntae.park/projects/harness-platform/adapters/content/slack_listener.py)**
   - `_wait_and_reply` 데몬 스레드에 `future.result(timeout=300)` 가드 추가 및 `TimeoutError` 예외 처리/완료 로그 추가
   - 비동기 처리 메시지 안내 문구를 `:thinking_face: 처리 중... (잠시 기다려주세요 — 결과가 별도 메시지로 도착합니다)` 로 변경하여 사용자 오해 방지

---

### ④ 글로벌 증시 시황 질의 라우팅 고도화
1. **[adapters/content/openclaw_agent.py](file:///Users/juntae.park/projects/harness-platform/adapters/content/openclaw_agent.py)**
   - `TOOL_KEYWORDS` 및 `_EXPLICIT_TOOL_NEED_RE`, `_HARD_TOOL_NEED_RE`에 `증시`, `시황`, `글로벌 증시`, `주식 시장`, `거시경제`, `나스닥`, `s&p500` 키워드 추가
   - 글로벌 증시/매크로 질문 시 자동으로 `web_search` 도구를 1~2회 수행하여 실시간 지수 및 거시경제 지표 수집
   - `_maybe_inject_trading_context` 프롬프트 지침을 수정하여 전체 시장 질문 시 개인 보유 포지션 단독 응답을 방지하고 글로벌 마켓 분석을 1순위로 출력하도록 개선
   - `_prefer_gemini_openclaw`가 `ANTHROPIC_API_KEY` 존재 시 유효한 API 호출을 우선하도록 개선

2. **[scripts/llm_fallback_manager.py](file:///Users/juntae.park/projects/harness-platform/scripts/llm_fallback_manager.py)**
   - `_is_provider_available("claude")` 실행 시 CLI `claude -p "reply with ok"` 호출에 `stdin=subprocess.DEVNULL`을 지정하여 3초 타임아웃 감지 오류 해결

---

## 3. 검증 및 배포 내역 (Verification & Deployment)

- **Agent Completion Guard**: 모든 주요 변경사항에 대해 `agent_completion_guard.py` 검증 통과 (`CLEAR`)
- **Git Commits & Push**:
  - `67e8340`: `docs(env): add GITHUB_TOKEN placeholder to .env.example`
  - `9f32250`: `fix(slack): gmail fast-path regex 확장 + _wait_and_reply 300s timeout guard`
  - `9200d62`: `ux(slack): '처리 중...' 메시지에 '결과가 별도 메시지로 도착' 안내 추가`
  - `1c5696e`: `feat(openclaw): 글로벌 증시 시황 및 거시경제 질의 처리 체계 구축`
  - `59df916`: `fix(openclaw): 글로벌 시황 및 매크로 투자 전략 요청 처리 체계 고도화`
- **Mac Mini Production Deploy**: `scripts/deploy_to_macmini.sh`로 배포 완료 및 `com.harness.slack-listener` 재기동 확인

---

## 4. 잔여 과제 및 후속 참고 사항 (Next Actions)

- **Gemini Red Team**: 2026-06-30까지 Gemini API 크레딧 이슈로 Red Team 자동 호출 대상 제외 상태 유지 (Claude + Codex / Copilot 2-of-3 다수결 적용 중)
- **Ollama 34s Latency**: 로컬 모델(gemma4) 처리 지연 시간 단축 필요 시 쿼터가 유효한 Gemini 3.5 Flash / Haiku 모델로의 우선 전환 검토 가능
