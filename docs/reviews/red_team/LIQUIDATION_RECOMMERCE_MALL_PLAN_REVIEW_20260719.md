# Red Team Review — Harness 재고가치회복형 커머스 추진계획

- Date: 2026-07-19
- Artifact: `docs/strategy/LIQUIDATION_RECOMMERCE_MALL_OPPORTUNITY_PLAN_20260719.md`
- Review scope: opportunity-candidate 단계의 계획 안전성·실행 가능성
- Requested resources: Gemini + GitHub Copilot CLI
- Claude: 사용자 지시에 따라 미사용
- Final verdict: `red_team_block`
- Retry count: 3 Copilot rounds, 2 Gemini CLI attempts, 1 Gemini browser fallback probe

## 1. Executive verdict

Copilot 최종 plan-only verdict는 `red_team_clear`다. 그러나 Gemini는 model review를 시작하지 못했다. `AGENTS.md`가 요구하는 서로 다른 모델 2개의 independent output이 없으므로 formal `red_team_clear`를 발행할 수 없다.

따라서 현재 상태:

- 계획 품질: Copilot 기준 clear
- cross-LLM gate: incomplete
- consolidated verdict: `red_team_block`
- 허용: 문서 보관, 대표 검토, 무비용 내부 준비
- 금지: 이 verdict를 근거로 상품 매입, 외부 공개, paid test, 판매 개시

## 2. Shared review prompt

```text
You are an independent Red Team reviewer. Review
docs/strategy/LIQUIDATION_RECOMMERCE_MALL_OPPORTUNITY_PLAN_20260719.md.
Do not edit any file. Test whether this beginner-facing 30-day plan can safely
validate a Korean liquidation/recommerce mall without pretending demand,
losing inventory capital, violating consumer/product/tax rules, or distracting
Harness core priorities. Check unit economics math, stage gates, evidence
quality, legal/product-safety boundaries, operational workload, KPI sample
sizes, approval semantics, and stop criteria. Return model identity, verdict,
critical/high/medium findings, required fixes, and residual risks.
```

## 3. Gemini execution record

### CLI identity

- binary: `/opt/homebrew/bin/gemini`
- version: `0.43.0`
- requested mode: read-only plan mode
- model output: none

### Failure

Both CLI attempts stopped during authentication with:

```text
IneligibleTierError: This client is no longer supported for Gemini Code Assist for individuals.
reasonCode: UNSUPPORTED_CLIENT
```

Environment preflight found no `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `GOOGLE_APPLICATION_CREDENTIALS`. Secret values were not printed. Emergency Gemini web fallback was checked, but the in-app browser surface was unavailable. No Gemini finding or verdict was fabricated.

### Gemini rerun brief

When a supported Gemini CLI/API/browser route becomes available, run the shared prompt against the final artifact and save:

- exact model identity
- exact prompt
- raw output
- verdict
- critical/high findings
- finding-to-fix mapping

Any Gemini critical/high finding returns the consolidated state to `red_team_block` until fixed and re-reviewed.

## 4. Copilot round 1

- CLI: `/opt/homebrew/bin/copilot`
- version: `1.0.71`
- model identity reported: `GPT-5.3-Codex (gpt-5.3-codex)`
- verdict: `red_team_block`

Critical/high findings:

1. CTR/interview signals were not separated enough from paid demand.
2. Korean consumer, product-safety, and tax operations lacked an evidence matrix.
3. Unit economics omitted labor, inventory markdown, dispute, and platform-penalty costs.
4. Inventory aging, maximum loss, and disposition rules were incomplete.
5. CS, settlement, cancellation, and profit-per-hour KPIs were incomplete.
6. Approval artifacts lacked quantitative evidence contracts.

## 5. Fixes applied

Plan was revised to include:

- SKU 10+ and total 30+ paid demand observations
- 95% Wilson interval and insufficient-evidence state
- explicit separation of CTA, interview, reservation, order, cancellation, refund
- Korean business/telecommerce, withdrawal/refund, product-safety, tax, settlement, privacy matrix
- labor, inventory loss, dispute, penalty, tax and settlement costs
- conservative/base/optimistic unit economics
- Day 30/45/60 inventory aging and liquidation rules
- per-SKU 100,000 won and portfolio 200,000 won maximum-loss rules
- CS SLA, cancellation, settlement-error and net contribution/hour KPIs
- gate-specific evidence and automatic block contracts
- settlement-delay, VAT reserve, refund-first, and inventory-liquidation cash stress
- distinction between plan Red Team and later experiment-result Red Team

## 6. Copilot round 2

- verdict: `red_team_block`
- resolved: legal/tax matrix, 3-scenario economics, inventory loss, operational KPIs, gate contracts
- remaining concern: plan review was incorrectly being asked to require future paid results already to exist, creating a circular gate
- additional request: sample 30+, cashflow stress

Resolution:

- plan `red_team_clear` now judges validation design, not future market proof
- actual experiment results require a later independent Red Team review
- paid sample raised to SKU 10+ and total 30+
- cashflow stress test added

## 7. Copilot final plan-only review

- model identity: `GPT-5.3-Codex (gpt-5.3-codex)`
- verdict: `red_team_clear`
- remaining critical/high plan findings: none

Copilot rationale:

- later legal, experiment, and capital gates correctly block execution
- approval semantics separate opportunity review from spending and sales
- paid sample, Wilson interval, and insufficient-evidence rules prevent early success claims
- cash stress, maximum loss, aging, and concentration controls limit inventory downside
- legal/tax/product-safety matrix and prohibited categories define beginner-safe boundaries
- weekly issue/CTR priority and six-hour weekly stop rule limit distraction

Residual risks:

- interview and CTA behavior may not reproduce in external sales
- 30 paid observations still have high variance
- supplier evidence quality can vary
- settlement delay and refund-first timing can create short liquidity pressure

## 8. Consolidated decision

```yaml
target_type: business_opportunity_plan
requested_approval: red_team_clear
copilot_verdict: red_team_clear
gemini_verdict: unavailable
cross_llm_requirement_met: false
final_verdict: red_team_block
human_review_required: true
block_reason: Gemini produced no independent review output
```

This is not a rejection of the business idea. It is a governance block on calling the plan cross-LLM-cleared.
