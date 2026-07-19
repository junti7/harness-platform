# Recommerce LLM Conservative OJT Selection Policy

## Purpose

Two novice operators do not manually invent SKU candidates. The system may present an OJT research target only when a local LLM reviews current Naver Shopping price evidence and deterministic hard gates independently pass.

This is not a purchase, listing, supplier, or demand recommendation. It is a narrowly scoped instruction to investigate a product further without spending money.

## Data flow

`Naver Shopping Search API → safe-category / restricted-keyword filter → high-similarity competitor evidence → local Ollama LLM → deterministic hard gates → OJT research target or selection hold`

The local LLM is required. If it is unavailable, malformed, or cannot select a defensible target, the process fails closed: no candidate is shown. A human cannot manually override a candidate into the OJT list.

## Required gates

| Gate | Conservative rule | Failure result |
| --- | --- | --- |
| Safety scope | Household organization categories only; restricted/safety-sensitive terms excluded | Reject |
| Ticket price | Comparable lower-quartile price at least 15,000 KRW | Reject |
| Comparable evidence | At least 5 high-similarity price samples across at least 3 malls | Reject |
| Price dispersion | 75th/25th percentile price ratio no higher than 1.60 | Reject |
| LLM review | Local LLM score at least 75/100 with a data-bound reason | Reject |
| Identity | Product ID and image both present | Reject |
| Worst-case economics | At least 3,000 KRW allowable supplier cost remains after conservative cost model | Reject |

Worst-case cost model: 15% platform fee, 8% return reserve, 10% advertising reserve, 20% target contribution, 4,000 KRW shipping, and 2,000 KRW labor/packaging. The OJT sales-price anchor is the comparable lower-quartile price, not a markup on a wholesale price.

## Explicit non-authorizations

- Naver Shopping Search API does not include actual shipping cost, supplier stock, wholesale terms, defect rate, or return responsibility.
- Therefore a selected item is `blocked_until_supplier_and_shipping_evidence`.
- The UI provides only a read-only market link, an empty evidence checklist, arithmetic review, and a copy-only inquiry draft. It cannot order inventory, send an inquiry, publish a listing, or approve capital.

## Operating expectation

Zero selected products is a valid and preferred outcome when the current market evidence does not pass every gate. The system must never lower thresholds merely to keep an OJT exercise populated.

## 2026-07-19 live result

The first local-LLM run completed, but selected zero OJT targets. The observed candidate pool contained low-ticket items and at least one candidate that failed both price-dispersion and worst-case supplier-ceiling gates. The correct state is selection hold, not a forced recommendation.
