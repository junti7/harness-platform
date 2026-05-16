# PLATFORM.md - Harness Autonomous Automation Platform
# Version: 2.1 | 도메인: 불가지론적(Agnostic)
# 이 문서는 도메인이 바뀌어도 변하지 않는 플랫폼 헌법이다.

---

## 1. 플랫폼 철학: 비관적 자율성 (Pessimistic Autonomy)

본 플랫폼은 다음을 절대 신뢰하지 않는다:
- AI의 판단 (환각 항상 가능)
- OS의 안정성 (스케줄링, 메모리 경합)
- 외부 서비스의 가용성 (API 단절, 지연)
- 네트워크의 연속성 (단절, 레이턴시 폭증)

모든 설계는 "잘 될 것이다"가 아니라 "망가질 것이다"를 전제로 한다.

---

## 2. 핵심 AI 계층 구조 (4-Tier AI Pipeline)

본 플랫폼의 모든 도메인 어댑터는 반드시 이 4계층을 따른다.
계층 간 역방향 호출 및 계층 건너뛰기는 엄격히 금지한다.

### Tier 1: 규칙 기반 수집 (Rule-Based Collector)
- 역할: 외부 소스에서 Raw 데이터를 수집
- 도구: RSS, API, 웹 스크래핑
- AI 사용: 없음 (순수 규칙 기반)
- 비용: 없음
- 출력: raw_signals 테이블 (JSONField 적재)
- 원칙: 모든 것을 수집하되 아무것도 판단하지 않는다

### Tier 2: On-device AI 필터링 (Local LLM Gate)
- 역할: Raw 데이터의 대량 1차 처리 (분류, 중복 제거, 가치 점수화)
- 도구: Ollama + `gemma2:27b` 기본. 하드웨어/성능 제약에 따라 동급 local model로 교체 가능하되 `.env`의 `OLLAMA_MODEL`과 실행 로그에 실제 모델명을 남긴다.
- AI 사용: 로컬 LLM (무료, 무제한)
- 비용: 없음 (전기세 제외)
- 입력: raw_signals
- 출력: filtered_signals (score 포함)
- 원칙:
  * Raw 데이터의 최소 80%를 이 단계에서 탈락시킨다
  * Tier 3(유료 AI)에 넘기기 전 반드시 이 게이트를 통과해야 한다
  * 원문 전체 LLM 주입 금지 — 최대 500토큰만 주입

### Tier 3: Premium AI 정제 (Cloud LLM Refinery)
- 역할: Tier 2를 통과한 고가치 데이터만 심층 분석 및 최종 정제
- 도구: Claude API / Gemini API
- AI 사용: 외부 유료 AI
- 비용: 발생 (최소화 필수)
- 입력: filtered_signals (score 상위 N개만)
- 출력: refined_outputs
- 비용 통제 규약:
  * Prompt Caching 강제 적용 (고정 시스템 프롬프트)
  * 배치 처리 가능한 작업은 실시간 API 호출 금지
  * 입력 토큰 한도: 요청당 최대 4,000 토큰을 목표로 한다. 코드가 강제하지 않는 경로에서는 호출 전 추정치와 실제 입력 크기를 로그에 남긴다.
  * 일일 API 비용 한도 초과 시 자동 중단 (킬스위치)

### Tier 4: 클라우드 배포 (Cloud Publisher)
- 역할: 최종 정제된 데이터만 외부 채널에 발행
- 도구: Notion API, Slack Webhook
- 입력: refined_outputs (검증 완료된 것만)
- 원칙:
  * Sanity Check 통과 전 배포 금지
  * Idempotency Key로 중복 발행 원천 차단
  * 배포 실패 시 재시도 최대 3회, 이후 Dead Letter Queue 이동

---

## 3. 5단계 운영 워크플로우

모든 도메인 어댑터의 실행은 이 순서를 따른다:

1. Context setting   → 현재 도메인/태스크 컨텍스트 로드
2. Skill setting     → 사용 가능한 도구/API 확인 및 초기화
3. Agent setting     → 각 에이전트 역할 및 권한 설정
4. PLATFORM.md 로드  → 위반 불가 규약 에이전트에 주입
5. CLAUDE.md 로드    → 도메인별 운영 지침 에이전트에 주입
↓
Task execute         → 실제 파이프라인 실행

