# Smartfarm Duration Alignment RED TEAM — Claude

- Reviewer: Claude Sonnet 4.6
- Verdict: `red_team_clear`

Verified:

- Backend rejects invalid and out-of-range duration before MQTT publication.
- UI TEST and ON controls cannot exceed the server-advertised maximum.
- Initial UI state defaults to the conservative 3-second limit.
- Production launchd maximum matches the Pi hub 3-second limit.

Low residual note:

- A runtime environment change reaches the backend immediately and the UI on its next overview poll; backend enforcement remains authoritative.

## UI rejection-message follow-up

- Reviewer: Claude Sonnet 4.6
- Verdict: `red_team_clear`
- Verified the TEST/ON branch and action-specific rejection labels.
- Requested confirmation that the displayed 300 seconds matches enforcement.
  `hardware/smartfarm/BENCH_WIRING.md` and the Pi hub `cooldown_s` contract confirm
  the production setting is 300 seconds.
