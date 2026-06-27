# Edu Curriculum Trust and Preview Handoff - 2026-06-25

## Current State

- Repo: `/Users/juntae.park/projects/harness-platform`
- Local HEAD: `7c15607 fix: clarify edu curriculum item counts`
- Origin `main`: pushed through `7c15607`
- Mac Mini HEAD: `7c15607`
- Mac Mini app URL: `http://100.97.175.44:5174/`
- Mac Mini services restarted after the latest deploy:
  - `com.harness.harness-os-backend`
  - `com.harness.edu-app`
- Mac Mini `com.harness.edu-daily` is still running from `2026-06-25 22:02:21`, currently at `4/5 Tier3 정제 + RAG 인덱스`.

## User Complaints Addressed

1. The Day 0 "맞춤 시작점" had too many reference cards expanded by default.
   - Changed to collapsed-by-default UX in the training screen.
   - Collapsed state summarizes what is inside and lets interested users expand.

2. The first reference card title and linked source did not match.
   - Example bad source: `https://blog.naver.com/sbk8004/224312216722`
   - The link was about an AI instructor / library training review, not "ChatGPT로 숙제하는 우리 아이, 말려야 할까요?"
   - Added trust curation so customer-facing evidence comes only from trusted evidence rows.

3. Need a background trusted evidence pool before VP/customer exposure.
   - Added curation and audit flow around `edu_curriculum_evidence_reviews` and trusted evidence selection.
   - Customer-facing personalization now loads trust metadata and uses trusted evidence.

4. Claude-selected curriculum preview mentioned Gemini.
   - Fixed hardcoded Gemini wording in adaptive curriculum module outcomes.
   - For selected `Claude`, module outcome now says `Claude 첫 질문`.

5. `Module 1 · ... · Day 0-11` looked like a 12-day training block.
   - Replaced range display with module item count.
   - Then refined again because "12개 실습" overstated the UX.
   - Current wording is:
     - `100개 개인화 항목`
     - `12개 항목 묶음`
     - Shows up to 3 `대표 실습 예` per module.

## Key Commits

- `79bd5ff feat: audit edu curriculum trust curation`
  - Added trust review table support and trusted curation output.
  - Added trust fields to personalization and UI cards.
  - Added prompt rules to prevent source/title mismatch.
  - Added tests for trust metadata.

- `3605310 fix: clamp edu trust scores`
  - Clamped trust score to max `1.0` to avoid `104%` display.

- `ee2c8ca docs: add edu personalization handoff`
  - Committed prior dirty handoff/test changes per user request.

- `64e9795 fix: align edu curriculum preview wording`
  - Passed selected LLM label into module phase generation.
  - Replaced `Day 0-11` range with item-count display.
  - Added regression test for Claude/Gemini mismatch.

- `7c15607 fix: clarify edu curriculum item counts`
  - Replaced "실습" count wording with "개인화 항목" / "항목 묶음".
  - Exposes up to 3 representative missions per module.

## Files Touched In Latest UX Fixes

- `harness-os/backend/main.py`
  - `_edu_vp_curriculum_modules(...)`
    - now accepts `llm_label`.
    - no longer hardcodes Gemini in first module outcome.
    - returns up to 3 `sample_missions`.
  - `_edu_vp_module_phase(...)`
    - now uses selected LLM label.

- `harness-os/edu-app/src/components/TrainingScreen.tsx`
  - Dynamic path preview wording:
    - `개인화 항목`
    - `항목 묶음`
    - `대표 실습 예`

- `tests/test_edu_vp_training_flow.py`
  - Added regression coverage for selected LLM label and sample mission count.

## Verification Completed

Local:

```bash
.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py
npm run build --prefix harness-os/edu-app
npm run lint --prefix harness-os/edu-app
```

Results:

- `tests/test_edu_vp_training_flow.py`: 5 passed
- `npm run build`: passed
- `npm run lint`: passed

Mac Mini:

```bash
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && git pull --ff-only && PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin npm run build --prefix harness-os/edu-app && uid=$(id -u) && launchctl kickstart -k gui/$uid/com.harness.harness-os-backend && launchctl kickstart -k gui/$uid/com.harness.edu-app'
```

After deploy:

- Mac Mini HEAD: `7c15607`
- `curl -I http://100.97.175.44:5174/`: `HTTP/1.1 200 OK`
- Backend/app launchd jobs are running.

Direct Mac Mini code check after `64e9795` showed:

```python
{
  "head": "모듈 1 · 첫 성공 만들기",
  "outcome": "'업무 답장 부담'를 Claude 첫 질문으로 바꾸고 쓸 만한 답변 1개를 저장한다.",
  "lesson_count": 12,
  "has_gemini": False
}
```

## Operational Data Quality State

Before the latest UI wording fix, Mac Mini trusted curriculum curation had been verified:

- Trusted rows: `49`
- Highlight rows returned in personalization: `12`
- Bad `sbk8004` link presence: `False`
- Trust score range after clamp: `0.72` to `1.0`

The source trust work is not a full guarantee that all historical education data is clean. It is a gate so VP/customer-facing curriculum pulls only from the trusted pool. Continue treating raw and filtered historical data as untrusted until curated.

## Known Risks / Next Work

1. `scripts/edu_daily.sh` can spend a long time in Tier3.
   - Current Mac Mini run is still at `4/5 Tier3 정제 + RAG 인덱스`.
   - Previous runs took about 2-3 hours.
   - Google embedding/RAG indexing may fail with `429 RESOURCE_EXHAUSTED` due monthly spending cap.
   - Recommended next patch: add timeout/fail-open behavior so curriculum curation still runs even when Tier3/RAG is slow or capped.

2. The "개인화 전체 과정" preview is still only a preview.
   - It now shows representative missions, but not the full item-by-item checklist.
   - If user wants stronger fidelity, next UX step is an expandable module detail view showing the actual underlying items/checklists for that module.

3. Copilot review for `64e9795` was attempted but did not complete.
   - It was cancelled after long wait with no final findings.
   - Do not claim formal cross-LLM `red_team_clear` for this UI wording change.

4. Gemini is excluded from Red Team automation through at least `2026-06-30` unless `HARNESS_GEMINI_RED_TEAM_ENABLED=true`.

## Useful Commands After Fresh Start

Check local state:

```bash
cd /Users/juntae.park/projects/harness-platform
git status --short
git rev-parse --short HEAD
```

Check Mac Mini state:

```bash
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && git status --short && git rev-parse --short HEAD && launchctl list | egrep "com.harness.(harness-os-backend|edu-app|edu-daily)" && tail -60 logs/edu-daily.log'
```

Check app:

```bash
curl -I http://100.97.175.44:5174/
```

Run focused validation:

```bash
.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py tests/test_edu_curriculum_personalization.py
npm run build --prefix harness-os/edu-app
npm run lint --prefix harness-os/edu-app
```

## Codex CLI Communication Rule

Codex CLI 사용 시 사용자와의 응답은 `caveman full` 규칙을 적용한다. 단, 코드 변경 요약은 정확하게 유지하고, 변경 파일·검증·커밋·배포 상태는 생략하지 않는다.