---

## 4. 데이터 아키텍처: 하이브리드 스키마

### raw_signals (Tier 1 출력)
- source: 수집 소스 (arXiv, RSS 등)
- ingested_at: 수집 시각
- raw_data: JSONField (원문 그대로)
- status: pending / filtered_pass / filtered_fail

### filtered_signals (Tier 2 출력)
- source, title, summary (로컬 LLM 요약)
- score: 가치 점수 (0.0 ~ 1.0)
- category, content_hash, tier2_model

### refined_outputs (Tier 3 출력)
- final_title, final_body, tags
- tier3_model, published, published_at

---

## 5. 안정성 가드 (모든 도메인 공통 적용)

### 5.1 Liveness Probe
- 수집 실행 시점마다 대상 소스의 liveness를 확인한다.
- 장기 실행 daemon이 있는 경우 10초 주기 probe를 사용할 수 있으나, batch collector에서는 source별 실행 시점 probe로 대체한다.
- 3회 연속 실패 시 해당 소스 Pause 또는 cooldown 처리한다.

### 5.2 Stale Data Guard
- `source_catalog.rate_limit_policy.stale_minutes` 또는 source별 기본 stale window를 따른다.
- 논문/RSS/기업 블로그처럼 발행 주기가 다른 소스를 단일 30분 기준으로 처리하지 않는다.

### 5.3 Semantic Sanity Check
- Tier 3 출력물에 원문에 없는 내용 포함 시 즉시 기각

### 5.4 Idempotency
- content_hash 기반 중복 실행 차단
- 시스템 재기동 후에도 동일 데이터 재처리 금지

### 5.5 Cooldown Strike
- 특정 소스 연속 3회 검증 실패 시 1시간 수집 중단

### 5.6 비용 킬스위치 (Cost Kill-Switch)
- Tier 3 일일 API 비용 한도 초과 시 Tier 3 전면 중단

### 5.7 Integrity Preflight
- pipeline 시작 전 DB 핵심 테이블/컬럼, 필수 env, 실제 모델 식별값을 점검한다.
- 무결성 preflight 실패는 경고가 아니라 실행 중단 사유다.
- "나중에 migration으로 고칠 것"은 production batch 실행의 허용 근거가 아니다.

---

## 6. 관측성 (Observability)

- 모든 로그에 correlation_id, tier 번호 필수 포함
- 비동기 로깅 큐, 최대 10,000개 (Drop-oldest)
- 각 Tier별 처리량, 통과율, 비용 메트릭 수집

---

## 7. 보안 규약

- 모든 API 키는 .env 파일에만 보관
- .env는 절대 git 커밋 금지
- 코드 내 API 키 하드코딩 엄금

---

## 8. 하드웨어 역할 분담

| 머신 | 역할 | Tier 담당 |
|------|------|-----------|
| MBP M5 32GB | 개발/테스트 + 로컬 LLM | Tier 2 개발 |
| MBP 2015 16GB | 위험한 실험 전용 | - |
| Mac Mini M4 24GB | 24/7 프로덕션 운영 | Tier 1,2,3,4 |

---

## 9. 환경 및 의존성 규약 (Environment & Dependencies)

- **가상환경 강제:** 모든 Python 프로그램은 프로젝트 루트의 `.venv` 가상환경 내에서 구동되어야 한다.
- **의존성 관리:** 새로운 패키지 설치 시 반드시 가상환경 활성화 후 설치하며, `requirements.txt`를 최신화한다.
- **실행 원칙:** 모든 쉘 명령은 `source .venv/bin/activate && ...` 형식을 취하거나 가상환경의 파이썬 인터프리터를 직접 사용하여 환경 격리를 보장한다.

---

## 10. 도메인 어댑터 현황

| 도메인 | 상태 | 경로 |
|--------|------|------|
| 컨텐츠 큐레이션 | 개발 중 | adapters/content/ |
| (다음 도메인) | 미정 | adapters/TBD/ |
