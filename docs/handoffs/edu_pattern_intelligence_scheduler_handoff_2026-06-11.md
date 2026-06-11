# Edu Pattern Intelligence Scheduler Handoff

Date: 2026-06-11  
Author: Codex  
Current code head: `fdd7bfe`

## Current State

`Edu Pattern Intelligence`는 현재 전용 `cron` 또는 전용 `launchd` 잡으로 백그라운드 정기 실행되지 않는다.

현재 갱신 구조는 두 층이다.

1. 상위 edu 데이터 수집/정제
- `com.harness.edu-daily` LaunchAgent가 매일 `10:30`에 실행된다.
- Mac Mini 실측 기준 `launchctl print gui/$(id -u)/com.harness.edu-daily`에서 로드 상태와 calendar trigger가 확인됐다.
- `last exit code = 0`, `runs = 6` 확인.

2. 패턴 인텔리전스 산출
- Harness OS의 `/api/edu/pattern-intelligence` 호출 시 backend가 artifact 존재 여부와 최근 실행 시각을 확인한다.
- 최근 실행 후 `300초` 초과 시에만 `scripts/build_edu_pattern_intelligence.py` + `scripts/fact_check_edu_patterns.py`를 다시 실행한다.
- frontend는 화면이 열려 있으면 `45초`마다 poll한다.
- 따라서 현재 구조는 “항상 백그라운드에서 정기 스캔”이 아니라 “화면/API 접근 기반 재계산 + 5분 refresh guard”다.

## Verified Facts

### Backend refresh interval
- File: [harness-os/backend/main.py](/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py:5479)
- `_EDU_PATTERN_REFRESH_INTERVAL_SEC = 300.0`

### Edu daily launchd
- File: [harness-os/launchd/com.harness.edu-daily.plist](/Users/juntae.park/projects/harness-platform/harness-os/launchd/com.harness.edu-daily.plist:26)
- Schedule: daily `10:30`

### Edu tier3 refine
- File exists: [harness-os/launchd/com.harness.edu-tier3-refine.plist](/Users/juntae.park/projects/harness-platform/harness-os/launchd/com.harness.edu-tier3-refine.plist:34)
- But Mac Mini 실측에서는 `NOT_LOADED`
- 즉 정의만 있고 실제 운영 등록은 안 되어 있다.

### Cron status on Mac Mini
- `crontab -l`에는 `IBKR Turtle Monitor`만 있다.
- `Edu Pattern Intelligence` 관련 cron entry는 없다.

## Why This Matters

현재 관제 UX는 많이 좋아졌지만, 대표가 화면을 열지 않으면 `edu_pattern_intelligence.json`과 `edu_pattern_fact_check.json`은 자동으로 자주 갱신되지 않는다.

즉 지금 상태는:
- data collection은 daily launchd에 의존
- pattern intelligence artifact는 on-demand refresh에 의존

이 구조는 “관제 화면” 용도로는 작동하지만, “항상 최신 intelligence artifact가 background에서 준비돼 있어야 한다”는 운영 목표에는 아직 부족하다.

## Recommended Next Task

전용 LaunchAgent를 추가해 `Edu Pattern Intelligence`를 정기 background rebuild 하도록 만든다.

권장 label:
- `com.harness.edu-pattern-intelligence`

권장 동작:
- `scripts/build_edu_pattern_intelligence.py --write`
- `scripts/fact_check_edu_patterns.py --write`
- optional: refresh audit log append

권장 주기:
- 30분 또는 60분
- 초기 추천: `StartInterval = 1800`

이유:
- 현재 artifact는 작고 계산 비용도 제한적이다.
- 5분은 과하다.
- 1일 1회는 complaint/usage drift 추적에 너무 느리다.
- 30분은 운영 관측성과 비용 사이의 타협점이다.

## Exact Implementation Proposal

1. 새 plist 추가
- path: `harness-os/launchd/com.harness.edu-pattern-intelligence.plist`

2. wrapper script 추가
- path: `scripts/run_edu_pattern_intelligence_refresh.sh`
- 역할:
  - repo root 이동
  - `.venv` python 사용
  - `build_edu_pattern_intelligence.py --write`
  - `fact_check_edu_patterns.py --write`
  - stdout/stderr를 dedicated log로 기록

3. launchd registration flow에 포함
- file: `harness-os/scripts/register_launchd.sh`
- 새 label을 register list에 추가

4. Mac Mini registration verification
- `launchctl list | grep com.harness.edu-pattern-intelligence`
- `launchctl print gui/$(id -u)/com.harness.edu-pattern-intelligence`
- log paths 확인

5. Harness OS observability 추가
- 가능하면 `/api/edu/pattern-intelligence` payload에
  - `scheduler.label`
  - `scheduler.loaded`
  - `scheduler.last_run`
  - `scheduler.log_path`
  를 노출

## Secondary Task

`com.harness.edu-tier3-refine`가 plist는 있는데 Mac Mini에 로드되어 있지 않으므로, 다음 작업에서 함께 판단 필요.

선택지:

1. 실제 필요하면 같이 등록
- edu raw -> refine -> rag pipeline completeness 강화

2. 불필요하거나 미완성이면 제거
- 존재하지만 안 쓰는 스케줄 정의는 운영 혼선을 만든다

## Validation Checklist For Next Agent

- `git status --short` 로컬/Mac Mini 둘 다 clean 확인 후 시작
- plist 추가 후 `plutil -lint`
- wrapper script `bash -n`
- Mac Mini 선택 배포
- Mac Mini에서 `launchctl bootstrap` 또는 기존 등록 스크립트로 로드
- `launchctl print`로 trigger 확인
- log file 생성 확인
- artifact `generated_at`가 주기적으로 갱신되는지 두 번 이상 확인
- 마지막에 로컬/Mac Mini 둘 다 clean 확인

## Current UX/Artifact Context

현재 관제 화면은 이미 아래를 지원한다.

- raw → scanned → linked → extracted fact 퍼널
- source별 excluded sample 예시
- included sample 원문 drill-down
- excluded sample 원문 drill-down
- fact-check / red-team artifact 링크
- history 기반 trend

따라서 다음 작업의 핵심은 UX 추가가 아니라 “background scheduler를 붙여 최신성이 보장되게 만드는 것”이다.

