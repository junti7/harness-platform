# Collection Scope Handoff — 2026-06-03

Date: 2026-06-03  
Project: `harness-platform`  
Scope: `education + physical_ai collection broadening`, `topic clustering`, `push briefs`, `Mac Mini deployment`

## Objective

이 작업의 목적은 수집 범위를 편협한 채널/키워드 중심에서 벗어나:

- 교육:
  - 부모
  - 직장인
  - 취준생
  - 군복무
  - 진로/전공
  - 디지털 의존
- 기술:
  - embodiment robotics
  - memory/packaging
  - networking/optics
  - power/cooling
  - simulation/software
  - warehouse/deployment

까지 다루는 구조로 넓히고, 이 범위가 실제로 수집/필터링/대시보드/Push 후보에 연결되게 만드는 것이다.

---

## Commit

로컬 git commit:

- `33c7605 feat(collection): harden topic-first discovery and cluster monitoring`

주의:

- 원격 Mac Mini 저장소는 로컬보다 다른 커밋 이력이 앞서 있어서 `git push`로는 배포하지 않았다.
- 대신 **이번 작업 파일만 `rsync`로 동기화**해서 배포했다.
- 따라서 **로컬 git commit 상태와 원격 working tree 반영 상태를 동일시하면 안 된다**.

---

## What Changed

### 1. Edu collection broadened from narrow AI mentions to topic-first discovery

핵심 파일:

- [scripts/run_edu_deep_research.py](/Users/juntae.park/projects/harness-platform/scripts/run_edu_deep_research.py)
- [configs/sources/edu_consulting.json](/Users/juntae.park/projects/harness-platform/configs/sources/edu_consulting.json)

핵심 변경:

- YouTube 수집을 `채널 whitelist-first`에서 `topic-first discovery`로 이동
- `yt-dlp` 기반 metadata-only discovery 경로 추가
- `YouTube Data API`는 기본 비활성화
- RSS도 `topic_cluster`를 붙이도록 변경

현재 교육 cluster:

- `parenting_ai`
- `worker_ai`
- `job_seeker_ai`
- `military_ai`
- `career_major`
- `digital_dependence`
- fallback `general_ai_education`

추가된 주제 축:

- 부모/자녀 AI
- 직장인 AI 활용
- 취준생 AI 역량/불안
- 군복무/입대 준비
- 진로/전공/미래 직업
- 스마트폰/디지털 의존

### 2. Physical AI broadened beyond robots/chips into infra bottlenecks

핵심 파일:

- [configs/keywords/physical_ai.json](/Users/juntae.park/projects/harness-platform/configs/keywords/physical_ai.json)
- [configs/sources/physical_ai.json](/Users/juntae.park/projects/harness-platform/configs/sources/physical_ai.json)
- [core/topic_registry.py](/Users/juntae.park/projects/harness-platform/core/topic_registry.py)
- [adapters/content/collector.py](/Users/juntae.park/projects/harness-platform/adapters/content/collector.py)
- [adapters/content/signalizer.py](/Users/juntae.park/projects/harness-platform/adapters/content/signalizer.py)

추가된 기술 축:

- `memory_packaging`
- `networking_optics`
- `power_cooling`
- `simulation_software`
- `warehouse_deployment`
- `edge_realtime`
- `compute_models`
- `embodiment_robotics`

즉 이제는 `로봇 본체 + GPU`만 보는 구조가 아니라, 실제 투자/사업 병목인 전력/냉각/패키징/네트워킹/시뮬레이션까지 본다.

### 3. Tier 2 relevance now uses cluster bonus

핵심 파일:

- [adapters/content/filter.py](/Users/juntae.park/projects/harness-platform/adapters/content/filter.py)

핵심 변경:

- `compute_cluster_bonus()` 추가
- `topic_cluster`를 relevance score에 직접 반영

의미:

- broad discovery로 들어온 row가 seed keyword hit만으로 조기에 탈락하는 문제를 줄였다.

