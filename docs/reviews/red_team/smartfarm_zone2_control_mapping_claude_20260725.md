# Smartfarm zone2 Control Mapping RED TEAM — Claude

- Reviewer: Claude Sonnet 4.6
- Verdict: `red_team_clear`

Verified:

- Monitoring and physical control zone state are independent.
- Production explicitly maps physical pump control to `zone2`.
- Missing configuration and nonconfigured TEST/ON targets fail closed.
- Emergency OFF remains available.
- Multiple future configured pump zones render a dedicated selector.

Low residual findings:

- Empty configuration safely disables the control panel but only shows `미설정`.
- A configured zone absent from telemetry displays `UNKNOWN`; backend safety still decides execution.
