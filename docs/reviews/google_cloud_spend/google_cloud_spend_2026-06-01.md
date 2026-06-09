# Google Cloud Spend Analysis - 2026-06-01

## Verdict
- 가장 유력한 원인: `YouTube Data API v3` 사용. 추정 quota units=11232, quota exceeded runs=0.
- Gemini 사용은 보조 요인 수준. calls=58, input_tokens=51834, output_tokens=18250.

## YouTube Evidence
- runs=4
- channel_calls=32
- search_queries=80
- estimated_units=11232
- api_new_items=1023
- quota_exceeded_runs=0

## Per Run
- 2026-06-01 00:50:30 | channels=8 | queries=20 | units~=2808 | api_new=361 | quota_exceeded=no
- 2026-06-01 06:52:12 | channels=8 | queries=20 | units~=2808 | api_new=308 | quota_exceeded=no
- 2026-06-01 12:53:50 | channels=8 | queries=20 | units~=2808 | api_new=0 | quota_exceeded=no
- 2026-06-01 18:55:12 | channels=8 | queries=20 | units~=2808 | api_new=354 | quota_exceeded=no

## Billing Export Status
- 로컬 환경에서는 GCP Billing Export / BigQuery SKU 데이터를 직접 조회하지 못했습니다.
- 따라서 이 리포트는 코드/로그/DB 기반의 강한 정황 분석입니다.
