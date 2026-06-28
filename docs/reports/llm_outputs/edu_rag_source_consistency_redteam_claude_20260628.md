claude_red_team_unavailable

Attempted commands:
- `/Applications/cmux.app/Contents/Resources/bin/claude --bare -p ...`
- `/Applications/cmux.app/Contents/Resources/bin/claude -p ...` with a 120 second alarm wrapper

Result:
- `--bare` failed with `Not logged in · Please run /login`.
- Normal non-interactive mode responded to a trivial prompt, but the actual source-consistency red-team prompt timed out after 120 seconds with no usable review output.

Status:
- No `red_team_clear` was claimed from Claude for this run.