### 4. Dashboard now exposes clusters and push candidates

핵심 파일:

- [harness-os/backend/main.py](/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py)
- [harness-os/frontend/src/components/DataCollectionMonitor.tsx](/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/components/DataCollectionMonitor.tsx)
- [harness-os/frontend/src/components/types.ts](/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/components/types.ts)

추가된 UI/API:

- `기술 테마 클러스터`
- `교육 테마 클러스터`
- `기술 Push 후보`
- `교육 Push 후보`

추가 API 변화:

- `/api/pipeline/signals`는 `edu_consulting` rows에 대해 `topic_cluster`를 노출

### 5. Topic push brief automation added

핵심 파일:

- [scripts/summarize_topic_push_brief.py](/Users/juntae.park/projects/harness-platform/scripts/summarize_topic_push_brief.py)
- [scripts/register_openclaw_cron_jobs.sh](/Users/juntae.park/projects/harness-platform/scripts/register_openclaw_cron_jobs.sh)

추가 cron:

- `harness-daily-topic-push-brief`
- 매일 `06:10 KST`
- route: `#exec-president-decisions`

### 6. Collection scope audit added

핵심 파일:

- [scripts/audit_collection_scope.py](/Users/juntae.park/projects/harness-platform/scripts/audit_collection_scope.py)
- [docs/reviews/collection_scope_audit/collection_scope_audit_2026-06-03.md](/Users/juntae.park/projects/harness-platform/docs/reviews/collection_scope_audit/collection_scope_audit_2026-06-03.md)

용도:

- 현재 설정이 정말 부모/직장인/취준생/군복무/진로, 그리고 기술 인프라 병목을 커버하는지 점검

---

## Important Correction Made Late In The Turn

사용자 지시:

- `"부동산, 경매, 재건축, 재개발"`은 공공데이터 수집에서 투자 관련 아이템이 될 수 있으므로 제거하면 안 됨

정정 파일:

- [adapters/content/collector.py](/Users/juntae.park/projects/harness-platform/adapters/content/collector.py)

최종 상태:

- `target_keywords`에 포함:
  - `부동산`
  - `경매`
  - `재건축`
  - `재개발`
  - `공매`
  - `상권`
  - `토지`
  - `주택`
- `low_signal_terms`에는 포함되지 않음
- 현재 low signal only:
  - `민원`
  - `공원`
  - `관광`
  - `복지`

중요:

- 원격 Mac Mini에는 한 번 잘못된 버전이 남아 있었고,
- 배포 검증 중 잡아서 `collector.py`만 다시 `rsync`로 덮고 재기동했다.

---

## Deployment Status

배포 대상:

- Mac Mini host: `juntaepark@192.168.0.203`

배포 방식:

- `git push` 실패
  - remote `main`이 로컬보다 앞선 다른 커밋 포함
- 그래서 이번 작업 파일만 `rsync`로 동기화

원격에서 수행한 것:

1. 대상 파일 sync
2. `python3 -m py_compile` 검증
3. frontend build
4. OpenClaw cron 재등록
5. launchd plist 교체
6. 관련 서비스 kickstart

확인된 상태:

- `com.harness.harness-os-backend` running
- `com.harness.2026-ai-seamless-gather` running
- frontend dist rebuilt at `2026-06-03 16:22 KST`

---

## Known Operational Caveat

원격 repo 상태:

- `main` branch는 별도 merge commit과 local-only 수정이 섞여 있음
- 즉, 다음 작업자는 **원격에서 git pull/reset/rebase를 함부로 하면 안 된다**

권장:

- 원격 변경이 필요한 경우 먼저 `git status`와 관련 파일 diff를 확인
- 안전한 경우에만 cherry-pick / rsync / selective patch 사용

---

## How To Feel The Change

사용자 질문에 대한 실무적 답:

### 1. Dashboard

