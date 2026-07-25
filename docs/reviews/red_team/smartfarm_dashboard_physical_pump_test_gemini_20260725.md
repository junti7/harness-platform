# Smartfarm Physical Pump TEST RED TEAM — Gemini

- Reviewer: Antigravity Gemini 3.6 Flash Low
- Verdict: `red_team_clear`

Reviewed change:

- A bounded `pump_test` uses a 5-second anti-repeat window instead of the 300-second irrigation cooldown.
- Normal `pump_on` retains the full configured irrigation cooldown.
- Active-pump rejection, sensor fault rejection, one-use CEO session token, per-zone lock, 3-second limits, Pi auto-OFF timer, and ESP watchdog remain.
- The UI waits for observed ON followed by completed OFF before reporting success.
- Edge rejection reasons are stored and shown to the operator.

Residual risks:

- Repeated TEST every few seconds can increase relay and pump wear.
- The UI uses a 10-second observation timeout; delayed telemetry may report timeout even if the edge later completes safely.
