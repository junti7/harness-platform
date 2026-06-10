# 데이터센터 공급망 투자 레이어 확장 — 현황 대시보드

- 제정: 2026-06-10 | 근거 핸드오프: `datacenter_supply_chain_handoff.md`(Antigravity brain)
- 성격: **candidate discovery / watchlist quality 강화** (실거래 확대 아님 — `CAPITAL_ACTIONS_ENABLED=false`, turtle_gate 불변)
- 상위 규약: `CLAUDE.md`, `docs/governance/DEPLOYMENT_SOURCE_OF_TRUTH.md`
- 추적 AR: **AR-031**

---

## 1. 목표

기존 physical_ai 투자 스택은 GPU/HBM·networking/optics·power/cooling·robotics에 강하다.
이번 확장은 상대적으로 비어 있던 **데이터센터 부품 레이어**(MLCC/passives, PMIC/power-delivery,
high-speed connector/backplane, 차세대 optics, CPU-GPU interconnect)를 evidence→ticker bridge로
촘촘히 메우는 작업이다. 핸드오프의 핵심 권고대로 "소스 추가"보다 **bridge 품질**을 우선했다.

## 2. 현황 (STATUS)

| 항목 | 내용 | 상태 |
|---|---|---|
| Theme bridge 패턴 | MLCC/passives, PDN·VRM·PMIC·busbar, connector/backplane, LPO·800G·1.6T, NVLink·PCIe Gen6 | ✅ 스테이징(branch) |
| Negative bridge 패턴 | passive oversupply, connector/optics ASP 하락 | ✅ 스테이징(branch) |
| 신규 종목(seed) | APH(Amphenol), ARM(Arm Holdings), 6981(Murata), 6762(TDK), 009150(삼성전기) | ✅ 스테이징(branch) |
| Alias 정밀도 | 회사-특정 별칭만. 일반어(`mlcc`/`arm`/`samsung`)는 theme bridge로 분리. `arm` 직접매칭 차단(robot arm 오매칭 방지) | ✅ 적용 |
| 키워드 보강 | 부품/병목 단위 29개 추가(기존 소스 relevance 정밀화, 신규 scraping 아님) | ✅ 스테이징(branch) |
| 신규 RSS 소스 3종 | MLCC/power, connector/optics, interconnect | ⛔ **게이트 대기** (`enabled:false`) |

## 3. 게이트 (활성화 차단 조건)

신규 RSS 소스 활성화 + main 머지 + 프로덕션 배포는 아래 통과 전 **BLOCK**:

1. `legal_review_approve` — 데이터 수집 정책 변경(source 추가, 저작권/약관) 사전 검토
2. `red_team_clear` — 서로 다른 reasoning LLM 2개 이상 cross-verification (기본 Claude+Gemini+Codex)

> 종목 선정은 거래 행동에 영향을 주므로, CEO의 "red_team_clear 전 실행 전면 BLOCK" 원칙을 적용해
> branch에 staging만 하고 프로덕션 배포는 게이트 통과 후 진행한다.

## 4. 효과 시점 (언제부터 보이나)

| 단계 | 트리거 | 예상 시점 |
|---|---|---|
| Bridge 재귀속(기존 evidence) | red_team_clear → main 머지 → 배포 → universe 재생성 | 게이트 통과 당일 (재생성 시 즉시) |
| 신규 부품 종목 universe 편입 | 위 + RSS 소스 `enabled:true` + 수집 사이클 누적(distinct source ≥ gate) | 소스 활성화 후 **수일~약 2주** |

> 현재 피드는 부품 vendor(Murata/TDK/APH 등)를 거의 거명하지 않으므로, 신규 종목은
> 소스가 켜지고 evidence가 쌓이기 전까지 `evidence_count=0`으로 universe에 나타나지 않는다(정상).
> 게이트 전까지 bridge는 기존 evidence의 AVGO/MRVL/COHR/LITE/ANET 등 귀속 정밀도만 개선한다.

## 5. 검증 체크리스트 (배포 후)

- [ ] `scripts/build_trading_universe.py` 재생성 후 부품 계열이 실제 selection evidence 확보 여부
- [ ] `harness_score`가 headline noise가 아닌 distinct source 기반으로 상승하는지
- [ ] 라이브 대시보드(TradingOpsCenter) universe 뷰에 신규 sector 라벨 노출 확인

## 6. 한계 (중요)

현재 universe는 **seed-gated closed registry**다 — `universe_seed.json`에 없는 회사는 evidence가
아무리 많아도 자동 편입되지 않는다. 신규 회사 편입은 **수동 seed 추가 + 게이트**가 필요하다.

이 한계를 보완하기 위해 **자동 후보 발굴기(unmatched-entity miner)**를 구축했다(AR-032):

- 모듈 `core/universe_candidate_miner.py`, 실행 `scripts/mine_universe_candidates.py`
- evidence에서 seed에 없는 상장 회사를 LLM NER로 추출 → 빈도/소스다양성 집계 → 제안 큐 출력
- 출력: `docs/trading/universe_candidate_queue.json` + `UNIVERSE_CANDIDATE_QUEUE.md`(모바일 검토용)
- **발굴은 자동, 편입은 게이트.** 큐는 *제안*일 뿐 seed/거래를 바꾸지 않는다.
  편입은 검토 → `legal_review_approve` + `red_team_clear` + 대표 승인 → seed 편입.
- 단일 소스 스팸 차단(distinct source ≥ min_sources), LLM 미가용 시 빈 큐 fail-safe(허위 후보 금지).
- 권장 cadence: 주 1회(프로덕션 스케줄러 등록은 배포 시 후속).
