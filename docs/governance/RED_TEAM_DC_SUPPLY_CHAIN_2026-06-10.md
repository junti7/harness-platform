# Red Team — 데이터센터 공급망 확장 + Unmatched-Entity Miner

- 일자: 2026-06-10 | correlation_id: dc-supply-chain-expansion-20260610
- 대상: branch `feat/dc-supply-chain-expansion` (AR-031 bridge/seed/sources, AR-032 miner)
- 참여 (cross-LLM 3): **Claude(Opus 4.8)**, **Gemini(2.5-pro)**, **Codex**
- 판정: **red_team_clear** (3-of-3 clear, 초기 Codex block은 전 항목 remediation 후 재확인 clear)

## 라운드 1 결과

| 모델 | 1차 판정 | 핵심 지적 |
|---|---|---|
| Gemini | clear | (minor) 005930 'samsung' 일반어 direct alias; (minor) miner substring 과잉제외 |
| Codex | **block** | (blocker) 005930 'samsung' direct alias — 009150 추가로 악화; (major) miner 버킷 분리; (major) distinct_sources가 피드 기반(syndication 미차단); (major) 커버리지가 _alias_map 제품/테마어 사용→오제외; (minor) 제목 dedup 없음 |
| Claude | findings | theme map VRM/PMIC→VRT 오귀속; 800g 단어경계; 위 substring/alias 동일 발견 |

## Remediation (커밋 반영)

1. `005930` direct alias에서 bare `samsung` 제거 (회사-특정어만) — **blocker 해소**
2. miner: name→ticker 2-pass 해석으로 동일 회사 버킷 병합
3. miner: 제목 정규화 dedup → distinct_sources/mentions를 제목-dedup 후 산출 (syndication 차단)
4. miner: seed 커버리지를 `_alias_map`에서 분리 → 정식 회사명 + 소규모 회사-동의어(cross-lang/ADR)만 사용. 제품/테마어 오제외 제거
5. miner: 토큰 단위 커버리지 매칭(substring 금지) — `meta`→`Metalenz`, `arm`→`Armada` 오제외 방지
6. theme map: 칩단 VRM/PMIC/PDN(seed 미보유) 매핑 제거 — miner가 발굴; rack/infra 전력만 VRT/GEV/PWR
7. theme map: `800g`/`1.6t` 단어경계

## 라운드 2 (재확인)

- **Codex: VERDICT clear** — 5개 지적 전부 `resolved` 확인.
- 오프라인 단위검증 통과: 제품어/substring 오제외 없음, seed 회사 정상 제외, MPWR 버킷 병합(ticker merge), syndication 제목 dedup(distinct=2).

## 잔여 리스크 (residual)

- `distinct_sources`는 제목-dedup 후에도 **피드 단위**다. 동일 publisher가 서로 다른 헤드라인으로
  여러 Google News 쿼리 피드에 걸리면 distinct가 다소 과대평가될 수 있다. 단 본 산출물은
  **read-only 제안 큐**이고 편입은 사람+게이트를 거치므로 over-inclusion 리스크는 낮다.
  publisher 단위 dedup은 향후 개선 과제로 둔다.

## 다음 게이트

- 신규 RSS 소스 활성화(`enabled:true`)는 별도 **legal_review_approve** 필요(데이터 수집 정책 변경).
- 실거래는 무관 (CAPITAL_ACTIONS_ENABLED=false, turtle_gate 불변).
- 본 red_team_clear는 **코드/문서/유니버스 로직** 변경에 대한 것이며, main 머지 + 배포 진행 가능.
