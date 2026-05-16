# Copilot Output - Competitor Library Pipeline Plan
# Date: 2026-05-10

---

## Scope

Design a legal-safe competitor intelligence Library pipeline for:

- public-source crawling
- metadata extraction
- scorecards
- customer-memory schema
- Slack/PDF review flow

---

## Core Design

Pipeline:

```text
source registry -> crawl manifest -> metadata extraction -> benchmark normalization -> scorecard -> review packet
```

Allowed:

- public homepages
- pricing pages
- public samples
- help/docs
- public PDFs

Forbidden:

- paywall bypass
- full paid-report storage
- excessive verbatim storage
- ToS/robots violation
- storing sensitive investor fields in customer memory

---

## Proposed Tables

Competitor intelligence:

- `ci_sources`
- `ci_source_urls`
- `ci_fetch_runs`
- `ci_page_snapshots`
- `ci_extracted_facts`
- `ci_competitor_profiles`
- `ci_report_anatomy`
- `ci_scorecard_dimensions`
- `ci_scorecard_scores`

Customer memory:

- `customer_profiles`
- `customer_interest_tags`
- `customer_watchlists`
- `customer_questions`
- `customer_feedback_memory`

Review operations:

- `review_packets`

---

## Scorecard Dimensions

| Dimension | Weight |
| --- | --- |
| Thesis clarity | 15 |
| Decision utility | 20 |
| Evidence/source quality | 15 |
| Economics/supply-chain implication | 10 |
| Watchlist utility | 10 |
| Personalization fit | 10 |
| Readability for non-expert | 10 |
| Legal safety | 10 |

Hard block:

- `legal safety < 4/5`
- `evidence/source quality < 4/5`

---

## Recommended Scripts

- `scripts/ci/register_sources.py`
- `scripts/ci/crawl_public_sources.py`
- `scripts/ci/extract_metadata.py`
- `scripts/ci/build_competitor_profiles.py`
- `scripts/ci/score_artifact.py`
- `scripts/ci/build_review_packet.py`
- `scripts/ci/render_review_pdf.py`
- `scripts/ci/post_review_slack.py`
- `scripts/ci/qa_check_ci_packet.py`
- `scripts/ci/purge_high_risk_content.py`

---

## Integration Note

This output should drive the next engineering sprint after President approval.
