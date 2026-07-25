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
