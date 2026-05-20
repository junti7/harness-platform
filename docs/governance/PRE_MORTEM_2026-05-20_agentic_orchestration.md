# PRE-MORTEM — Agentic Orchestration 전면 개편

**Date:** 2026-05-20
**Author:** Chief of Staff (Codex/Jarvis) drafted by Claude (Opus 4.7)
**Protocol:** `docs/governance/PRE_MORTEM_PROTOCOL.md`
**Gate:** `pre_mortem_approve` ✅ 대표 confirm 2026-05-20
**Triggering Red Team:** `docs/governance/RED_TEAM_LOG.md` 2026-05-20 entry (Claude+Gemini+Codex, 2 CONDITIONAL_PROCEED / 1 BLOCK, 5 non-negotiables)

---

## 1. 의사결정 요약

harness-platform의 구조를 pipeline 중심에서 **agentic orchestration**(persona 기반 에이전트 + Slack-as-workspace + 자율 CC + episodic memory)으로 전면 개편한다. 대표 지시로 이 개편을 **최우선 순위**로 격상하고, 기존 CLAUDE.md의 *Business Reality Constraint*(초기 30일 weekly issue 발행 + 첫 paid subscriber 우선)를 일시적으로 override한다.

이 결정은 high-impact governance change이므로 PRE_MORTEM_PROTOCOL §2(데이터 수집 정책 변경/구조 전환에 준함) + 대표 자본(인간 시간) 재배치에 해당하여 pre-mortem을 요구한다.

---

## 2. 최악 시나리오 (5개)

### S1. Process Capture — 매출 검증 없이 runway 소진
8주간 에이전트 인프라만 쌓고 weekly issue 0회, 무료 구독자 증가 0, paid subscriber 0. 사업 가설(한국어 Physical AI 구독)이 검증되지 않은 채 동기/시간/비용이 고갈된다. CLAUDE.md §1이 가장 강하게 경고하는 "pipeline sophistication을 결과물 가치로 착각" 함정.

- **발생 확률:** High
- **최대 손실:** 8주 founder 시간 + 검증 기회비용. 회사 존속 자체 위협 (가장 큰 손실).
- **회복 가능성:** Partially recoverable — 인프라 산출물은 남지만 소실된 시간/시장 타이밍은 회복 불가.

### S2. LLM 비용 스파이럴
autonomous CC + multi-persona "유기적 토론"이 단일 CEO order당 20~50회 LLM 호출로 증폭. `DAILY_COST_LIMIT_USD`는 일일 총량 게이트일 뿐 per-order/per-conversation cap이 없어 예산이 조용히 초과된다.

- **발생 확률:** Medium-High
- **최대 손실:** 월 LLM 비용이 예측 불가하게 급증 (예산 대비 수배). 재무 리스크 임계값(AGENTS.md §3.16: 일일 비용 80% 초과) 상시 초과.
- **회복 가능성:** Recoverable — cap 도입 시 즉시 차단 가능. 단 cap이 없으면 인지 지연.

### S3. Governance Gate 침식 (가장 위험)
persona 이름이 "Red Team / Legal(KITT) / QA"인 단일 LLM 에이전트가, CLAUDE.md §6이 금지한 *cross-LLM 게이트의 self-review 위장*으로 작동. 단일 모델이 통과시킨 법률 오류·사실 오류가 외부 발행되어 평판/법적 손상.

- **발생 확률:** Medium (구조상 혼동 유발 → 운영 중 발생 가능성 상승)
- **최대 손실:** 표시광고법/자본시장법 위반성 표현 외부 노출, 독자 신뢰 붕괴, 환불/법적 분쟁.
- **회복 가능성:** Partially recoverable — 발행물 회수는 가능하나 신뢰/법적 노출은 회복 어려움.

### S4. PII / 기밀 유출
autonomous Slack 채널 생성 + episodic memory(일기)가 subscriber 데이터, 대표/부대표 의사결정, 기밀 사업 메모를 보존 정책·접근 통제·삭제 정책 없이 축적. PIPA 위반 또는 유출.

- **발생 확률:** Medium
- **최대 손실:** PIPA 위반 과징금/신고, subscriber 신뢰 손상, 기밀 전략 노출.
- **회복 가능성:** Unrecoverable (유출 발생 시) — 데이터는 회수 불가.

### S5. 복잡성 디버그 사망 (1인 운영 한계)
multi-agent 시스템이 1인이 디버그하기엔 너무 복잡해져, orchestrator 정지·무한 루프 같은 silent failure가 인지되지 않음. CLAUDE.md §8이 "artifact quality blocker"로 규정한 daily ops brief 불안정이 재현·악화.

- **발생 확률:** Medium-High
- **최대 손실:** 운영 신뢰성 붕괴, 자동화 전체 마비, 디버깅에 founder 시간 추가 소진.
- **회복 가능성:** Recoverable — 단 단순성으로 롤백해야 하므로 개편 투자 일부 손실.

