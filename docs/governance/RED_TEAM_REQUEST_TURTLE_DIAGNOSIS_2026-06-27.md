# Red Team Request — Turtle 자동매매 시스템 진단 (CEO 주문)

> 일자: 2026-06-27 | correlation_id: turtle-system-diagnosis-20260627 | AR: AR-20260627-003
> **트리거: CEO(junti7) 명시 주문** — BASIC RULE(2026-06-20)상 red-team은 CEO 주문 시에만 수행. 본 건은 충족.
> 대상 진단: `docs/trading/TURTLE_SYSTEM_DIAGNOSIS_2026-06-27.md`
> 동반 Pre-Mortem: `docs/governance/PRE_MORTEM_2026-06-27_turtle_paper_to_live.md`
> 상태: **의제 등록 완료 — 실행 대기.** CEO의 "실행" 지시 시 `scripts/redteam_review.sh`로만 구동.

---

## 운영 제약 (메모리 규칙 — 필수 준수)

- **참여 모델 = Codex + GitHub Copilot CLI** (cross-LLM 2). **Gemini CLI는 영구 불가**(IneligibleTierError).
  2-clear 불가 시 third opinion 대신 **CEO confirm**으로 중재. (메모리 `project_gemini_cli_unavailable`)
- **실행 경로:** `scripts/redteam_review.sh` **read-only 래퍼로만**. codex read-only / copilot `--available-tools ''`.
  **red-team에 git 쓰기권한 절대 금지.** (메모리 `redteam_readonly_wrapper`, `persona_pause`)
- **라운드 상한 r5.** 심각 Major 아니면 r5까지만. (메모리 `redteam_round_cap`)
- 동일 모델 self-review를 cross-LLM으로 위장 금지.

---

## 검증 대상 (Scope)

1. `scripts/turtle_auto_trader.py` — 진입/청산/포지션 관리 로직
2. `scripts/alpaca_paper_trading.py` — 신호 계산, 포지션 사이징, ATR, 게이트
3. 진단 리포트 F1~F6의 사실성·재현성
4. Pre-Mortem 시나리오 1~3의 확률·완화책 타당성

---

## Red Team 프롬프트 (cross-LLM 공통)

> 아래 6개 Finding은 비서실장(Claude)의 1차 진단이다. 각 Finding에 대해 **confirm / refute / refine** 판정과
> 근거(코드 라인·데이터)를 제시하라. 놓친 결함(특히 자본 손실로 직결되는 것)을 추가하라.

- **F1 (롱 전용):** `should_enter()`가 `breakout_long`에만 진입, `breakout_short` 전량 무시. 양방향 시장에서
  수익 절반을 비활성화한다는 진단이 맞는가? 롱 전용을 유지한다면 어떤 추세필터가 필수인가?
- **F2 (상관집중):** SMH·SOXX 동시 보유 = 사실상 동일 베팅 2배. 상관 한도 부재가 6/08 동시 손절의 원인인가?
  적정 상관/유닛 상한 수치는?
- **F3 (리스크 2×):** `shares=(계좌×1%)/ATR`로 1N 사이징하나 손절은 2N. 실효 손절 리스크가 2%(규정 ≤1%의 2배)이고
  `turtle_gate_check`가 1N으로 잘못 측정한다는 진단이 맞는가? 원조 Turtle 정의와 회사 규정 충돌을 어떻게 정리할 것인가?
- **F4 (휩쏘 재진입):** 6/08 손절 → 6/22~26 더 높은 가격 재매수 → 재손절. 추세필터/돌파스킵 부재가 원인인가?
- **F5 (장부 불일치):** diary 청산 0건 / `positions.json` 18일 stale vs 브로커 실청산. 통합원장 부재 + 멀티-writer가
  실자본에서 일으킬 최악 결과는? circuit breaker 설계 타당성은?
- **F6 (표본/현금):** 3주·12회 매매로 전략 판정 불가하다는 한계 인정이 적절한가? 현금 54% 미투입의 의미는?

**추가 질문:** P0·P1 수정 없이 실자본(capital_action) 전환 시 가장 큰 단일 위험은? `turtle_gate_clear`에
포트폴리오 합산 상관 리스크 점검을 추가해야 하는가?

---

## 판정 기록란

| 라운드 | Codex | Copilot | 비고 |
|---|---|---|---|
| r1 | (대기) | (대기) | |

- 최종 판정: `red_team_clear` / `red_team_block` / `CEO confirm` (2-clear 불가 시) — **(대기)**
- 결과는 본 문서 + `docs/governance/RED_TEAM_LOG.md`에 기록.
