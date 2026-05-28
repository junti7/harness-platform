# Investment Thesis — TSM + MU
# Date: 2026-05-28 | Version: 1.0
# Status: CEO approval_request (investment_thesis_approve 필요)
# Approval: PENDING

---

## 개요

Harness 리서치 파이프라인(Layer 1) 선정 → Turtle Trading S2 브레이크아웃 신호(Layer 2) 통과 종목.
이 thesis는 2026-05-28 Harness 순수 실적 측정 베이스라인 설정 이후 **첫 번째 진입 후보**다.

---

## Harness Layer 1 — 리서치 기반 선정 근거

### TSM (Taiwan Semiconductor Manufacturing Company)

| 항목 | 내용 |
|------|------|
| harness_score | 9 / 10 |
| 섹터 | 반도체 파운드리 |
| 기술 신뢰도 | Mature — 2nm 양산 시작. AI 칩 유일한 첨단 생산처 |
| 시장 채택 | NVDA, AMD, Apple, Broadcom 전량 TSM 의존. 병목 자산 |
| 최근 카탈리스트 | 2026년 Q1 매출 $35.9B (YoY 35%), 그로스마진 66.2% |
| 경쟁 포지션 | 삼성/인텔 대비 2nm에서 2~3년 선도. 대체 불가 |
| 리스크 | 대만 지정학, 고객 자체 칩 설계 확대 |

### MU (Micron Technology)

| 항목 | 내용 |
|------|------|
| harness_score | 8 / 10 |
| 섹터 | AI 메모리 반도체 (HBM) |
| 기술 신뢰도 | Growing — HBM3E 전량 완판, HBM4 선납 계약 |
| 시장 채택 | NVDA Vera Rubin 공급사. AI GPU에 HBM 필수 |
| 최근 카탈리스트 | FY2026 Q2 매출 $23.86B, EPS $12.07 사상 최대. 시총 $1T 달성 |
| 경쟁 포지션 | HBM 시장 점유율 21% (SK하이닉스 62%). 빠른 추격 중 |
| 리스크 | 반도체 사이클성, SK하이닉스 대비 HBM 점유율 열세 |

---

## Harness Layer 2 — Turtle Trading 기술 신호

### TSM — System 2 브레이크아웃

| Turtle 파라미터 | 값 |
|---|---|
| entry_system | S2 (55일 최고가 돌파) |
| entry_signal_date | 2026-05-28 |
| current_price | $422.70 |
| s2_high (55일) | $421.90 |
| breakout_margin | +$0.80 (+0.2%) |
| atr_value (20일) | $14.03 |
| suggested_shares | 70주 |
| position_value | $29,589 |
| stop_loss_price | $394.63 (진입가 - 2×ATR) |
| risk_usd | $982 |
| risk_pct | 0.991% |
| exit_system | S2 (20일 최저가 이탈) |

### MU — System 2 브레이크아웃

| Turtle 파라미터 | 값 |
|---|---|
| entry_system | S2 (55일 최고가 돌파) |
| entry_signal_date | 2026-05-28 |
| current_price | $928.30 |
| s2_high (55일) | $916.49 |
| breakout_margin | +$11.81 (+1.3%) |
| atr_value (20일) | $60.43 |
| suggested_shares | 16주 |
| position_value | $14,853 |
| stop_loss_price | $807.43 (진입가 - 2×ATR) |
| risk_usd | $967 |
| risk_pct | 0.976% |
| exit_system | S2 (20일 최저가 이탈) |

---

## 포트폴리오 구성 (진입 후)

| 항목 | TSM | MU | 합계 |
|------|-----|----|------|
| 포지션 가치 | $29,589 | $14,853 | $44,442 |
| 비중 | 29.9% | 15.0% | 44.9% |
| 리스크 | $982 (0.99%) | $967 (0.98%) | $1,949 (1.97%) |
| 잔여 현금 | — | — | ~$54,558 (55.1%) |

총 포지션 리스크: 2.0% — Turtle 룰(개별 1%) 준수. 남은 자금은 신규 신호 대기.

---

## TurtleGate 체크리스트

### TSM
- [x] 1. 진입 신호: S2 (55일 최고가 $421.90 돌파 → $422.70)
- [x] 2. ATR: 20일 ATR = $14.03 명시
- [x] 3. 포지션 리스크: 0.991% ≤ 1% 확인
- [x] 4. 손절가: $394.63 (= $422.70 - 2×$14.03) 사전 계산
- [x] 5. 청산 시스템: S2 명시
- [ ] 6. Pre-Mortem: 작성 필요 (paper trading — 간소화 허용)
- [ ] 7. CEO investment_thesis_approve: **PENDING**

### MU
- [x] 1. 진입 신호: S2 (55일 최고가 $916.49 돌파 → $928.30)
- [x] 2. ATR: 20일 ATR = $60.43 명시
- [x] 3. 포지션 리스크: 0.976% ≤ 1% 확인
- [x] 4. 손절가: $807.43 (= $928.30 - 2×$60.43) 사전 계산
- [x] 5. 청산 시스템: S2 명시
- [ ] 6. Pre-Mortem: 작성 필요 (paper trading — 간소화 허용)
- [ ] 7. CEO investment_thesis_approve: **PENDING**

---

## Pre-Mortem (간소화 버전 — Paper Trading)

### Worst-Case 시나리오

| 시나리오 | 확률 | 최대 손실 | 복구 방법 |
|----------|------|-----------|-----------|
| TSM: 대만 지정학 리스크 급등 | 10% | -$982 (손절) | 신호 재진입 대기 |
| MU: 반도체 사이클 급반전 | 15% | -$967 (손절) | 신호 재진입 대기 |
| 양쪽 동시 손절 | 5% | -$1,949 | 나머지 $54,558 현금 보존 |

Detection Trigger: 손절선 이탈 시 즉시 청산. "조금만 더 기다리자" 없음.

---

## Harness 실적 측정 기준점

- **베이스라인 설정일**: 2026-05-28
- **시작 포트폴리오 가치**: $99,182.79 (기존 포지션 청산 완료 후)
- **이 thesis 진입 후**: ~$44,442 투자 / ~$54,558 현금 대기
- **실적 추적 시작**: 이 진입 시점부터가 Harness 순수 실적

---

## 승인 요청

CEO님께 `investment_thesis_approve` 요청드립니다.
승인 시 시장 개장 후 즉시 paper trading 매수 주문 실행.

```
target_type: investment_thesis
approval_type: investment_thesis_approve
tickers: [TSM, MU]
requested_by: Harness Research Agent
requested_at: 2026-05-28
```

---

## 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2026-05-28 | 1.0 | 초안 — Harness 리서치 파이프라인 Layer 1 + Turtle Layer 2 통합 thesis |
