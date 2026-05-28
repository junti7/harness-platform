# Kill Criteria
# Version: 2.0
# Date: 2026-05-10

---

## 1. Purpose

Harness must avoid continuing because the automation is interesting rather than because readers care.

---

## 2. 30-Day Criteria

Continue if:

- 4 weekly issues published, and
- 50 free subscribers, and
- 1 paid subscriber or clear paid intent

Acceptable learning:

- paid subscriber 0, but strong replies/shares and clear paid hesitation data

Pause or pivot if:

- fewer than 2 issues published
- no subscriber capture path
- fewer than 20 free subscribers after 4 issues
- paid tier never shown
- all work is internal documentation or infrastructure

---

## 3. 90-Day Criteria

Continue if:

- 12 issues published
- 300 free subscribers, or
- 10 paid subscribers, or
- meaningful inbound custom memo interest

Pivot if:

- readers like free content but no one pays
- open/share/reply rates are weak
- content production remains mostly manual
- topic is too broad or too technical for target readers

---

## 4. Non-Negotiable Rule

No amount of document quality, agent architecture, or Slack automation overrides weak reader evidence.

---

## 5. B2I 트레이딩 중단 기준 (2026-05-25 추가 — AR-018 조건6)

### 5-1. 계좌 손실 기반 자동 중단

| 트리거 | 조치 |
|--------|------|
| 계좌 누적 손실 -20% 이상 | 전량 청산 + 30일 거래 중단 |
| 단일 포지션 손실 -15% 이상 | 해당 포지션 즉시 청산 |
| 월 손실 -10% 이상 | 신규 진입 금지 + CEO 리뷰 |
| $7,000 기준 잔고 $3,500 이하 | 강제 중단 + CEO 확인 없이 재개 불가 |

### 5-2. 거시 트리거 기반 자동 청산 (Macro Kill Switch)

아래 이벤트 중 하나라도 발생하면 **모든 포지션 즉시 청산 + 신규 진입 60일 금지**:

| 트리거 | 기준 |
|--------|------|
| 반도체 수출 규제 신규 발표 | 미국·일본·네덜란드 등 주요국의 대중국 반도체 장비/칩 수출 규제 신규 발동 또는 확대 |
| SOXX 급락 | Philadelphia Semiconductor Index(SOXX) 고점 대비 -25% 이상 하락 |
| NVIDIA 단일 급락 | NVDA 5거래일 내 -20% 이상 하락 |
| Physical AI ETF 동반 급락 | Watchlist 내 ETF 3개 이상이 동시에 20일 신저가 갱신 |
| 미·중 갈등 격화 | 대만 해협 군사적 긴장 고조 (공식 뉴스 매체 3개 이상 보도) |
| 글로벌 금리 급등 | 미국 10년물 국채 수익률 1개월 내 +100bp 이상 상승 |
| Harness 운영 현금 위기 | 월 운영비 충당 가능 잔고 3개월 미만 |

### 5-3. B2I 사업 모델 자체 중단 기준

- B2I 운용 6개월 후 투자 수익이 LLM API 비용 합계를 초과하지 못한 경우 → B2C 재활성화 검토
- B2I + 교육 컨설팅 양쪽 모두 수익 0이 90일 이상 지속 → 대표 전략 재검토 필수

### 5-4. 감지 및 알림

- Business Risk Management(BRM) Agent가 매일 위 트리거를 모니터링
- 트리거 발동 시 `#exec-president-decisions` 즉시 알림
- Watchman이 `risk_escalation_note` 발행 및 AR tracker 등록
