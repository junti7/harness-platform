# EDU Safety Coach Question Eligibility Handoff - 2026-06-28

## Operating Rule

Codex CLI 사용 시 caveman full 응답 규칙을 적용하되, 코드 변경 요약은 정확하게 유지한다.

This handoff is for a fresh start after the EDU safety coach RAG/source/formatting and `question_not_addressed` reduction work.

## Current Repo State

- Workspace: `/Users/juntae.park/projects/harness-platform`
- Branch: `main`
- Latest observed HEAD before handoff creation: `5cb3b95`
- EDU safety coach main commits:
  - `56bf294 fix: classify edu safety coach answerable questions`
  - `fc1dadf docs: update edu safety coach deployment evidence`

## What Changed

The safety coach now separates inputs before judging/answering:

- `real_user_question`: answer normally and evaluate answer quality.
- `source_snippet`: source fragments, pasted corpus snippets, wrapper text like `이런 상황이면 어떻게 해야 해요? ...` when it is not a real user question.
- `article_title`: paper/news/title-like inputs.
- `ad_event_noise`: event, 모집, 신청, contact/link noise.
- `too_ambiguous`: too short or missing enough context.
- `out_of_scope`: not about AI/learning/child/screen/career coaching.

Runtime endpoint change:

- Endpoint: `POST /api/edu/vp-training/safety-coach`
- Non-eligible inputs return `model="input-clarifier"`, `evidence_used=false`, `fallback_used=true`, and a clarification answer instead of a fabricated generic answer.

Core files changed:

- `harness-os/backend/main.py`
  - Added `_edu_vp_safety_coach_input_category`.
  - Added `_edu_vp_safety_coach_clarification_answer`.
  - Added runtime clarification path.
  - Added broader fallback branches for common parent AI/learning intents.
  - Expanded answer-intent detection for evaluation.
- `scripts/evaluate_edu_safety_coach_available_questions.py`
  - Uses the same backend input category split.
  - Separates `answer_quality_eligible` from skipped non-user inputs.
  - Keeps RAG/source/markdown hard gates on all relevant candidates.
- `scripts/edu_coach_simulation_runner.py`
  - Uses the same input eligibility split for corpus/adversarial current fallback simulation.
- `tests/test_edu_vp_training_flow.py`
  - Added regression coverage for input category classification and common fallback intent families.

## Key Evidence

Completion evidence file:

- `docs/reports/completion_evidence/edu_safety_coach_verified_rag_anchors_20260628.json`

Local all-available evaluation:

- Command:
  - `.venv/bin/python scripts/evaluate_edu_safety_coach_available_questions.py --sample-limit 150 --output docs/reviews/edu_coach_simulations/full_available_safety_coach_eval_20260628T_question_eligible.json`
- Result:
  - unique inputs: `54,936`
  - skipped non-user/question-noise inputs: `47,383`
  - answer-quality eligible inputs: `7,553`
  - eligible clear: `5,313`
  - eligible needs_work: `2,240`
  - remaining `question_not_addressed`: `2,045`
  - RAG expected: `12,968`
  - RAG pass: `12,968`
  - source quote verified: `24,062`
  - source URLs checked: `9`
  - no hard RAG/source/markdown failures observed.

Mac Mini all-available evaluation:

- Command:
  - `ssh macmini 'cd /Users/juntaepark/projects/harness-platform && .venv/bin/python scripts/evaluate_edu_safety_coach_available_questions.py --sample-limit 80 --output scratch/full_available_safety_coach_eval_question_eligible_macmini_20260628.json'`
- Result:
  - unique inputs: `57,068`
  - skipped non-user/question-noise inputs: `48,874`
  - answer-quality eligible inputs: `8,194`
  - eligible clear: `5,770`
  - eligible needs_work: `2,424`
  - remaining `question_not_addressed`: `2,229`
  - RAG expected: `13,215`
  - RAG pass: `13,215`
  - source quote verified: `24,508`
  - source URLs checked: `9`

## Verification Already Run

Local:

- `.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py -q`
  - `108 passed, 3 warnings, 59 subtests passed`
- `.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py tests/test_edu_evidence_quality.py tests/test_edu_customer_facing_retrieval.py tests/test_embeddings.py -q`
  - `125 passed, 5 warnings, 59 subtests passed`
