# Smartfarm dashboard implementation - Claude RED TEAM

- Reviewer: Antigravity `claude-sonnet-4-6`
- Verdict: `red_team_residual_risk`
- Material blockers: none

## Verified

- ON is feature-flagged off by default and requires CEO role, one-time fresh nonce, fresh watchdog-capable device,
  good sensor quality, and no active command.
- Raspberry Pi hub is the sole structured manual pump owner and checks sequence, expiry, cooldown and sensor fault.
- Firmware has an independent maximum-run watchdog.
- Dashboard distinguishes publish, ack and observed state.

## Finding resolved after review

- Automatic Pi hub `pump/cmd` publishes used default QoS 0. Both start and stop now publish QoS 1, non-retained.

## Required live verification before enabling ON

1. Mac mini `/api/smartfarm/overview`: DB healthy and MQTT connected.
2. Each controllable node reports a fresh boot ID and non-null watchdog duration.
3. Firmware heartbeat capabilities match the physically wired sensors.
4. Diagnostic request produces edge result.
5. OFF produces broker ack and observed physical state.
6. `HARNESS_SMARTFARM_ACTUATION_ENABLED` remains absent/false until all above pass.
