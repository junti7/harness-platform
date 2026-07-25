# Smartfarm dashboard implementation - Codex RED TEAM

- Reviewer: Codex
- Initial verdict: `red_team_block`

## Findings

1. Edge command sequence was RAM-only and structured pump control could bypass the Pi hub.
2. Concurrent ON requests with different valid nonces could pass the same pre-command safety snapshot.
3. SQLite had direct writes outside the single serialization boundary.
4. Mac mini lacked MQTT dependency and runtime configuration in its deployment path.

## Resolution

- Pump intent now terminates at the Pi hub, which checks expiry and monotonic sequence and owns relay dispatch.
- Per-zone control lock makes safety check, nonce consumption and command creation atomic.
- All SQLite writes share one lock; concurrency regression test added.
- Backend requirements installation and launchd MQTT/DB configuration added to the official deployment script.

## Re-review

- Verdict: `red_team_clear`
- Remaining material blockers: none
- Production verification still must prove broker ingest, Pi hub deployment, actual heartbeat after firmware flash,
  diagnostic result, and OFF observed state. ON remains blocked until these conditions are live-proven.

## Post-deploy delta

Live ESP8266 verification found that legacy scalar telemetry worked while heartbeat JSON did not publish because
PubSubClient retained its 256-byte default packet buffer. Firmware now calls `mqtt.setBufferSize(1024)`, has a
source regression assertion, and compiles for both ESP targets. This resolves the false-old-firmware condition.