- `.venv/bin/python scripts/check_edu_coach_simulation_regression.py`
  - `ok=true`
  - adversarial needs_work: `45 <= 95`
  - corpus needs_work: `1,697 <= 14,265`
- `npm run build --prefix harness-os/edu-app`
  - build succeeded.
- `.venv/bin/python scripts/agent_completion_guard.py --require-deploy --require-red-team docs/reports/completion_evidence/edu_safety_coach_verified_rag_anchors_20260628.json`
  - `completion_guard: CLEAR`
  - status: `residual_risk`

Mac Mini:

- `scripts/deploy_to_macmini.sh ...`
  - backend reload passed.
  - port `8000` served.
  - origin diff checks returned `0` for deployed files.
- `ssh macmini 'cd /Users/juntaepark/projects/harness-platform && .venv/bin/python -m pytest tests/test_edu_vp_training_flow.py -q'`
  - `108 passed, 2 warnings, 59 subtests passed`
- Mac Mini completion guard:
  - `completion_guard: CLEAR`

## Red-Team Status

Requested red-team pair was Claude + Gemini.

Artifacts:

- `docs/reviews/edu_coach_simulations/red_team_claude_question_eligible_20260628.md`
- `docs/reviews/edu_coach_simulations/red_team_gemini_question_eligible_20260628.md`

Result:

- Claude CLI produced no output after more than 120 seconds and was interrupted.
- Gemini CLI failed with `IneligibleTierError`.
- Therefore red-team verdict is correctly recorded as `red_team_residual_risk`, not `red_team_clear`.

## Residual Risk

This work is not a perfect completion claim.

Remaining known issues:

- Local eligible `needs_work`: `2,240`
- Local remaining `question_not_addressed`: `2,045`
- Mac Mini eligible `needs_work`: `2,424`
- Mac Mini remaining `question_not_addressed`: `2,229`
- API spot check against `http://127.0.0.1:8000/api/edu/vp-training/safety-coach` was not completed because the non-interactive Mac Mini shell did not expose a usable `HARNESS_OS_SECRET_KEY`, and `.env` lookup did not produce a usable secret. No secret value was printed.

Interpretation:

- RAG/source hard gate is strong.
- Non-question/source noise is now largely separated.
- Real answerable question quality still has residual cases and should be improved in future loops without weakening the source/RAG gates.

## How To Verify User-Visible Effect

Use these checks:

1. RAG-eligible parent AI question:
   - `AI가 아이 숙제를 대신 해주는 건 어디까지 막아야 해?`
   - Expected:
     - RAG/source link appears when matched.
     - `출처:` appears with URL.
     - no raw `**` markdown leak.
     - source quote is actually present in source content.

2. Source snippet / title-like input:
   - `이런 상황이면 어떻게 해야 해요? 앤트로픽 vs 오픈AI 왜 사모펀드와`
   - Expected:
     - clarification answer, not generic coaching.
     - `model=input-clarifier`.
     - `evidence_used=false`.

3. Common parent AI-learning questions:
   - `챗GPT 초등학생에게 깔아줘도 돼?`
   - `AI 학습앱이 틀린 답을 줄 수도 있다면 어떻게 확인해야 해?`
   - `AI 디지털교과서 때문에 아이가 기계에 의존할까 걱정돼`
   - Expected:
     - direct answer to the intent.
     - no old generic template: `AI 교육이나 학습을 시작할 때는...`
     - summary break before `간단히 말하면,`.

## Suggested Next Loop

If the user wants further improvement:

1. Sample the remaining eligible `needs_work` cases from:
   - `docs/reviews/edu_coach_simulations/full_available_safety_coach_eval_20260628T_question_eligible.json`
2. Group by recurring intent rather than exact text.
3. Add only broad fallback/intent branches that cover many cases.
4. Keep input eligibility strict so source snippets do not get forced into fake answers.
5. Re-run:
   - full all-available evaluation
   - targeted pytest
   - broader pytest
   - simulation guard
   - completion guard
   - Mac Mini deploy + Mac Mini evaluation

## Dirty State At Handoff Creation

At the start of this handoff creation, `git status --short` was clean.

After creating this handoff file, the new file itself is expected to be uncommitted until staged/committed.
