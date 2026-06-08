# Hand-off — Edu Pilot / Parents First

Date: 2026-06-08  
Context: `부모 AI 자가점검 (1호 파일럿)`의 현재 구현 상태를 진단했고, 다른 LLM이 바로 코드 수정에 들어갈 수 있도록 상태/재현 경로/우선순위를 정리한다.

## 1. 이번 턴에서 새로 추가된 것

### Added
- `configs/edu_pilot_simulations.json`
- `scripts/run_edu_pilot_simulations.py`
- `tests/test_edu_pilot_simulations.py`
- `docs/reviews/edu_pilot_simulations/edu_pilot_diagnosis_2026-06-08.md`

### Purpose
- live API를 직접 치는 고객 시뮬레이션 baseline
- 개선 전/후 점수 비교 가능한 reusable regression harness
- customer dissatisfaction를 추상 평가가 아니라 transcript + score로 남기기

## 2. 현재 제품 구조

### Frontend
- public app: `harness-os/frontend/public/edu-pilot-app.html`
- internal tester page: `harness-os/frontend/src/pages/EduPilotPage.tsx`

### Backend
- `harness-os/backend/main.py`
  - `/api/public/edu/bootstrap`
  - `/api/public/edu/diagnose`
  - `/api/public/edu/curriculum`
  - `/api/public/edu/resume`
  - `/api/public/edu/magic-link/consume`
  - internal magic link test create route

### Persistence
- migration: `infra/migrations/2026-06-02_edu_case_persistence.sql`
- tables:
  - `edu_customers`
  - `edu_cases`
  - `edu_case_turns`
  - `edu_magic_links`

### Evidence / RAG
- `data/edu_research/evidence_bank.json`
- `data/edu_research/evidence_index.json`
- builders:
  - `scripts/refresh_edu_evidence_bank.py`
  - `scripts/build_edu_evidence_index.py`

### Naver collection
- `scripts/collect_naver_community.py`
- uses official Naver Search API
- sources:
  - `Naver_카페글`
  - `Naver_지식iN`
  - `Naver_블로그`

## 3. 운영 상태 진단 핵심

### 실제 운영 DB facts
`harness_prod` 기준:
- raw_signals `edu_consulting`: `30455`
- top raw sources:
  - `Naver_블로그` `11308`
  - `Naver_카페글` `10272`
  - `Naver_지식iN` `8426`
- refined_outputs:
  - `Naver_카페글` `6117`
  - `Naver_지식iN` `3518`
  - `Naver_블로그` `179`

즉 Naver는 양적으로 충분히 들어온다.

### 문제
1. quantity는 충분하지만 answer voice에 잘 녹지 않는다.
2. refined sample이 generic/SEO-like 상담문으로 평탄화된다.
3. `evidence_bank.json`은 얇고 Naver community realism이 약하다.
4. `evidence_index.json`은 noisy YouTube가 많이 섞여 retrieval precision이 떨어진다.
5. worker/job seeker segment는 live timeout이 난다.
6. salutation enum leak (`네, father.`)가 실제 transcript에서 확인됐다.

## 4. Live simulation baseline

Generated reports:
- `docs/reviews/edu_pilot_simulations/edu_pilot_simulations_2026-06-08_150536.json`
- `docs/reviews/edu_pilot_simulations/edu_pilot_simulations_2026-06-08_150707.json`
- `docs/reviews/edu_pilot_simulations/edu_pilot_simulations_2026-06-08_150809.json`
- `docs/reviews/edu_pilot_simulations/edu_pilot_simulations_2026-06-08_150838.json`
- `docs/reviews/edu_pilot_simulations/edu_pilot_simulations_2026-06-08_151020.json`

Representative results:

