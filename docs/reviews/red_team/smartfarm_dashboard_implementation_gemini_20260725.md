# Smartfarm dashboard implementation - Antigravity Gemini RED TEAM

- Reviewer: Antigravity `gemini-3.6-flash-low`
- Scope: dashboard runtime, API, UI, firmware, Pi hub, deploy and tests
- Initial verdict: `red_team_block`

## Material findings

1. Zone safety check and command creation needed one atomic zone-level control lock.
2. Direct SQLite writes and the telemetry writer queue needed common serialization.
3. Dashboard manual pump commands bypassed Raspberry Pi hub state, cooldown and sensor-fault ownership.

## Resolution

- Added `SmartfarmRuntime.control_guard()` around safety check, one-time nonce consumption and command creation.
- Serialized direct writes and writer-thread writes with the DB write lock; added concurrent ingest/read/command test.
- Raspberry Pi hub now owns structured pump commands, validates expiry/sequence/duration/fault/cooldown,
  updates `ZoneState`, emits ack, and dispatches the legacy edge command.
- ESP nodes no longer subscribe to structured pump requests, so the Pi safety owner cannot be bypassed.

## Re-review

- Verdict: `red_team_clear`
- Remaining material blockers: none
- Reviewer verified the zone control lock, shared SQLite write serialization, and Pi-hub-only pump intent path.
- Required focused suites: dashboard runtime, pump control, and Pi hub structured command tests.
