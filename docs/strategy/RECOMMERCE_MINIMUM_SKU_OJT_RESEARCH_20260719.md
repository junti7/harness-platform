# Recommerce Minimum SKU OJT Research

## Decision

Do not ask two novice operators to invent 30 SKU candidates. Begin OJT with three research targets only. These are supplier-interview and cost-analysis candidates, not purchase recommendations.

## Current market snapshot

Observed through Naver Shopping Search API on 2026-07-19. Result counts are search competition/coverage signals, not sales or demand proof.

| Rank | OJT candidate | Search results | 100-result median price | Training purpose |
| ---: | --- | ---: | ---: | --- |
| 1 | 성인 공예·소형부품 수납함 | 959 | 16,240원 | lower apparent competition; evidence, hinge and lock inspection |
| 2 | 모듈형 서랍 정리 트레이 세트 | 8,778 | 12,645원 | bundle economics, dimensions, nesting and breakage |
| 3 | A4 문서 정리함 묶음 | 135,264 | 19,800원 | saturation, volumetric shipping and damage rejection |

## Rejected from the first OJT set

- 케이블 정리 클립: median 1,585원; delivery and labor economics are structurally weak.
- 길이조절 서랍 칸막이: median 3,900원; low ticket and fit-return risk.
- 책상 밑 부착 서랍: median 6,850원; adhesive, load and desk-material return risk.
- 데스크 오거나이저 트레이: 68,553 results; intense brand and commodity competition.

## Automation

- `scripts/run_recommerce_market_research.py` refreshes the shortlist from Naver Shopping Search API.
- Runtime output: `runtime/recommerce/market_research.json` (gitignored).
- CEO may refresh from Harness OS; VP has read-only access.
- The UI shows three guided exercises and explicit rejection reasons.
- No automation purchases inventory, contacts suppliers, creates listings, advertises, or treats result counts as verified demand.

## External evidence

- 국가데이터처 2026년 3월 온라인쇼핑동향: https://mods.go.kr/board.es?act=view&bid=241&list_no=444909&mid=a10301120300
- 제품안전정보센터 안전관리 대상: https://www.safetykorea.kr/policy/targetsSafetyCert
- Naver Shopping Search API live observations are stored only in the runtime snapshot.
