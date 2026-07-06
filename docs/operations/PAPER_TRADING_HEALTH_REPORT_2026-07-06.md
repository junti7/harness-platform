# Paper Trading Health Report — 2026-07-06

Status: active

## What Changed

Added a daily paper trading health report for the Turtle paper lock period.

Files:

- `scripts/run_paper_trading_health_report.py`
- `harness-os/launchd/com.harness.paper-trading-health-report.plist`

The script writes runtime outputs to ignored paths:

- `docs/reports/paper_trading_health_report.json`
- `docs/reports/paper_trading_health_report.jsonl`

## Schedule

Mac Mini LaunchAgent:

```text
com.harness.paper-trading-health-report
```

Runs weekdays at `13:45 UTC`, after the Alpaca and IBKR post-open paper trading scheduler slots.

## Checks

The report verifies:

- Alpaca account status
- Alpaca active positions
- Alpaca open protective stop coverage
- Alpaca AR-018 paper KPI snapshot
- IBKR Gateway connectivity
- IBKR active positions
- IBKR open protective stop coverage
- IBKR state ↔ broker position match
- SPY, QQQ, SMH, SOXX benchmark snapshot
- LaunchAgent entry lock variables for Alpaca and IBKR

The report exits non-zero if any required stop coverage or entry-lock check fails.

## IBKR 000660 Stop Repair

Initial read-only health check found:

```text
IBKR 000660: position 93 shares, open protective stop count 0
```

The state file contained:

```text
stop_loss = 2030881.4 KRW
resident_stop_id = 96
```

IBKR rejected that exact stop price because it did not conform to the KRX minimum price variation. The health script now normalizes KRX/KRW sell stop prices down to the valid tick. For this position:

```text
2030881.4 -> 2030000
```

Repair command used on Mac Mini:

```bash
HARNESS_ROOT=/Users/juntaepark/projects/harness-platform \
  .venv/bin/python /tmp/run_paper_trading_health_report.py --repair-ibkr-stops --json
```

Result:

- created IBKR paper `SELL STP` order
- symbol: `000660`
- quantity: `93`
- stop price: `2030000.0`
- status observed: `PreSubmitted`
- state updated with `resident_stop_id=8`

Follow-up read-only run returned `ok=true`.

## Operating Rule

Default scheduled run is read-only. It does not use `--repair-ibkr-stops`.

Use repair mode only when:

- the state file already tracks the position
- broker has the matching position
- protective stop coverage is missing
- the repair is for a resident stop only, not a new entry
