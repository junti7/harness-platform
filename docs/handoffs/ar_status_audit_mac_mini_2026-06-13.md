# AR Status Audit Hand-off - Mac Mini Harness OS

작성일: 2026-06-13  
작성자: Codex  
점검 대상 환경: Mac Mini production (`juntaepark@100.97.175.44`)  
프로덕션 워킹 디렉터리: `/Users/juntaepark/projects/harness-platform`  
로컬 검토 워킹 디렉터리: `/Users/juntae.park/projects/harness-platform`

## 목적

Mac Mini Harness OS의 "실행요청 현황 (AR현황)"에 표시되는 상태(`진행중`, `보류`, `완료` 등)가 2026-06-13 현재 실제 운영 상태와 맞는지 점검하고, 상태 보정이 필요한 항목을 hand-off로 남긴다.

## 점검 기준

- 원본 AR 트래커: `/Users/juntaepark/projects/harness-platform/docs/reports/ar_tracker.jsonl`
- 상태 정규화 로직: `/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py`
- AR UI 렌더링: `/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/App.tsx`
- Mac Mini launchd 상태: `launchctl list`
- Mac Mini `.env` 및 로그/DB 실측:
  - `/Users/juntaepark/projects/harness-platform/.env`
  - `/Users/juntaepark/projects/harness-platform/logs/tier3-filter.log`
  - `/Users/juntaepark/projects/harness-platform/scripts/budget_revert_check.sh`

## 결론 요약

상태 보정이 필요한 핵심 항목은 아래 4건이다.

1. `AR-046`는 현재 사실과 불일치한다.
2. `AR-046-UPDATE`도 현재 사실과 불일치한다.
3. `AR-044`는 `open`보다 `hold` 또는 `waiting_external` 성격에 가깝다.
4. `AR-053`은 "긴급 차단 상태"는 이미 해소됐으므로 설명 보강이 필요하다.

## 항목별 판정

### 1. AR-046

- AR ID: `AR-046`
- 현재 상태: `open`
- 현재 표기 요지: Gemini cap 초과, OpenAI 패키지 미설치, Claude만 가동
- 판정: `현재 사실과 불일치`

근거:

- 후속 AR에서 OpenAI 패키지 설치가 이미 완료됐다.
  - `/Users/juntaepark/projects/harness-platform/docs/reports/ar_tracker.jsonl`
  - `AR-051`: `completed`
- 후속 검증에서 OpenAI billing 추가 후 `gpt-4o-mini` 라이브 호출 성공이 기록됐다.
  - `/Users/juntaepark/projects/harness-platform/docs/reports/ar_tracker.jsonl`
  - `AR-051-VERIFY`: `completed`
- Mac Mini 현재 `.env`에 `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` 모두 설정돼 있다.
  - `/Users/juntaepark/projects/harness-platform/.env`

권고:

- `AR-046`는 `completed` 또는 최소한 `completed (superseded)` 성격으로 정리하는 것이 맞다.
- 잔여 이슈는 더 이상 "OpenAI 미설치"가 아니라 Gemini cap 문제뿐이며, 이는 `AR-052`로 분리돼 있다.

### 2. AR-046-UPDATE

- AR ID: `AR-046-UPDATE`
- 현재 상태: `open`
- 현재 표기 요지: Anthropic만 가동, OpenAI는 billing 미펀딩
- 판정: `현재 사실과 불일치`

근거:

- `AR-051-VERIFY`에 OpenAI billing 추가와 프로덕션 라이브 검증 완료가 명시돼 있다.
  - `/Users/juntaepark/projects/harness-platform/docs/reports/ar_tracker.jsonl`
- 결과적으로 현재 상태는 "Anthropic만 가동"이 아니라 `Anthropic + OpenAI 가동, Gemini 429 잔존`이다.
- 실제 로그에서도 Gemini 429는 계속 재현되지만, OpenAI 미가동 정황은 현재 hand-off 점검 범위에서 발견되지 않았다.
  - `/Users/juntaepark/projects/harness-platform/logs/tier3-filter.log`

권고:

- `AR-046-UPDATE`는 `completed`로 닫고, 잔여 provider funding/cap 이슈는 `AR-052`만 남기는 편이 맞다.
- 그대로 두면 AR현황에 동일 주제의 stale open 항목이 중복 노출된다.

### 3. AR-044

- AR ID: `AR-044`
- 현재 상태: `open`
- 현재 표기 요지: 외부 익명 트래픽 유입 전까지 PIPA 조치 필요, 현재 실 트래픽 0
- 판정: `상태 표현이 부정확하거나 과하게 활성 상태처럼 보임`

근거:

- 이 항목은 설명 자체가 trigger-gated다. 즉 "지금 즉시 처리 중인 open blocker"보다 `hold` 또는 `waiting_external` 성격이 강하다.
- Mac Mini production DB에는 공개 edu 경로 사용 흔적이 있다.
  - 최근 `edu_cases` 존재
  - 최근 `edu_magic_links` 존재
  - 예: case `60`, magic link 사용 시각 `2026-06-12`
  - DB 접근 워킹 디렉터리: `/Users/juntaepark/projects/harness-platform`
