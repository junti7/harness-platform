패킷 기준으로 코드/테스트를 즉시 재검토하고, 각 안전 게이트가 실제로 강제되는지 확인하겠습니다. 먼저 핵심 아티팩트와 테스트를 병렬로 읽습니다.

핵심 판단은 브리지 구현 강제조건에 달려 있어서, 관련 함수/명령부만 정밀 추출해 확인하겠습니다.

## 1. Objective
Smartfarm OpenClaw procurement 재검토 완료. **Verdict: BLOCK** (핵심 안전 블록 1개 미충족).

## 2. Findings
- **통과:** 검색결과 URL 차단은 코드 강제됨 (`scripts/smartfarm_market_research.py`의 `_is_direct_http_url`, `SEARCH_RESULT_HOSTS`; 검증 실패 처리 포함).
- **통과:** recommended 후보는 evidence URL 2개 이상 필수 강제됨 (`validate_report`에서 `len(set(evidence_urls)) < 2` 차단).
- **통과:** recommended/alternate의 모든 required check에 대해 `verified` 상태 + direct evidence URL 강제됨 (`unresolved checks`/`lacks direct check evidence` 차단).
- **통과:** stale observation 차단됨 (`observed_at` 14일 초과 또는 미래 과도치 차단).
- **통과:** ESP32 + Arduino framework + ADC1 아키텍처 명시됨 (research plan `controller_architecture` 및 카탈로그 `esp32_adc1_compatibility` check).
- **통과:** 6개 카테고리 유지됨 (`configs/smartfarm/procurement_items_v1.json` 6 items, 테스트에서도 6개 확인).
- **미통과:** “research cannot cart/order/pay”가 **머신 강제로 완결되지 않음**. 동일 브리지에 `coupang-cart`, `coupang-pay-approve` 명령과 실행 경로가 그대로 노출/동작함 (`scripts/openclaw_codex_bridge.py`).

## 3. Risks
- 연구 세션 중 오퍼레이터 실수/오용으로 장바구니/결제 실행 가능.
- “Research remains read-only” 체크를 운영 규칙 문구에만 의존하고 기술적 차단이 부족함.

## 4. Recommended Next Actions
1. `openclaw_codex_bridge.py`에 **명령 권한 게이트** 추가: research context에서는 `coupang-*` 실행을 하드 블록.
2. `coupang-pay-approve`에 **승인 토큰/상태 검증(2-step machine check)** 없으면 무조건 실패하도록 변경.
3. 테스트 추가: research task 실행 컨텍스트에서 cart/pay 명령 호출 시 반드시 차단되는지 검증.