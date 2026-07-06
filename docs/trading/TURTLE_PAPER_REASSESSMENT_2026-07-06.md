# Turtle Paper Reassessment — Entry Lock and 2-Week Review

Date: 2026-07-06
Scope: Alpaca paper trading, IBKR paper trading schedule guard
Status: active paper trading is restricted; existing Alpaca positions remain protected by broker stop orders.

## Executive Decision

Do not continue the current Turtle automation as-is.

The current paper result is below the required benchmark gate. The drawdown is not large enough by itself to invalidate Turtle trading, but the portfolio is underperforming SPY and the operating state was inconsistent. The correct next state is:

- no new automatic entries
- no pyramiding
- keep existing Alpaca positions under resident stop orders
- do not enable short trading yet
- remeasure paper results for 2 weeks before any live-capital decision

This is not investment advice or a recommendation to buy, sell, or hold securities. It is an internal paper-trading operating control.

## Current Alpaca Ground Truth

Read-only broker check on 2026-07-06 confirmed 3 active long positions:

| Symbol | Qty | Avg entry | Current | Unrealized P/L | Stop order |
| --- | ---: | ---: | ---: | ---: | --- |
| ASX | 377 | 40.51 | 44.10 | +1,353.43 | live stop, sell 377 @ 35.34 |
| TSM | 48 | 465.765 | 444.00 | -1,044.72 | live stop, sell 48 @ 423.65 |
| VRT | 52 | 326.292308 | 307.18 | -993.84 | live stop, sell 52 @ 284.50 |

Open order check confirmed exactly 3 open stop orders, one per active position.

## State Reconciliation

`docs/reports/paper_trading_positions.json` had no tracked positions while Alpaca held ASX, TSM, and VRT. The file was reconciled to the broker state using the existing stop order IDs. No new Alpaca orders were submitted during reconciliation.

The state now includes:

- `ASX`
- `TSM`
- `VRT`
- `entry_lock: new_entries_disabled_max_positions_0_pyramid_disabled`

## Scheduler Guard

The installed and repo LaunchAgent plists now carry:

- `PAPER_TRADING_MAX_POSITIONS=0`
- `PAPER_PYRAMID_ENABLED=false`
- Alpaca also carries `PAPER_TRADING_AUTO_EXECUTE=false`

Important nuance: the LaunchAgent still passes `--execute`, so exits and protective management can still run. New entries are blocked by `MAX_POSITIONS=0`; pyramiding is blocked separately.

## IBKR Status

IBKR paper broker-side verification is currently blocked:

- mode: paper
- port: `127.0.0.1:4002`
- result: connection refused

The IBKR scheduler guard was still applied through LaunchAgent environment variables, but live IBKR positions and open orders were not verified. Before any IBKR paper execution is trusted again, IB Gateway/TWS must be running and `scripts/ibkr_runtime_status.py` must pass.

## Long-Only vs Short Decision

Do not enable short trading now.

Reason:

- The current codebase still treats the mature path as long-oriented in several places.
- Short trading needs separate short-safe state, order, exit, borrow/margin, and backtest handling.
- Recent short breakout signals show that the market regime would have rewarded a symmetric system, but turning on shorts immediately would replace one known risk with a larger implementation risk.

Interim rule:

- long-only stays disabled for new entries during the 2-week review
- short trading remains disabled
- any future short rollout requires a separate short-safe implementation review and paper-only validation

## 2-Week Measurement Plan

Measurement window starts after this entry lock is active.

Daily checks:

- Alpaca account value
- SPY return over the same window
- QQQ return over the same window
- SMH and SOXX return over the same window
- open positions and stop order coverage
- state file vs broker position match

Pass conditions for reopening new paper entries:

- state and broker positions match for 10 consecutive trading days
- every active position has exactly one live protective stop
- no unintended new entry or pyramid order appears while locked
- portfolio return is not worse than SPY by more than 5 percentage points over the review window
- max single-position loss remains above -15%

Fail conditions:

- any missing protective stop
- state/broker mismatch
- any new entry while lock is active
- IBKR Gateway remains unverifiable when IBKR paper execution is scheduled

## Re-Enable Gate

Do not re-enable new Turtle entries until all are true:

- `scripts/turtle_auto_trader.py` dry-run sees broker positions and reports 0 unexpected reconcile actions
- `scripts/ibkr_runtime_status.py` passes when IBKR paper is in scope
- Chief of Staff review records `cos_approve`
- Red Team confirms no unresolved state/order lifecycle blocker
- CEO explicitly approves removing `PAPER_TRADING_MAX_POSITIONS=0`
