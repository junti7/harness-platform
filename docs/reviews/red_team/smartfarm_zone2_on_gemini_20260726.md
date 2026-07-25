# Smartfarm zone2 ON RED TEAM — Gemini

- Reviewer: Antigravity Gemini 3.6 Flash Low
- Initial verdict: `red_team_block`
- Remediation verdict: `red_team_clear`

Initial findings:

- An OFF observation arriving before ON could falsely complete a `pump_on` command.
- A fixed 10-second UI polling window was insufficient for longer bounded commands.

Remediation verified:

- Completion requires prior `status=observed` and `observed_state=on`.
- OFF-before-ON does not complete and has a regression test.
- UI observation timeout is requested duration plus seven seconds.
- CEO role, one-use nonce, exact zone confirmation, zone2 binding, sensor/watchdog checks, cooldown, and edge auto-OFF remain.

Residual risk:

- Lost MQTT ON observation leaves the command incomplete instead of reporting false success.

Final startup review:

- Initial autostart implementation was blocked for test contamination and duplicate-worker risk.
- Production-only `HARNESS_SMARTFARM_AUTOSTART`, single-worker launchd, and explicit MQTT/writer shutdown remediation received `red_team_clear`.
