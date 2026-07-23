# Claude Red Team — OpenClaw Notebook Orchestration

- Scope: deterministic enrichment, NotebookLM answer contract, privacy, Saju calendar parsing
- Final recorded verdict: `red_team_clear`

Claude found and drove fixes for refusal-echo acceptance, solar-term boundaries,
birth/target inversion, lunar fail-open paths, argv PII exposure, 23-hour day
boundaries, AM/PM parsing, unrelated target-time capture, out-of-range hours,
and limitation-language false positives.

The final reported blocker was the limitation-language false positive in the
semantic non-answer detector. That issue was fixed by limiting the semantic
refusal heuristic to short answers and adding a positive regression test for a
complete grounded answer containing explicit limitations.

After quota recovery, Claude independently re-reviewed commit `57f6ea8` and
returned `red_team_clear`. The final verification confirmed:

1. Short semantic refusals fail.
2. Complete cited answers with limitation language pass.
3. No high/critical correctness, privacy, or fail-open regression remains.
4. The deterministic pillars match independent day/month/hour calculations.
5. Sensitive questions remain off argv and out of the audit log.

Residual non-blocking risks remain in heuristic answer-contract coverage and
documented unsupported calendar/time inputs. They do not invalidate the clear
verdict.
