# IBKR A-to-Z Setup

Last updated: 2026-05-26

Purpose:
- enable Harness to monitor and eventually trade Korean, US, Japanese, and European securities through IBKR
- keep the current implementation read-only until account, market-data, and approval gates are fully validated

Primary official sources:
- IBKR Web API / Client Portal API docs: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/
- IBKR Web API overview: https://www.interactivebrokers.com/campus/ibkr-api-page/webapi-doc/
- IBKR account application requirements: https://www.interactivebrokers.com/en/general/what-you-need-inv.php
- IBKR individual account structures: https://www.interactivebrokers.com/en/accounts/individual.php

## 1. Business Boundary

Current Harness implementation status:
- dashboard integration exists
- IBKR Client Portal Gateway preflight exists
- ETF whitelist contract resolution exists
- read-only watchlist quote monitor exists
- no live order placement has been enabled

Do not enable live trading until all of the following are true:
- IBKR account is opened and funded
- required market-data subscriptions are active
- account visibility and quote freshness are stable in the dashboard
- legal / internal approval policy for live trading is written and approved

## 2. Human Steps Required

These cannot be completed by Codex alone:
- create or log into the IBKR account
- complete KYC / identity verification
- complete 2FA enrollment
- fund the account
- accept market-data and exchange agreements
- install and launch IBKR Client Portal Gateway if not already installed

## 3. Account Requirements

From IBKR official docs:
- Client Portal API requires an active IBKR account
- Client Portal API supports IBKR Pro accounts
- demo accounts cannot subscribe to data
- funded account is required before receiving data
- 2FA is required

What you need for the application typically includes:
- legal name
- residential address
- date of birth
- citizenship / country of birth
- tax residency and tax ID number
- employer information
- assets / income / investment experience
- funding account information

## 4. Recommended Account / Product Scope

For the current Harness use case:
- account type: Individual
- plan: IBKR Pro
- base currency: USD is simplest operationally
- product scope:
  - US stocks / ETFs
  - Korean ETFs / stocks if exchange access is enabled
  - Japanese listings / ETFs
  - European UCITS ETFs where supported

## 5. Manual IBKR Onboarding Checklist

1. Open IBKR Pro individual account.
2. Complete KYC and identity verification.
3. Enable supported 2FA.
4. Fund the account.
5. Enable trading permissions for target regions/products.
6. Subscribe to the market data needed for the watchlist.
7. Download and run IBKR Client Portal Gateway.
8. Log into the Gateway and complete 2FA.
9. Confirm `authenticated=true` from the local API.
10. Confirm account visibility from Harness dashboard.

## 6. Local Environment Setup

Add these to local `.env`:

```env
IBKR_CP_API_BASE_URL=https://localhost:5000/v1/api
IBKR_CP_TIMEOUT_S=12
IBKR_CP_TLS_VERIFY=false
```

Notes:
- `IBKR_CP_TLS_VERIFY=false` is acceptable only for localhost Gateway use
- current code explicitly rejects non-local hosts when TLS verify is false

## 7. Gateway Verification

Low-level client:
- `scripts/ibkr_cp_client.py`

Bridge commands:

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py status
.venv/bin/python scripts/openclaw_codex_bridge.py ibkr-setup-status
.venv/bin/python scripts/openclaw_codex_bridge.py ibkr-etf-check --format text
```

Expected success signals:
- Gateway reachable
- `authenticated=true`
- visible accounts count > 0
- no persistent preflight error in dashboard

## 8. Contract Resolution Workflow

Files:
- ETF candidate list: `docs/trading/etf_whitelist_v0.json`
- operator watchlist: `docs/trading/trading_watchlist_v0.json`
- approved mappings: `docs/reports/instrument_registry.jsonl`
- pending mappings: `docs/reports/instrument_registry_pending.jsonl`

Read-only resolution flow:
1. maintain ETF whitelist candidates
2. run `ibkr-etf-check`
3. inspect confidence and ambiguity
4. only then append approved mappings

## 9. Dashboard Integration

Current dashboard covers:
- Gateway connectivity
- authenticated status
- visible accounts
- setup checklist progress
- whitelist item count
- approved registry count
- pending review count
- read-only watchlist quotes
- quote freshness
- inactive watchlist filtering
- UI-based add / activate / deactivate

Primary UI:
- `http://127.0.0.1:5173`
- onboarding status file: `docs/trading/ibkr_onboarding_status.json`