| Scenario | Score | Notes |
| --- | ---: | --- |
| parent_father_middle_school_homework | 94 | transcript itself revealed enum leak: `네, father.` |
| parent_neutral_highschool_career_major | 91 | core chat works, `next_steps` timed out |
| parent_mother_elementary_screen_dependence | 72 | robotic authority phrasing + weak grounding feel |
| worker_female_job_seeker | 0 | scenario failed: `ReadTimeout` |
| worker_male_office_worker_lagging | 0 | scenario failed: `ReadTimeout` |

### Important nuance
`run_edu_pilot_simulations.py` was hardened to continue when a scenario times out.
Before that change, full-suite runs died mid-run.

### P0 patch status
This turn applied a narrow production patch in `harness-os/backend/main.py`:
- prompt salutation now receives natural-language guidance instead of raw enum
- worker and curriculum prompts were shortened
- retrieval `k` and history budget were reduced for slow paths
- simulation harness now supports `--mode internal` with dashboard secret header
- runtime events are now logged to `runtime/edu_pilot_runtime_events.jsonl`
- evidence builders now classify `source_kind`
- retrieval now tries to mix `community_voice` and `research_policy` instead of pure cosine top-k
- low-quality entertainment-style YouTube items are filtered at evidence-layer time

Observed after patch:
- `429` public rate-limit failures are gone in internal simulation mode
- worker/job seeker scenarios no longer hard-timeout
- `next_steps` timeout was reduced
- but many scenarios now end in persona fallback text, so quality is still not where it should be

Observed after second pass:
- internal simulation average score is now `72.83`
- runtime event log shows a large share of worker fallback is currently caused by `429 RESOURCE_EXHAUSTED` from Gemini
- old `evidence_index.json` items often lack `source_kind`, so backend now lazy-infers it at retrieval time
- because quota exhaustion is now visible, future quality work must separate:
  1. retrieval/source-quality issues
  2. provider quota/availability issues

Observed after third pass:
- `edu diagnose/curriculum` now has provider fallback ladder
  - primary: Gemini
  - fallback: Claude
  - OpenAI only if package + key are both available
- `source_name/source_kind/segment` metadata is now backfilled across existing index items without re-embedding
- fresh bank quota now prefers `community_voice`
- single-scenario remote smoke (`worker_female_job_seeker`) still scores `71`, but runtime events now clearly show:
  - source mix is better
  - provider fallback attempts are visible
  - remaining failures are mostly provider-side, not hidden retrieval failures

Representative post-patch scores:
- `parent_father_middle_school_homework`: `73`
- `parent_neutral_highschool_career_major`: `68`
- `worker_female_job_seeker`: `71`
- `worker_male_office_worker_lagging`: `71`

Interpretation:
- system stability improved
- answer quality regressed into safe fallback mode too often
- next fix should focus on why `_run_edu_diagnose` / `_run_edu_curriculum` still fail and fall back even after prompt slimming

### Current simulation limitation
Full suite against live Mac Mini can still be slow enough that running all scenarios in one process is operationally awkward.
Single-scenario runs are stable enough to diagnose baseline.
If needed, split the suite into:
- `parent-core`
- `parent-extended`
- `worker`

## 5. What to fix first

### P0 — immediate
1. **Fix salutation enum leak**
   - somewhere in the prompt/render pipeline, `father/mother/neutral/name` is leaking into natural language.
   - repro transcript exists in `edu_pilot_simulations_2026-06-08_150536.json`

2. **Stabilize worker/job seeker path**
   - repro:
     ```bash
     PYTHONPATH=. .venv/bin/python scripts/run_edu_pilot_simulations.py --scenario worker_female_job_seeker --base-url http://100.97.175.44:8000 --timeout 20
     ```
   - current evidence from runtime log:
     - worker path still often fails due Gemini `429 RESOURCE_EXHAUSTED`
   - likely remaining causes:
     - provider quota exhaustion
     - segment mismatch in retrieval corpus
     - too many `general_reference` items and not enough clean `community_voice`

3. **Reduce `next_steps` timeout risk**
   - high-school career scenario hits this repeatedly
   - likely easiest fixes:
     - trim history harder
     - cut evidence count
     - separate shorter prompt for `next_steps`

