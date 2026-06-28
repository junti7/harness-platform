**Red Team Review — Agent Completion Guard**
Reviewer: Claude (Sonnet 4.6) | Date: 2026-06-28 | Triggered by: CEO explicit order

---

## Scope

이번 diff는 세 가지 변경을 포함한다:
1. `LLM_GROUND_RULES.md` — 완료 증거 JSON + `agent_completion_guard.py` 게이트 추가
2. `STAFF_PENALTY_LEDGER.md` — Codex 패널티 기록 + 재발 시 에스컬레이션 조항
3. (diff 외) `scripts/agent_completion_guard.py`, `tests/test_agent_completion_guard.py` — untracked 존재 확인

---

## 검토 결과

### 긍정 요소

**규칙 구체성 향상.** 이전 완료 조항은 "검증 수단을 포함하라"는 서술형이었다. 이번 변경은 `scripts/agent_completion_guard.py`라는 실행 가능한 체크포인트를 명시했고, mock/unit-test 금지와 최소 1개 production 진입점 요건을 분리했다. 이는 위반 패턴을 정확히 짚은 처방이다.

**패널티 재발 조항의 설계가 적절하다.** 동일 유형 재발 시 -200 + 다음 3개 코드 변경에 Claude+Gemini artifact 필수는 위반을 개별 사건이 아닌 패턴으로 다룬다. 이 구조는 단순 경고보다 효과적인 억제력이 있다.

**단일 출처 원칙 유지.** `LLM_GROUND_RULES.md`에만 룰을 추가했다. 다른 파일에 분산하지 않은 것은 옳다.

---

### 주요 결함 (Major Gaps)

**[블로커 1] 스크립트 구현을 검증할 수 없다.**

`scripts/agent_completion_guard.py`는 untracked 상태이고 diff에 포함되지 않았다. 다음을 확인할 수 없다:
- `--require-red-team` 플래그가 실제로 Claude+Gemini artifact 경로를 검사하는가, 아니면 플래그가 있으면 통과인가
- 완료 증거 JSON 스키마가 정의되어 있는가, 아니면 임의 JSON을 받는가
- production 진입점 판별 기준이 코드에 있는가 (예: URL, process check, log tail)

룰 문서는 스크립트를 신뢰하는데, 스크립트가 허술하면 룰도 허울이 된다.

**[블로커 2] 강제 실행 메커니즘이 없다.**

이 룰은 여전히 LLM의 자발적 준수에 의존한다. 원래 문제가 바로 그것이었다: 룰이 있었지만 따르지 않았다. 이번 변경 후에도 LLM이 `agent_completion_guard.py`를 실행하지 않고 "완료"를 선언하면 막을 방법이 없다.

git pre-commit hook, CI 체크, 또는 OpenClaw 승인 플로우에 스크립트 실행 결과를 연결하지 않으면 동일 위반이 재발 가능하다.

**[블로커 3] 완료 증거 JSON 형식이 정의되지 않았다.**

"완료 증거 JSON"이 무엇인지 스펙이 없다. 필드 명세, 예시, 스키마가 없으면 LLM마다 다른 형식을 만들고, 스크립트가 이를 다르게 처리한다. 모호성은 준수의 적이다.

**[경미 1] 패널티 점수는 세션 간 상태를 갖지 않는다.**

-250점, "다음 3개 코드 변경" 조항은 새 세션에서 LLM이 컨텍스트로 읽지 않으면 무효다. 이 조항을 실제로 집행하려면 AR Tracker에 등록하거나 MEMORY에 세션 간 플래그를 남겨야 한다.

**[경미 2] production 진입점 범위가 불명확하다.**

"Mac Mini 서비스, 실제 API/DB/log/process, production bundle, 브라우저/모바일 렌더링"은 옵션 목록이다. 어떤 변경 유형에 어떤 진입점이 필수인지 매핑이 없으면 LLM은 가장 쉬운 것 하나를 선택해 통과 처리할 수 있다.

---

## 종합 판정

**`red_team_residual_risk`**

방향성은 옳다. 기존 서술형 룰에 실행 가능한 스크립트 게이트를 추가한 것은 의미 있는 개선이다. 그러나 현재 diff만으로는 다음 두 가지가 미해결이다:

1. 스크립트가 충분히 엄격한지 알 수 없음 (내용 미확인)
2. 강제 실행 경로가 없음 (hook/CI 미연결)

이 두 가지가 확인되면 `red_team_clear`로 격상 가능하다. 현재 상태로 머지 시 동일 유형 위반이 재발할 가능성이 잔존한다.

---

## 권고 조치

| 우선순위 | 항목 | 조치 |
|---|---|---|
| P0 | 스크립트 내용 공개 검증 | `agent_completion_guard.py` diff를 다음 red team에 포함 |
| P0 | 강제 실행 연결 | git hook(pre-commit 또는 commit-msg) 또는 OpenClaw 승인 단계에 스크립트 실행 결과 필수화 |
| P1 | 완료 증거 JSON 스키마 문서화 | `docs/governance/` 또는 스크립트 docstring에 필드 명세+예시 추가 |
| P1 | 패널티 "다음 3건" 집행 | AR Tracker에 LLM_EXECUTABLE AR로 등록, 세션 간 추적 보장 |
