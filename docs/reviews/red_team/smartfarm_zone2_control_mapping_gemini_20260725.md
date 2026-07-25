# Smartfarm zone2 Control Mapping RED TEAM — Gemini

- Reviewer: Antigravity Gemini 3.6 Flash Low
- Initial verdict: `red_team_block`
- Remediation verdict: `red_team_clear`

Initial block:

- Missing control-zone configuration allowed TEST/ON to fail open.
- A future multi-pump configuration needed an independent control-zone selector.

Remediation verified:

- Production explicitly configures `HARNESS_SMARTFARM_PUMP_CONTROL_ZONES=zone2`.
- TEST/ON fail closed when the setting is empty.
- A zone outside the configured set returns `pump_control_zone_disabled`.
- Monitoring `selectedZone` and physical `selectedControlZone` are independent.
- Multiple configured control zones render a dedicated selector.
- Emergency OFF remains outside `pump_safety` and stays available.

Residual risk:

- Zone IDs are case-sensitive and must remain canonical lowercase values.
