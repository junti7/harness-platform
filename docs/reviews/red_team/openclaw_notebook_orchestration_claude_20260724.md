# Claude Red Team — OpenClaw Notebook Orchestration

- Scope: deterministic enrichment, NotebookLM answer contract, privacy, Saju calendar parsing
- Final recorded verdict: `red_team_block`

Claude found and drove fixes for refusal-echo acceptance, solar-term boundaries,
birth/target inversion, lunar fail-open paths, argv PII exposure, 23-hour day
boundaries, AM/PM parsing, unrelated target-time capture, out-of-range hours,
and limitation-language false positives.

The final reported blocker was the limitation-language false positive in the
semantic non-answer detector. That issue was fixed by limiting the semantic
refusal heuristic to short answers and adding a positive regression test for a
complete grounded answer containing explicit limitations.

Claude could not perform the required post-fix rerun because the CLI session
quota was exhausted until 05:20 Asia/Seoul. Therefore this artifact must remain
`red_team_block`; the fix and passing local tests do not authorize changing the
verdict to clear.

## Required follow-up

After Claude quota recovery, independently review the current commit and verify:

1. Short semantic refusals fail.
2. Complete cited answers with limitation language pass.
3. No high/critical correctness, privacy, or fail-open regression remains.