CLI:

```bash
.venv/bin/python scripts/ibkr_onboarding.py status
.venv/bin/python scripts/ibkr_onboarding.py complete --step-id account_opened
.venv/bin/python scripts/ibkr_onboarding.py complete --step-id kyc_complete
.venv/bin/python scripts/ibkr_onboarding.py reset --step-id funded
.venv/bin/python scripts/ibkr_onboarding.py note --note "Waiting for market-data subscription decision"
```

## 10. Watchlist Operations

CLI:

```bash
.venv/bin/python scripts/trading_watchlist.py list
.venv/bin/python scripts/trading_watchlist.py add --id us-QQQ --query QQQ --name-hint "Invesco QQQ Trust"
.venv/bin/python scripts/trading_watchlist.py deactivate --id us-BOTZ
.venv/bin/python scripts/trading_watchlist.py activate --id us-BOTZ
```

Bridge:

```bash
.venv/bin/python scripts/openclaw_codex_bridge.py trading-watchlist-list --format json
.venv/bin/python scripts/openclaw_codex_bridge.py trading-watchlist-add --id us-QQQ --query QQQ --name-hint "Invesco QQQ Trust"
.venv/bin/python scripts/openclaw_codex_bridge.py trading-watchlist-deactivate --id us-BOTZ
.venv/bin/python scripts/openclaw_codex_bridge.py trading-watchlist-activate --id us-BOTZ
```

## 11. Market Data Validation

Before using data operationally:
- verify each target exchange/product has real quotes
- check freshness after repeated refreshes
- identify which instruments return delayed / missing data
- remove or flag instruments that lack entitlement

## 12. What Still Requires Human Input

Codex cannot complete these without you:
- IBKR website login / application
- ID upload / KYC completion
- funding transfer
- exchange market-data purchase decisions
- Gateway login and 2FA session completion

## 13. Next Technical Steps

After account is live:
1. verify accounts endpoint shows the real account
2. verify quote entitlement for every watchlist item
3. add priority editing in UI
4. add scenario / invalidation / note fields to watchlist
5. only after governance sign-off, discuss live order flow

---

## 14. 진행 이력 (CEO 직접 확인 사항)

| 날짜 | 확인 내용 | 비고 |
| --- | --- | --- |
| 2026-05-26 | CEO IBKR 로그인 화면 스크린샷 제공. IBKR 계정 존재 확인. | **⚠️ 주의: 스크린샷은 IBKR Prediction Markets(이벤트 컨트랙트) 화면. 일반 주식 거래 Pro 계좌 여부 별도 확인 필요.** |

### ⚠️ IBKR Prediction Markets vs IBKR Pro — 반드시 구분

| 항목 | IBKR Prediction Markets | IBKR Pro (필요한 것) |
| --- | --- | --- |
| 거래 대상 | 선거 결과, 금리 결정, 원자재 가격 이벤트 컨트랙트 | 주식, ETF, 선물 등 실제 증권 |
| Turtle Trading 적용 가능 | ❌ 불가 | ✅ 가능 |
| Client Portal API 지원 | ❌ 별도 플랫폼 | ✅ 지원 |
| IBKR Gateway 연동 | ❌ | ✅ |

### Pro 계좌 여부 확인 방법

IBKR 웹 로그인 후:
```
상단 메뉴 → Account → Account Type / Account Summary
→ "IBKR Pro" 또는 "Individual IBKR Pro" 표시 여부 확인
```

또는 Client Portal:
```
https://www.clientam.interactivebrokers.com/portal
→ 로그인 후 계좌 정보 확인
```

### CEO 확인 요청 사항

1. IBKR 로그인 후 계좌 유형이 **"IBKR Pro"** 인지 확인
2. 주식/ETF 거래 권한이 있는지 확인
3. 미국 주식(US Stocks/ETFs) 거래 활성화 여부 확인
4. 계좌에 입금(funding)이 완료됐는지 확인

→ 위 4가지 확인 완료 시 `ibkr_onboarding_status.json`의 `account_opened`, `kyc_complete` 를 `true`로 업데이트 가능.