- `http://100.97.175.44:8000/`
- `데이터 수집 파이프라인`

체감 포인트:

- 단순 수집량이 아니라 `무슨 주제가 들어오고 있는지`가 보임
- 교육/기술 모두 cluster 기반으로 보임
- Push 후보가 주제별로 따로 보임

### 2. Logs

파일:

- `logs/2026-ai-seamless-gather.log`

체감 포인트:

- 예전처럼 channel crawl 중심이 아니라
  - `YouTube Topic Discovery (Primary Method)`
  - `max_topic_queries=18`
  - `max_channel_crawls=0`
  식으로 topic-first run이 보임
- `Requested format is not available` 오류가 줄어든다

### 3. Scope audit report

- [collection_scope_audit_2026-06-03.md](/Users/juntae.park/projects/harness-platform/docs/reviews/collection_scope_audit/collection_scope_audit_2026-06-03.md:1)

체감 포인트:

- 현재 수집 설정이 어떤 축을 포함하는지 문서로 확인 가능

---

## Files Touched In This Iteration

- [adapters/content/collector.py](/Users/juntae.park/projects/harness-platform/adapters/content/collector.py)
- [adapters/content/filter.py](/Users/juntae.park/projects/harness-platform/adapters/content/filter.py)
- [adapters/content/signalizer.py](/Users/juntae.park/projects/harness-platform/adapters/content/signalizer.py)
- [configs/keywords/physical_ai.json](/Users/juntae.park/projects/harness-platform/configs/keywords/physical_ai.json)
- [configs/sources/edu_consulting.json](/Users/juntae.park/projects/harness-platform/configs/sources/edu_consulting.json)
- [configs/sources/physical_ai.json](/Users/juntae.park/projects/harness-platform/configs/sources/physical_ai.json)
- [core/topic_registry.py](/Users/juntae.park/projects/harness-platform/core/topic_registry.py)
- [harness-os/backend/main.py](/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py)
- [harness-os/frontend/src/components/DataCollectionMonitor.tsx](/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/components/DataCollectionMonitor.tsx)
- [harness-os/frontend/src/components/types.ts](/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/components/types.ts)
- [launchd/com.harness.2026-ai-seamless-gather.plist](/Users/juntae.park/projects/harness-platform/launchd/com.harness.2026-ai-seamless-gather.plist)
- [scripts/register_openclaw_cron_jobs.sh](/Users/juntae.park/projects/harness-platform/scripts/register_openclaw_cron_jobs.sh)
- [scripts/run_edu_deep_research.py](/Users/juntae.park/projects/harness-platform/scripts/run_edu_deep_research.py)
- [scripts/audit_collection_scope.py](/Users/juntae.park/projects/harness-platform/scripts/audit_collection_scope.py)
- [scripts/summarize_topic_push_brief.py](/Users/juntae.park/projects/harness-platform/scripts/summarize_topic_push_brief.py)
- [docs/reviews/collection_scope_audit/collection_scope_audit_2026-06-03.md](/Users/juntae.park/projects/harness-platform/docs/reviews/collection_scope_audit/collection_scope_audit_2026-06-03.md)

---

## Recommended Next Steps

1. `physical_ai` legacy raw에 남은 `general_physical_ai` 비중을 second-pass reclustering으로 더 줄이기
2. `topic_cluster` 기준 KPI를 대시보드에 추가
   - raw count
   - pass rate
   - signal promotion rate
3. topic push brief가 실제 운영상 유효한지 3~5일 관찰
4. 원격 repo drift를 정리할 안전한 배포 루틴 설계
   - selective cherry-pick
   - deployment branch
   - rsync manifest

---

## One-Line State

이번 턴 기준으로 수집 구조는 `좁은 채널 의존`에서 `topic-first + cluster-aware monitoring`으로 이동했고, Mac Mini에는 다른 변경을 크게 건드리지 않는 방식으로 선택 배포까지 끝난 상태다.
