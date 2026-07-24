# OpenClaw hardware typo grounding — Claude review

Scope: final staged implementation for model-identifier normalization, evidence ranking, Skill
instructions, tests, and completion evidence.

## Verdict

`VERDICT: clear`

## Findings addressed before release

- Added exact-match, ambiguous-match, repeated-token, and unrelated-context fail-safe tests.
- Limited candidates to smartfarm hardware/config roots.
- Limited correction to registered model families and hardware-context questions.
- Preserved the original question and exposed every correction as an explicit assumption.
- Added physical-pin and Wi-Fi/MQTT evidence coverage.

No blocker was found. Claude recommended avoiding broad hardware roots and protecting
non-model technical identifiers; both recommendations were incorporated before commit.

## Production routing follow-up

The first production replay exposed that the misspelled model did not trigger the Skill and
the model bypassed the native knowledge tool through memory and shell searches. The follow-up
review found no major issue after adding a hardware-model plus connection-intent trigger and
blocking memory, shell, and workspace-search fallbacks only inside an active knowledge run.
English intent boundaries and negative compatibility tests were added from the minor findings.

`VERDICT: clear`