### P1 — answer quality
4. **Split community voice from research voice**
   - current pipeline mixes them, producing generic “consultant article” language
   - recommended:
     - `parent_voice_bank`
     - `research_policy_bank`

5. **Tighten Naver precision**
   - current raw Naver sample contains:
     - study café chatter
     - academy/marketing noise
     - non-parent generic posts
   - Tier 2 is not removing enough

6. **Source quota in evidence index**
   - cap irrelevant/noisy YouTube dominance
   - force minimum representation for:
     - Naver cafe
     - Naver kin
     - Naver blog

7. **Make source_kind durable in full corpus**
   - current backend has lazy inference for legacy items
   - next rebuild step should persist `source_kind` across the full index, not only new items

8. **Add provider fallback / queueing for edu diagnose**
   - until quota exhaustion is handled, simulation scores will keep being capped by fallback quality

### P2 — product scope
9. **Decide whether worker/job seeker stays public**
   - current code exposes both `parent` and `worker`
   - if worker stays unstable, consider hiding it until fixed

## 6. High-signal files to inspect next

### Core generation path
- `harness-os/backend/main.py`
  - `_run_edu_diagnose`
  - `_run_edu_curriculum`
  - `_retrieve_evidence`
  - `_retrieve_evidence_indexed`
  - `_edu_build_opener`

### Evidence builders
- `scripts/refresh_edu_evidence_bank.py`
- `scripts/build_edu_evidence_index.py`

### Collection / source quality
- `scripts/collect_naver_community.py`

## 7. Recommended debugging path

### A. Reproduce salutation leak
1. Historical repro existed before this patch:
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/run_edu_pilot_simulations.py --scenario parent_father_middle_school_homework --base-url http://100.97.175.44:8000 --mode internal --timeout 20
   ```
2. The raw enum leak appears fixed by natural-language salutation hints.
3. Keep the regression scenario; do not remove it.

### B. Reproduce worker timeout
1. Run:
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/run_edu_pilot_simulations.py --scenario worker_female_job_seeker --base-url http://100.97.175.44:8000 --mode internal --timeout 20
   ```
2. Current state: timeout is mostly gone, but fallback is frequent.
3. Next debugging target:
   - read `runtime/edu_pilot_runtime_events.jsonl`
   - separate `provider quota failure` vs `JSON parse failure` vs `commercial/fabrication regeneration loop`
   - log evidence source_kind mix at failure

### C. Improve Naver realism
1. Sample latest raw `Naver_카페글` / `Naver_지식iN`
2. Add early precision rules:
   - source_detail denylist
   - title/description intent heuristics
   - parent/worker relevance cues
3. Preserve short authentic snippets before refined rewrite stage.

## 8. Simulation process — how to reuse

Config:
- `configs/edu_pilot_simulations.json`

Script:
- `scripts/run_edu_pilot_simulations.py`

Tests:
- `tests/test_edu_pilot_simulations.py`

Outputs:
- timestamped JSON/MD under `docs/reviews/edu_pilot_simulations/`
- `latest.json`
- `latest.md`

Scoring currently covers:
- naturalness
- personalization
- grounding feel
- conversion readiness
- wrong salutation
- enum leak
- repeated template voice
- weak actionability
- scenario/runtime timeout

## 9. Important interpretation rule

Do not over-read the high parent scores.

`94` / `91` here do **not** mean the product is production-grade.
They mean:
- the transcript completed
- personalization heuristics fired
- major runtime failure did not happen

The broader diagnosis still stands:
- Naver realism is weak
- worker segment is unstable
- `next_steps` latency is a real product risk

## 10. Safe change boundaries

This turn intentionally did **not** modify production edu prompt/backend behavior.
Only reusable simulation and diagnosis artifacts were added.

If you continue from here:
- keep edits scoped to edu pilot files
- do not mix with unrelated dirty repo changes
- preserve simulation script/config so future delta measurement remains comparable