- 따라서 `현재 실 트래픽 0`이라는 표현은 최소한 "생산계 write activity 0" 기준으로는 맞지 않는다.
- 다만 이것이 "실 외부 고객 유입"인지 "내부/테스트 트래픽"인지는 추가 구분이 필요하다.

권고:

- 상태를 `hold` 또는 `waiting_external`로 조정하는 것이 UI 의미상 더 정확하다.
- 설명 문구도 아래처럼 바꾸는 편이 안전하다.
  - 기존: `현재 실 트래픽 0이라 runway 있음`
  - 권고: `현재 공개 경로 사용 이력은 있으나, 외부 실고객 유입 전 PIPA 고지/보존정책/접근통제 확정 필요`

### 4. AR-053

- AR ID: `AR-053`
- 현재 상태: `open`
- 현재 표기 요지: budget 자동 원복 로직 구조 수정 필요
- 판정: `상태 자체는 열려 있어도 되지만, 현재 위험 수준 설명 보강 필요`

근거:

- Mac Mini 현재 `.env` 기준 `DAILY_COST_LIMIT_USD=30.00`으로 이미 수동 원복된 상태다.
  - `/Users/juntaepark/projects/harness-platform/.env`
- 즉 "무제한 고착"이라는 즉시 위험은 현재 시점에는 완화돼 있다.
- 반면 구조적 결함 자체는 여전히 남아 있다.
  - `/Users/juntaepark/projects/harness-platform/scripts/budget_revert_check.sh`
  - 현재도 백로그 기반 단일 조건에 의존
- 실측 백로그는 여전히 크다.
  - `physical=8041`
  - `edu=24508`
  - `pending=0`
- 따라서 "해결 완료"는 아니지만, 운영 화면상으로는 `긴급 진행중`보다 `구조개선 open` 또는 `in_progress` 의미에 가깝다.

권고:

- 상태를 그대로 `open`으로 두더라도 설명 첫 줄에 아래를 추가하는 것이 좋다.
  - `현재 가드레일은 수동 복구됨(DAILY_COST_LIMIT_USD=30.00). 본 AR은 구조개선 미완료 추적용.`
- 가능하면 raw status를 `in_progress`로 명시해 UI에서 `진행중`으로 분리하는 편이 더 낫다.

## 상태 변경 권고안

아래는 가장 보수적인 정리안이다.

| AR ID | 현재 | 권고 | 이유 |
| --- | --- | --- | --- |
| AR-046 | open | completed | OpenAI 미설치/Claude-only 전제가 더 이상 사실이 아님 |
| AR-046-UPDATE | open | completed | OpenAI billing 미펀딩 전제가 AR-051-VERIFY 이후 사실이 아님 |
| AR-044 | open | hold 또는 waiting_external | trigger-gated legal follow-up이며 활성 blocker처럼 보이는 표현이 부정확 |
| AR-053 | open | in_progress 또는 open 유지 + 설명 보강 | 긴급 위험은 해소, 구조개선만 미완료 |
| AR-052 | open | open 유지 | Gemini 429가 2026-06-13 현재 로그로 재현됨 |

## 실제와 맞는 항목

아래는 이번 점검 기준으로 상태 유지가 타당한 항목이다.

- `AR-052`
  - 이유: `/Users/juntaepark/projects/harness-platform/logs/tier3-filter.log` 에 2026-06-13 현재도 Gemini `429 RESOURCE_EXHAUSTED`가 반복 기록됨
- `AR-051`
  - 이유: OpenAI 패키지 설치 및 bootstrap 단일출처화 완료 후 `completed`
- `AR-051-VERIFY`
  - 이유: OpenAI billing 추가 후 Mac Mini 프로덕션 라이브 검증 완료 후 `completed`

## 권장 후속 액션

1. `/Users/juntaepark/projects/harness-platform/docs/reports/ar_tracker.jsonl` 에 `AR-046`, `AR-046-UPDATE` 상태 정정 append row를 추가한다.
2. `AR-044`는 Legal/비서실장 확인 후 `hold` 또는 `waiting_external`로 재분류한다.
3. `AR-053`는 구조개선 전용 AR로 설명을 축약하고, 현재 가드레일 복구 사실을 첫 문장에 반영한다.
4. AR현황 화면에서 stale/superseded AR가 중복 노출되지 않게 운영 규칙을 정한다.
   - 예: 동일 correlation_id의 최신 항목 우선
   - 또는 `superseded_by` 필드 도입

## 참고 메모

- Mac Mini는 최종 프로덕션 환경이므로 상태 판단은 로컬이 아니라 `/Users/juntaepark/projects/harness-platform` 실측을 기준으로 했다.
- 이번 작업에서는 AR 원본 JSONL을 자동 수정하지 않았다. 상태 변경은 운영 판단과 audit trail이 필요하므로 hand-off만 남긴다.
