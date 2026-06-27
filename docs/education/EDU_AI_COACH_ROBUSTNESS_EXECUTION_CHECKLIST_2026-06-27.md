# EDU AI Coach Robustness Execution Checklist

> 작성일: 2026-06-27
> 목적: `EDU_AI_COACH_DIGITAL_TWIN_ROBUSTNESS_PLAN_2026-06-27.md`를 실제 repo artifact와 검증 루프로 순차 실행한다.

---

## 0. Ground Rules

- Codex CLI 사용 시 caveman full 응답 규칙을 적용하되, 코드 변경 요약은 정확하게 유지한다.
- 기존 `EDU_SIMULATION_GATING.md`는 UX/security/product gate다. 이 체크리스트는 AI 코치 답변 품질 gate다.
- 세 gate 중 하나라도 `block`이면 release/확장 판정은 `block`.
- Case-by-case 답변 하드코딩이 아니라 intent, constraint, failure, policy, twin, scenario artifact를 축적한다.

---

## 1. Phase 0 Checklist

| ID | Task | Artifact | Status |
| --- | --- | --- | --- |
| P0-1 | 현재 실패 유형을 failure taxonomy로 고정 | `configs/education/edu_coach_policy_registry.json` | done |
| P0-2 | seed policy 5개 생성 | `professional_cost_barrier`, `ai_energy_use`, `emotional_validation`, `isolation_dependency`, `principle_question` | done |
| P0-3 | 24개 seed twin 생성 | `configs/education/edu_digital_twins.json` | done |
| P0-4 | scenario matrix 생성 | `configs/education/edu_coach_scenarios.json` | done |
| P0-5 | 20개 이상 gold-set seed 생성 | `docs/reviews/edu_coach_simulations/gold_set_seed_2026-06-27.jsonl` | done |
| P0-6 | offline deterministic runner 생성 | `scripts/edu_coach_simulation_runner.py` | done |
| P0-7 | runner unit test 생성 | `tests/test_edu_coach_simulation_runner.py` | done |

---

## 2. Phase 1 MVP Checklist

| ID | Task | Artifact | Status |
| --- | --- | --- | --- |
| P1-1 | current fallback 답변 대상으로 simulation 실행 | `docs/reviews/edu_coach_simulations/run_*.jsonl` | done |
| P1-2 | latest summary 생성 | `docs/reviews/edu_coach_simulations/latest.json`, `latest.md` | done |
| P1-3 | known bad/good gold-set을 deterministic gate에 통과시켜 calibration sanity check | runner `--candidate-source gold-set` | done |
| P1-4 | 500개 question variant 생성 | scenario mutation 확장 | next |
| P1-5 | top failure cluster report 생성 | failure cluster markdown | next |

---

## 3. Phase 2 Checklist

| ID | Task | Artifact | Status |
| --- | --- | --- | --- |
| P2-1 | runtime policy resolver를 backend 코드에 분리 구현 | edu safety coach service module | done |
| P2-2 | answer generator가 policy registry를 직접 읽도록 연결 | backend integration | done |
| P2-3 | downvote review가 policy candidate artifact를 생성하도록 확장 | policy promotion queue | done |
| P2-4 | LLM judge strict schema 추가 | judge worker | done |
| P2-5 | judge-vs-human agreement 측정 | gold-set calibration report | next |

---

## 4. Phase 3 Checklist

| ID | Task | Artifact | Status |
| --- | --- | --- | --- |
| P3-1 | scheduled durable downvote reprocessor 등록 | launchd/cron or app scheduler | next |
| P3-2 | downvoted answer cache invalidation을 event와 연결 | backend cache path | next |
| P3-3 | admin review dashboard/report 생성 | admin API/report | next |
| P3-4 | QA/Red Team/Legal/CoS approval artifact 연결 | governance records | next |

---

## 5. Done Definition

최소 완료 조건:

- seed artifacts가 repo에 존재한다.
- runner가 LLM/API 없이 재현 가능하게 실행된다.
- known bad answer는 `needs_work` 또는 `block`으로 잡힌다.
- current fallback answer는 seed case에서 `clear`를 목표로 검증된다.
- 실행 결과가 JSONL + latest summary로 남는다.
- 구현 전/후 상태를 커밋 단위로 추적한다.
