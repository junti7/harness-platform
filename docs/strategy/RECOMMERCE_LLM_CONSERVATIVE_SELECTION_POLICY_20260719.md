# Recommerce LLM Conservative OJT Selection Policy

## Purpose

Two novice operators do not manually invent SKU candidates. The system may present an OJT research target only when a local LLM reviews current Naver Shopping price evidence and deterministic hard gates independently pass.

This is not a purchase, listing, supplier, or demand recommendation. It is a narrowly scoped instruction to investigate a product further without spending money.

## Data flow

`Naver Shopping Search API → safe-category / restricted-keyword filter → high-similarity competitor evidence → local Ollama LLM → deterministic hard gates → OJT research target or selection hold`

The local LLM is required. If it is unavailable, malformed, or cannot select a defensible target, the process fails closed: no candidate is shown. A human cannot manually override a candidate into the OJT list.

## Adaptive required gates

The system always tries the strict profile first. When that returns zero candidates, it tries only the next profile. It stops at the first profile that has a candidate; it never blends thresholds across profiles or silently relaxes them.

| Gate | Strict | Adaptive 1 | Adaptive 2 | Failure result |
| --- | --- | --- | --- | --- |
| Safety scope | Household organization only; restricted/safety-sensitive terms excluded | Same | Same | Reject |
| Ticket price | Comparable lower-quartile price ≥ 15,000 KRW | ≥ 14,000 KRW | ≥ 12,000 KRW | Reject |
| Comparable evidence | ≥ 5 high-similarity samples, ≥ 3 malls | Same | ≥ 4 samples, ≥ 2 malls | Reject |
| Price dispersion | 75th/25th ≤ 1.60 | ≤ 1.90 | ≤ 2.10 | Reject |
| LLM review | score ≥ 75/100 | ≥ 72/100 | ≥ 70/100 | Reject |
| Identity | Product ID and image both present | Same | Same | Reject |
| Worst-case economics | Allowable supplier cost ≥ 3,000 KRW | ≥ 2,500 KRW | ≥ 1,500 KRW | Reject |

Worst-case cost model: 15% platform fee, 8% return reserve, 10% advertising reserve, 20% target contribution, 4,000 KRW shipping, and 2,000 KRW labor/packaging. The OJT sales-price anchor is the comparable lower-quartile price, not a markup on a wholesale price.

## Explicit non-authorizations

- Naver Shopping Search API does not include actual shipping cost, supplier stock, wholesale terms, defect rate, or return responsibility.
- Therefore a selected item is `blocked_until_supplier_and_shipping_evidence`.
- The UI provides only a read-only market link, an empty evidence checklist, arithmetic review, and a copy-only inquiry draft. It cannot order inventory, send an inquiry, publish a listing, or approve capital.

## Operating expectation

Zero selected products is a valid and preferred outcome when the current market evidence does not pass every gate. The system must never lower thresholds merely to keep an OJT exercise populated.

## 2026-07-19 strict scan result

The first strict local-LLM run completed with zero OJT targets. The observed candidate pool contained low-ticket items and at least one candidate that failed both price-dispersion and worst-case supplier-ceiling gates. The adaptive scan records its selected profile and the exact relaxation in the runtime snapshot and UI; it remains an OJT research target, never a purchase recommendation.