---

## 3. 종합 손실/확률 매트릭스

| 시나리오 | 확률 | 최대 손실 | 회복 가능성 |
|---|---|---|---|
| S1 Process Capture | High | 회사 존속 위협 | Partial |
| S2 비용 스파이럴 | Med-High | 예산 수배 초과 | Recoverable |
| S3 Gate 침식 | Medium | 법적/평판 손상 | Partial |
| S4 PII 유출 | Medium | PIPA 위반/유출 | Unrecoverable |
| S5 복잡성 사망 | Med-High | 운영 마비 | Recoverable |

---

## 4. Mitigation (사전 차단 조치)

각 mitigation은 Phase 0 Charter에 강제 조항으로 편입한다.

- **M1 (→S1):** Kill-criteria + 2주 체크포인트. Phase 1 종료 시 (a) weekly issue cadence 유지 실패, (b) 무료 구독자 증가 0, (c) 누적 LLM 비용 cap 초과 중 하나라도 발생 시 개편 중단·재평가. **개편 기간에도 weekly issue 발행은 병행 유지** (완전 중단 금지).
- **M2 (→S2):** per-order LLM 비용 cap + active 채널 수 상한 + 주간 founder 시간 cap을 Charter에 명시. cap 초과 시 `expensive_run_approve`(신규 내부 게이트) 또는 자동 중단.
- **M3 (→S3):** **Persona ≠ Gate 조항.** persona "Red Team/Legal/QA"는 팀 산출물만 생산하고, 동명의 CLAUDE.md 거버넌스 게이트(`red_team_clear`/`legal_review_approve`/`qa_clear`)를 *충족하지 않는다*. 게이트는 기존 cross-LLM 절차(AGENTS.md §3.8/§3.11/§3.14A) 유지.
- **M4 (→S4):** Slack 채널·agent memory의 PII/기밀 분류·보존·접근·삭제 정책을 Charter + `SLACK_CHANNEL_CREATION_LOG.md` 스키마에 포함. subscriber 평문 데이터의 채널/일기 기록 금지(기존 AGENTS.md §3.14 규칙 계승).
- **M5 (→S5):** 채널 생성 honor-system 금지 → `scripts/check_slack_channel_log.py` 일일 reconciliation. orchestrator heartbeat/타임아웃 모니터링은 기존 ops-incidents 경보에 연결. Phase는 한 번에 하나씩, 이전 Phase 안정화 후 진행.

---

## 5. Detection Trigger (실패 인지 신호)

| 신호 | 측정 위치 | 대응 |
|---|---|---|
| 2주간 weekly issue 0회 | BizOps goal_health_brief | 즉시 개편 중단, issue 발행 복귀 |
| 무료 구독자 증가율 0 (Phase 1 종료) | subscriber_snapshots | 2주 체크포인트 재평가 |
| 일일 LLM 비용 cap 초과 | cost_alerts (core.cost_alerts) | 자동 중단 + risk_escalation_note |
| 로그 없는 Slack 채널 발견 | check_slack_channel_log.py (일일) | 채널 동결, 생성자 persona 추적 |
| 단일 LLM이 cross-LLM 게이트로 기록된 흔적 | red_team / legal audit trail | 발행 차단, 게이트 재실행 |
| daily ops brief 연속 실패 | launchd job 모니터 | 개편 일시정지, 단순성 롤백 검토 |

---

## 6. Residual Risk (잔여 리스크)

Mitigation 적용 후에도 남는 리스크:

- 개편 자체가 매출에 직접 기여한다는 보장은 없음 (S1은 확률 저감일 뿐 제거 불가).
- 1인 운영에서 multi-agent 디버깅 부담은 구조적으로 상존.
- 대표의 "future of company depends on it" 판단은 **근거 기반 가설이 아니라 전략적 베팅**임을 명시적으로 수용해야 함 (Codex/Gemini non-negotiable 지적).

---

## 7. 대표 Confirm 요청 사항

이 pre-mortem을 근거로 대표는 다음을 명시적으로 confirm해야 진행 가능:

1. Business Reality Constraint override는 **일시적·고위험 예외**이며, weekly issue 발행은 병행 유지한다.
2. 2주 체크포인트에서 kill-criteria 충족 시 개편을 중단/롤백하는 데 동의한다.
3. "future of company depends on it"은 evidence가 아니라 전략적 베팅임을 수용한다.

대표 confirm 기록:

```
python scripts/openclaw_codex_bridge.py record-decision \
  research_report <id> approved pre_mortem_approve \
  --reason "pre_mortem: docs/governance/PRE_MORTEM_2026-05-20_agentic_orchestration.md"
```

---

*이 문서 없이는 agentic orchestration 개편의 high-impact gate를 통과할 수 없다. 대표 confirm 전까지 Phase 0 산출물은 draft 상태로만 존재한다.*
