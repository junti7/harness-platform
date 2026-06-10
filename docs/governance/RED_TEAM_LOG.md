# RED-TEAM LOG

---

## 2026-05-24 AR-029 교육 컨설팅 메인 격상 Red Team — Claude Pass

**Participating LLM:** Claude (claude-sonnet-4-6) — 1-of-3 완료
**Verdict (Claude):** `APPROVE with conditions`
**Scope:** 교육 컨설팅 메인 격상 결정 전반 (MASTER_PLAN·MARKET_RESEARCH·RESEARCH_UNIVERSE·Pre-Mortem)
**correlation_id:** edu-consulting-20260524
**상태:** Gemini + Codex 검토 대기 — `red_team_clear` 미기록

### Claude 판정 매트릭스

| 검토 항목 | 판정 | 세부 |
|---|---|---|
| ① 사실 정확성 (소스·수치) | CONCERN | 아래 주석 참조 |
| ② 전략 논리 (타겟·차별화·수익 모델) | APPROVE | 전반적으로 타당, 조건부 |
| ③ Pre-Mortem 완전성 | APPROVE | 5개 시나리오 적절 |
| ④ 법률·규제 리스크 | APPROVE | 학원법 조건 올바르게 식별 |
| ⑤ 누락된 중대 리스크 | CONCERN | 3개 추가 지적 |

**전체 판정: APPROVE (조건 3개)**

---

### 사실 정확성 CONCERN 내역

1. **AI 의존성 연구 상관계수(-0.68):** MARKET_RESEARCH에 `media`(뉴시스 보도) 근거로 표기했으나, 영국 연구의 1차 학술지 출처를 직접 확인하지 않음. 수치는 타당해 보이나 "학술지 인용" 레벨로 격상 전 1차 논문 확인 필요. ⚠️ 고객-facing 콘텐츠에 이 수치 단독 인용 금지 (1차 확인 후 사용).
2. **통계청 사교육비조사 hard$ 인용:** RESEARCH_UNIVERSE Class 3에서 언급했으나 구체적 수치(가구당 연평균)를 인용하지 않음. 실제 가격 설정 근거로 쓰려면 실제 숫자 확보 필요.
3. **글로벌 AI 교육 시장 $5~8B(2025):** `vendor-estimate`으로 올바르게 표기됨. 절대 금액 신뢰 말 것 — 방향성만 사용 원칙 유지 확인.

→ 심각한 허위 정보 없음. 근거 자세 표기 원칙은 지켜짐.

---

### 전략 논리 — APPROVE 근거

- **"조사≡제품" 논리:** 타당. Multi-LLM 인텔리전스 파이프라인을 교육 도메인에 재지향하는 것은 구조적으로 합리적이며, 기존 자산(collector, Tier 1~4) 재활용 효율이 높음.
- **반의존 포지셔닝:** "AI를 더 빨리 쓰는 법"이 포화된 시장에서 실재하는 빈틈. AI의존성 연구가 정당화.
- **초·중등 학부모 타겟:** 결제 주체·통증·VP 적합성 3개 동시 충족. 타겟 스코어링 논리 수용.

---

### 누락된 리스크 (CONCERN) — Pre-Mortem 보완 권고

**리스크 A — 구독 단가 대비 LLM 비용 역마진:**
예산 $100/월, 예상 LLM 실소비 $35~60/월. 만약 구독자 10명이 월 ₩20,000(=$15)씩 내면 총 매출 $150이나 LLM 비용 $60 + 운영비를 감안하면 이익률이 매우 낮음. **구독자 N명 × 가격 P원이 LLM 비용을 넘으려면** 최소 구독자 수·가격 조합을 미리 모델링해야 함. 현재 문서에 이 계산 없음.

**리스크 B — CAC(고객 획득 비용) 불명확:**
첫 50명 익명 학부모를 어떻게 찾을지 구체적 채널·비용이 없음. 맘카페 유기적 유입(법률 제약), 인스타/유튜브 유료 광고(표시광고법 검토 필요), 유튜브 콘텐츠 SEO(시간 필요). Pre-Mortem에 "분산 리스크"는 있지만 CAC 리스크(고객을 못 찾는 것)는 별도 시나리오로 없음.

**리스크 C — 뉴스레터 Backend vs 교육 파이프라인 도메인 충돌:**
Physical AI ETF 투자 신호를 수집하는 파이프라인과 "부모를 위한 AI 교육 best practices" 콘텐츠를 수집하는 파이프라인은 **소스 도메인이 다름**. 현재 `edu_consulting.json`은 교육 도메인 RSS를 등록했지만, `physical_ai.json`은 arXiv 로보틱스·ETF 신호를 수집. 두 목적이 하나의 파이프라인에서 충돌 없이 공존할 수 있는지 아키텍처 설계 명시 필요.

---

### Claude 권고 (APPROVE 조건)

1. **구독 경제 계산:** 구독자 수 × 가격 × LLM 비용 손익분기 시뮬레이션 작성 후 MASTER_PLAN 추가
2. **CAC 채널 구체화:** Pretotyping 설계 시 "어디에 가짜문을 내건다"를 명시 (채널 + 예상 획득 비용)
3. **파이프라인 이중 도메인 분리 설계:** 교육용 수집기(edu domain)와 Physical AI 수집기(B2I domain)를 명시적으로 분리 관리

---

*Claude 검토 완료: 2026-05-24 | 다음: Gemini 검토 → Codex 검토 → 2-of-3 판정*

---

### Claude 조건 3개 — 보완 문서 작성 완료 (2026-05-24)

> CEO 지시: "RED team의 진단이 모두 clear되지 않으면 시작하면 안된다."
> 원칙 등록: red_team_clear 전 모든 실행 BLOCK.

| 조건 | 보완 문서 | 상태 |
|---|---|---|
| A — 구독 단가 BEP 시뮬레이션 | `docs/education/EDU_UNIT_ECONOMICS.md` | ✅ 완료 |
| B — CAC 채널·비용 구체화 | `docs/education/EDU_CAC_PLAN.md` | ✅ 완료 |
| C — 파이프라인 도메인 분리 설계 | `docs/education/EDU_PIPELINE_ARCHITECTURE.md` | ✅ 완료 |

**BEP 요약 (조건 A):** ₩19,900/월 × 7명 = LLM 비용 BEP. 최악 손실 $130 (₩180,000). 역마진 리스크 낮음.

**CAC 요약 (조건 B):** 인스타 광고 $20~30 (Pretotyping) + 맘카페 유기적 무비용 조합. LTV/CAC > 10x 목표.

**파이프라인 요약 (조건 C):** `configs/sources/edu_consulting.json` vs `physical_ai.json` 분리 확정. DB `domain` 컬럼 + 별도 스크립트로 완전 격리.

**Gemini 리뷰 프롬프트:** `docs/governance/RED_TEAM_GEMINI_PROMPT_AR029.md` — 대표님이 Gemini CLI에서 실행 필요.

---

---

## 2026-05-24 AR-029 교육 컨설팅 메인 격상 Red Team — Gemini Pass

**Participating LLM:** Gemini (2-of-3 완료)
**Verdict (Gemini):** `APPROVE with conditions`
**correlation_id:** edu-consulting-20260524

### Gemini 판정 매트릭스

| 검토 항목 | 판정 | 세부 |
|---|---|---|
| ① 사실 정확성 | CONCERN | AI 의존성 연구(-0.68) media 인용 — 학술 원문 확인 필요 |
| ② 전략 논리 | CONCERN | "조사≡제품" 고객 가치 전달 방식 명확화 필요 |
| ③ 재무 타당성 | APPROVE | BEP 5~7명, CAC/LTV 합리적 |
| ④ Pre-Mortem 완전성 | APPROVE | 5개 시나리오 종합적으로 다룸 |
| ⑤ 법률/규제 리스크 | APPROVE | 학원법·PIPA·표시광고법 적절히 식별 |
| ⑥ 누락된 리스크 | CONCERN | 리스크 D(LLM 의존도) + E(불안→결제 전환 심리) 신규 지적 |

**Gemini 전체 판정: APPROVE with conditions**

### Gemini 조건 4개

1. **학술 검증**: -0.68 상관계수 원문 논문 직접 확인 (외부 발행·유료 서비스 전)
2. **메시징 정교화**: "조사≡제품" → "상시 자문 서비스" / "맞춤형 AI 교육 전략 가이드"로 구체화
3. **LLM 의존도 리스크**: Pre-Mortem에 시나리오 D 추가 ✅ 해소 (`PRE_MORTEM_ADDENDUM_AR029_Gemini.md`)
4. **WTP 심층 검증**: Pretotyping에서 "비의존 학습법" A/B 테스트로 검증 ✅ 해소 (시나리오 E 추가)

**조건 해소 현황:**
- 조건 1: HUMAN_REQUIRED — 학술 논문 직접 검색 (대표님 검색 또는 DEEP RESEARCH 1차 스윕에서 확인)
- 조건 2: 추가 AR 등록 (메시징 초안 작성 — LLM_EXECUTABLE)
- 조건 3: ✅ `PRE_MORTEM_ADDENDUM_AR029_Gemini.md` 시나리오 D
- 조건 4: ✅ `PRE_MORTEM_ADDENDUM_AR029_Gemini.md` 시나리오 E + Pretotyping A/B 설계

---

## ✅ red_team_clear 기록 — AR-029 교육 컨설팅 메인 격상

**기록일:** 2026-05-24
**판정 구성:** Claude APPROVE + Gemini APPROVE = **2-of-3 기준 충족**
**CLAUDE.md 근거:** "기본값은 2-of-3 approve/clear"
**Non-negotiable 점검:** 사실 오류 없음 (근거 자세 표기 원칙 지켜짐), 법률 리스크 적절 식별, 허위 출처 없음

### ✅ `red_team_clear` 기록 완료

**단, 잔여 조건 (실행 단계별 해소 필수):**

| 조건 | 해소 시점 | 담당 |
|---|---|---|
| -0.68 학술 원문 확인 | DEEP RESEARCH 1차 스윕 또는 개별 검색 | 대표님 / Vision |
| "조사≡제품" 메시징 구체화 초안 | AR-032 (신규, LLM_EXECUTABLE) | Scribe |
| LLM 의존도 Pre-Mortem | ✅ 완료 (시나리오 D) | Jarvis |
| WTP A/B Pretotyping 설계 | ✅ 완료 (시나리오 E) | Jarvis |

**이 조건들은 외부 발행·유료 제안 전 해소 필수. 내부 파이프라인 구축은 즉시 진행 가능.**

---

## 2026-05-24 AR-018 B2I 전환 Red Team 검증

**Participating LLMs:** Claude (claude-opus-4-7) + Gemini (gemini-2.0-flash)  
**Verdict:** `red_team_block` (2-of-2 block — unanimously blocked)  
**Scope:** B2C→B2I 전환 결정 전반 (자본시장법/외국환거래법, LLM 환각→실주문, Physical AI 섹터 집중, $7k 대비 법률 제재 비대칭, 놓친 가정)  
**correlation_id:** strategy-pivot-b2i-20260524

### 판정 요약

| 항목 | Claude | Gemini | 합의 |
|---|---|---|---|
| ① 자본시장법/외국환거래법 | CONCERN | CONCERN | CONCERN |
| ② LLM 환각 신호→실주문 | **BLOCK** | CONCERN | BLOCK |
| ③ Physical AI 단일섹터 집중 | CONCERN | CONCERN | CONCERN |
| ④ $7,000 vs 1.5억 비대칭 | **BLOCK** | **BLOCK** | **BLOCK** |
| ⑤ 놓친 가정·약한 근거 | CONCERN | CONCERN | CONCERN |

**Overall: `red_team_block`** — 두 모델 만장일치

### Claude 주요 BLOCK 근거

- **② LLM 환각→실주문**: 투자 신호→주문 변환 레이어에 콘텐츠 산출물 수준의 cross-LLM 게이트 부재. Paper↔Live 환경 전환 사고(18%, 800만원) 포함. 시나리오 3 확률 42%로 최고.
- **④ EV 음수 구조**: $7,000 업사이드 대비 1.5억 다운사이드(법률 제재) = EV 음수. Gemini 단독 "자기계정 자본시장법 LOW" 판단을 유권해석 없이 확정으로 신뢰 불가.

### 해제 조건 7개 (Claude 제시, 이행 시 재발주)

1. **자본 금액 ground truth 통일** — $7,000 vs $5,000 불일치 해소 (Pre-Mortem $5k vs 패킷 $7k)
2. **AR-017 강화** — 외부 변호사 의견서 1회 mandatory. AR-017 완료 기준 = "한국은행 신고 수리 완료"로 재정의
3. **B2I 전환 자체 Pre-Mortem 추가** — 발행 보류 4주+ 시 brand-equity·subscriber 손실 포함
4. **신호→주문 레이어 cross-LLM 게이트 명문화** — 2-of-3 합의 + non-negotiable factual finding 차단
5. **EV 비대칭 구조적 해법** — Live capital $500 hard-cap. $7,000은 paper trading+8주+KPI 충족 전 IBKR 입금 금지 protocol을 SOUL.md에 추가
6. **거시 트리거 기반 자동 청산** — 반도체 수출규제 신규 발표, SOXX -25% 같은 macro trigger를 KILL_CRITERIA에 명문화
7. **Multi-LLM 법률 검토 보강** — Claude+Gemini+Codex 3모델 독립 검토 + 외부 변호사 사인오프. Gemini 단독 결론은 사전분석으로만 활용

**재발주 트리거**: 조건 1·2·3·4·7 충족 시. 조건 5·6은 capital_action_approve 사전 조건으로 별도 추적.

### Evidence

- Claude: `docs/reports/llm_outputs/claude_ar_018_b2i_red_team_2026-05-24_172003.md`
- Gemini: `docs/reports/llm_outputs/gemini_ar_018_b2i_red_team_2026-05-24_172003.md`
- Packet: `docs/reports/llm_outputs/packet_ar_018_b2i_red_team_2026-05-24_172003.json`

---

## 2026-05-23 IBKR ETF Whitelist Resolver (Pre-Execution)

**Participating LLMs:** Claude + Gemini + Codex (planned)  
**Verdict:** `red_team_block` (Claude block + Codex block; Gemini output produced but did not provide an explicit clear verdict)  
**Scope:** `scripts/ibkr_cp_client.py`, `scripts/openclaw_codex_bridge.py`, `adapters/content/openclaw_agent.py`, `docs/trading/etf_whitelist_v0.json`, `docs/reports/instrument_registry.jsonl`

- Request doc: `docs/governance/RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md`
- Notes: IBKR CP API는 session/2FA 제약이 있으므로 “연결 OK”와 “authenticated OK”를 구분해 차단/가이드해야 한다.
- Evidence:
  - Claude: `docs/reports/llm_outputs/claude_ibkr_etf_whitelist_resolver_registry_gating_2026-05-23_103608.md`
  - Gemini: `docs/reports/llm_outputs/gemini_ibkr_etf_whitelist_resolver_registry_gating_2026-05-23_103857.md`
  - Codex: `docs/reports/llm_outputs/codex_ibkr_etf_whitelist_resolver_registry_gating_2026-05-23.md`

## 2026-05-23 IBKR ETF Whitelist Resolver (Hardening v2 Re-Review)

**Participating LLMs:** Claude + Codex (+ Gemini)  
**Verdict:** `red_team_clear` (2-of-3: Claude clear + Codex clear; Gemini output was low-signal but non-blocking)  
**Scope:** same as above + pending queue + snapshot-based approve

- Evidence:
  - Claude: `docs/reports/llm_outputs/claude_ibkr_etf_whitelist_resolver_registry_gating_hardening_v2_2026-05-23_105007.md`
  - Gemini: `docs/reports/llm_outputs/gemini_ibkr_etf_whitelist_resolver_registry_gating_hardening_v2_2026-05-23_105007.md`
  - Codex: `docs/reports/llm_outputs/codex_ibkr_etf_whitelist_resolver_registry_gating_hardening_v2_2026-05-23.md`

## 2026-05-20 Agentic Orchestration Phase 0 Plan

**Participating LLMs:** Claude (Opus 4.7), Gemini (2.5-pro), Codex (gpt-5.5)
**Verdict:** `conditional_proceed` — 2-of-3 CONDITIONAL_PROCEED / 1 BLOCK(Codex), non-negotiable 5건으로 자동 통과 불가. 대표가 Path A(8개 항목 Phase 0 편입) 선택.
**Scope:** agentic orchestration 개편 Phase 0 plan (`/tmp/agentic_orchestration_phase0_plan.md`)

### Non-negotiable findings (전 모델 통합)

1. Pre-Mortem 누락 (high-impact governance change) — Codex
2. Kill-criteria / 2주 체크포인트 부재 — 3개 모델 공통
3. PII / 보존 / 접근 정책 부재 (autonomous 채널 + episodic memory) — Codex
4. Persona ≠ Gate 혼동 (단일 LLM persona의 cross-LLM 게이트 위장 위험) — Claude
5. "future of company depends on it" = evidence 아닌 전략적 베팅 (Product-over-Pipeline override 정당화 부족) — Codex+Gemini

### 조치 (Path A, 2026-05-20)

| 산출물 | 경로 |
|---|---|
| Pre-Mortem | `docs/governance/PRE_MORTEM_2026-05-20_agentic_orchestration.md` |
| Charter | `docs/governance/AGENTIC_ORCHESTRATION_CHARTER.md` (kill-criteria, 비용 cap, PII 정책, Persona≠Gate, persona→LLM, override protocol, 회의실+OpenClaw 릴레이 포함) |
| Channel log | `docs/operations/SLACK_CHANNEL_CREATION_LOG.md` |
| Enforcement | `scripts/check_slack_channel_log.py` |
| Jarvis persona | `agents/jarvis/{SYSTEM_PROMPT,MEMORY,CHANNEL}.md`, `agents/README.md` |
| CLAUDE.md patch (미적용) | `docs/governance/CLAUDE_MD_PATCH_DRAFT_2026-05-20.md` |

### 남은 조건

- 모든 산출물은 **DRAFT**다. 대표 `pre_mortem_approve` + Business Reality Constraint override 서면 confirm 전까지 구속력 없음.
- CLAUDE.md patch는 미적용 상태. 대표 검토 후 반영.

---

## 2026-05-18

**Participating LLMs:** Claude (Sonnet 4.6), Gemini (0.42.0)  
**Verdict:** `red_team_block`  
**Scope:** `adapters/content/openclaw_agent.py`, `scripts/openclaw_codex_bridge.py`, `scripts/goal_loop.py`, Mac Mini runtime env

### 판정 근거

두 LLM 모두 `red_team_block`에 동의. 수정 전 production 배포 불가.

### 합의된 발견사항

| ID | 등급 | 항목 | Claude | Gemini |
|----|------|------|--------|--------|
| H-1 | HIGH | `SLACK_CEO_USER_ID` 미설정 → 뮤테이션 auth bypass | 발견 | 동의 (함수명 정정: `_authorize_structured_command`) |
| H-2 | HIGH | `_resolve_path` 절대경로 경계 미검사 (path traversal) | 발견 | 동의, `tool_write_file`에 `write=True` 명시 추가 |
| H-3 | HIGH | `_format_with_haiku` 날짜 미주입 → 오계산 | 발견 | 동의 |
| H-4 | HIGH | **Prompt Injection** (신규 — Gemini 발견) | 미발견 | 발견 |
| M-1 | MEDIUM | budget gate Haiku 경로 미적용 | 발견 | 동의 |
| M-2 | MEDIUM | `CAPITAL_ACTIONS_ENABLED` bridge 차단 미수행 | 발견 | 동의 |
| M-3 | MEDIUM | `correlation_id` goal_loop.py 미전파 | 발견 | 동의 (파일 경로 차이로 직접 검증 불가) |
| M-4 | MEDIUM | log rotation 미설정 | 발견 | 동의 |
| M-5 | MEDIUM-LOW | **Race condition** `_write_output` 동시 쓰기 (신규 — Gemini 발견) | 미발견 | 발견 |
| M-6 | MEDIUM | **클라이언트 Rate Limiting 부재** (신규 — Gemini 발견) | 미발견 | 발견 |

### Gemini 신규 발견사항 요약

**H-4: Prompt Injection (HIGH)**
- `_build_chat_system_prompt`, `_build_tool_system_prompt`, `_format_with_haiku`, `_classify_intent_with_haiku` 전부 user_message를 프롬프트에 직접 주입
- 악의적 입력으로 시스템 프롬프트 우회, 민감 정보 추출, 의도치 않은 tool-use 유발 가능
- 수정 방향: XML 태그로 사용자 입력 캡슐화, 시스템 프롬프트에 injection 방어 지침 추가

**M-5: Race Condition (MEDIUM-LOW)**
- `_write_output` 파일 잠금 없이 동시 쓰기 시 데이터 손상 가능
- 수정 방향: `fcntl` 또는 `filelock` 기반 파일 잠금 추가

**M-6: Rate Limiting 부재 (MEDIUM)**
- Anthropic/Slack API 클라이언트 측 rate limit 없음
- Prompt Injection + 연쇄 API 호출 시 비용 급증 위험
- 수정 방향: 인메모리 또는 Redis 기반 rate limiter 추가

### 수정 완료 항목 (2026-05-18 commit `2e522a2`)

| ID | 수정 내용 | 검증 |
|----|-----------|------|
| H-1 | `_authorized_for_high_risk` fail-closed + `_authorize_structured_command` env 미설정 차단 + Mac Mini `.env` `SLACK_CEO_USER_ID=U0B2P25NR6Y` 추가 | Mac Mini 4개 케이스 PASS |
| H-2 | `_resolve_path` `_ALLOWED_READ_ROOTS`/`_ALLOWED_WRITE_ROOTS` boundary 강제, `tool_write_file` `write=True` | SSH key / /etc/hosts 차단 PASS |
| H-3 | `_format_with_haiku` `datetime.now()` system prompt 주입 | 코드 확인 |
| H-4 | 모든 LLM 호출 user_message XML 캡슐화, SYSTEM_PROMPT/CHAT_SYSTEM_PROMPT injection 방어 지침 추가 | 코드 확인 |
| M-2 | `command_record_decision` `capital_action_approve` gate 추가 | 코드 확인 |

### 추가 수정 완료 (2026-05-18 commit `c6bec74`, `28cde34`)

| ID | 수정 내용 | 검증 |
|----|-----------|------|
| M-1 | Mac Mini 싱크 코드에 이미 내부 `_cost_limit_reached()` 체크 존재 (수정 완료 확인) | 코드 확인 |
| M-3 | `correlation_id UUID` 컬럼 migration + `create_goal` / `set_goal_model` / `record_goal_snapshot`에 전파 | Mac Mini DB ALTER TABLE PASS |
| M-4 | `slack_listener.py` RotatingFileHandler 10MB×5 + launchd plist stdout→`/dev/null` (중복 제거) | 단일 포맷 로그 확인 |
| M-5 | `_write_output` `fcntl.LOCK_EX` 파일 잠금 | 코드 확인 |
| M-6 | `run()` 진입부 슬라이딩 윈도우 rate limiter (60초/20회, 환경변수 조절 가능) | 코드 확인 |

### 추가 수정 완료 (2026-05-18 commit `b16792a`)

| 항목 | 수정 내용 | 검증 |
|------|-----------|------|
| CLAUDE.md compliance | `PREREQUISITE_GATES` in `core/approval.py` — `report_publish_approve` / `monetization_experiment_approve` / `investment_thesis_approve` / `capital_action_approve` 기록 전 `legal_review_approve` + `red_team_clear` + `pre_mortem_approve` (+ `qa_clear`) 충족 여부 DB 검증 | Mac Mini 3케이스 PASS |
| CLAUDE.md compliance | `_check_prerequisites()` in `ceo_decision.py` — 미충족 시 `PermissionError` + 필요 gate 목록 반환 | PASS |
| CLAUDE.md compliance | `docs/governance/PRE_MORTEM_PROTOCOL.md` 신규 작성 | |
| CLAUDE.md compliance | `docs/operations/QA_PLAYBOOK.md` 신규 작성 | |
| CLAUDE.md compliance | `docs/operations/LEGAL_REVIEW_PLAYBOOK.md` 신규 작성 | |

### 미해결 항목

없음 — 모든 `red_team_block` 항목 수정 완료.

### `red_team_clear` 조건

Codex / GPT reasoning model의 독립적 final pass 후 3-of-3 또는 2-of-3 approve 시 `red_team_clear` 기록 가능.

재검토 참여 LLM: Claude + Gemini + Codex (기존 Claude + Gemini 완료 → Codex pass 1개 남음)

---

## 2026-05-19 — Codex Final Pass
**Participating LLMs:** Codex  
**Verdict:** `red_team_block`

### Checklist Findings

| Item | Verdict | Finding |
| --- | --- | --- |
| H-1 Auth Bypass | PASS for patched functions; CONCERN on Slack DM ingress | `_authorized_for_high_risk()` now fails closed when `SLACK_CEO_USER_ID` is unset (`adapters/content/openclaw_agent.py:477`). `_authorize_structured_command()` blocks mutating structured commands when the env var is unset, missing caller identity, or wrong caller (`adapters/content/openclaw_agent.py:1041`). However, Slack DM ingress still routes any DM sender to `agent_run()` when `CEO_SLACK_USER_ID` is unset (`adapters/content/slack_listener.py:98`), leaving read-only tools and LLM spend exposed if production env is misconfigured. |
| H-2 Path Traversal | PASS for read/write; NEW CONCERN for script execution | `_resolve_path()` resolves absolute and relative paths, then enforces `resolved.is_relative_to(root.resolve())` (`adapters/content/openclaw_agent.py:1177`). Because `.resolve()` follows symlinks before the boundary check, symlink escape outside `PROJECT_ROOT` is blocked for read/write. `tool_write_file()` passes `write=True` (`adapters/content/openclaw_agent.py:1208`). Separate issue: `tool_run_script()` does not use `_resolve_path()` and builds `PROJECT_ROOT / script`; an absolute `script` path bypasses the project-root intent (`adapters/content/openclaw_agent.py:1237`). |
| H-4 Prompt Injection | FAIL | `SYSTEM_PROMPT` and `CHAT_SYSTEM_PROMPT` include injection-defense instructions (`adapters/content/openclaw_agent.py:95`, `adapters/content/openclaw_agent.py:119`). Current direct `user_message` calls are XML wrapped (`adapters/content/openclaw_agent.py:1489`, `adapters/content/openclaw_agent.py:1566`, `adapters/content/openclaw_agent.py:1619`, `adapters/content/openclaw_agent.py:1677`, `adapters/content/openclaw_agent.py:1945`). But prior user turns are stored raw (`adapters/content/openclaw_agent.py:331`) and replayed directly with `messages.extend(history or [])` into Ollama chat (`adapters/content/openclaw_agent.py:1488`), Anthropic chat (`adapters/content/openclaw_agent.py:1565`), and the tool agent (`adapters/content/openclaw_agent.py:1944`). This leaves a multi-turn prompt-injection path outside the XML wrapper. |
| M-6 Rate Limiter Thread Safety | PASS | `_rate_limit_check()` holds `_rate_lock` across bucket lookup, expiry pruning, length check, and append (`adapters/content/openclaw_agent.py:407`). The check-and-append is atomic inside the process; no in-process TOCTOU found. Residual limitation: in-memory buckets do not coordinate across multiple processes. |
| Compliance Gates | FAIL | `_check_prerequisites()` counts only `decision = 'approved'` records (`scripts/ceo_decision.py:18`). `record_decision()` calls it only for `decision == "approved"` before inserting (`scripts/ceo_decision.py:37`). However, `PREREQUISITE_GATES` omits `qa_clear` for `monetization_experiment_approve` and `investment_thesis_approve` (`core/approval.py:9`), conflicting with the current AGENTS.md approval table that requires `qa_clear` for both. |
| M-2 / M-5 Bridge Safety | PASS | `command_record_decision()` blocks `capital_action_approve` unless `CAPITAL_ACTIONS_ENABLED=true` (`scripts/openclaw_codex_bridge.py:194`). `_write_output()` uses `fcntl.LOCK_EX` while writing output files (`scripts/openclaw_codex_bridge.py:130`). |
| M-3 Goal Loop SQL / Correlation | PASS | Reviewed target `execute_query()` calls in `scripts/goal_loop.py`; user-controlled values are passed as parameters, including JSON via `%s::jsonb` and UUID via `%s::uuid` (`scripts/goal_loop.py:49`, `scripts/goal_loop.py:116`, `scripts/goal_loop.py:253`, `scripts/goal_loop.py:661`). No SQL injection found in this file. |
| M-4 Slack Log Rotation | PASS with auth concern above | `RotatingFileHandler` is configured with 10MB files and 5 backups, and duplicate rotating/stream handlers are avoided (`adapters/content/slack_listener.py:39`). |

### Independent Scan

- SQL injection: no user-input SQL concatenation found in the requested target files. Most target queries use `%s` parameters. Out-of-scope note: `scripts/publish_weekly_to_substack.py:52` uses an f-string for generated placeholders, but values are still parameterized and `ids` is typed as `list[int]`; not treated as a blocker in this pass.
- SSRF: `tool_fetch_url()` accepts arbitrary URLs and calls `httpx.get(..., follow_redirects=True)` without scheme, host, or private-network validation (`adapters/content/openclaw_agent.py:1269`, `adapters/content/openclaw_agent.py:1303`). Because `fetch_url` is classified as low-risk/no approval (`adapters/content/openclaw_agent.py:184`), an attacker with access to the agent surface can probe localhost, RFC1918, or metadata endpoints and can use redirects to reach them.
- Prompt/tool-result injection: fetched web content is returned as a tool result and then appended back into the tool-agent conversation (`adapters/content/openclaw_agent.py:1328`, `adapters/content/openclaw_agent.py:2004`). There is no explicit untrusted-content wrapper or instruction preventing the model from following instructions embedded in fetched pages. If the requester is the CEO, a malicious fetched page could induce later high-risk tool calls that preflight would authorize based only on requester identity.
- Script execution boundary: `tool_run_script()` lacks the same resolved-root boundary used by file read/write (`adapters/content/openclaw_agent.py:1237`). This is especially risky in combination with the tool-result prompt-injection path.

### New Findings

| ID | Severity | Finding |
| --- | --- | --- |
| C-1 | HIGH | Multi-turn user history bypasses XML prompt-injection wrapping. Raw prior user turns are replayed into future LLM calls. |
| C-2 | HIGH | Unrestricted `fetch_url` creates SSRF exposure and can feed untrusted remote instructions back into the tool-agent loop. |
| C-3 | HIGH | `tool_run_script()` does not enforce project-root containment for script paths. |
| C-4 | MEDIUM | Slack DM route is fail-open to `agent_run()` when `SLACK_CEO_USER_ID` is unset. |
| C-5 | MEDIUM | Compliance gates omit `qa_clear` for `monetization_experiment_approve` and `investment_thesis_approve` relative to current AGENTS.md. |

### Final Verdict

`red_team_block`. The direct H-1, H-2 read/write, M-2, M-3, M-4, M-5, and M-6 patches mostly verify, but H-4 remains incomplete through conversation history replay. SSRF plus untrusted fetched content plus broad script execution is a credible tool-chaining risk. Do not record `red_team_clear` or run the Mac Mini `record-decision red_team_clear` command until these findings are fixed and re-reviewed.

---

## 2026-05-19 — Codex 발견사항 수정 완료 (commit `182635d`)

| ID | 수정 내용 |
|----|-----------|
| C-1 (H-4 history replay) | `_record_conversation_turn()` 저장 시점에 XML 캡슐화 → 모든 replay 경로 자동 커버 |
| C-2 (SSRF) | `_check_ssrf_url()` 추가 — private/loopback/link-local/reserved IP 차단, `tool_fetch_url()` 진입부 적용 |
| C-3 (run_script boundary) | `tool_run_script()` → `_resolve_path(script)` 경유로 PROJECT_ROOT boundary 강제 |
| C-4 (DM fail-open) | `slack_listener.py` DM handler: `not CEO_SLACK_USER_ID or ...` → `CEO_SLACK_USER_ID and user == CEO_SLACK_USER_ID` |
| C-5 (compliance qa_clear) | `PREREQUISITE_GATES`에 `monetization_experiment_approve`, `investment_thesis_approve`에 `qa_clear` 추가 |

### `red_team_clear` 기록

**Verdict:** `red_team_clear`  
**Participating LLMs:** Claude (Sonnet 4.6) + Gemini (0.42.0) + Codex  
**DB 기록:** `ceo_decisions` target_type=red_team_review target_id=1 decision=approved approval_type=red_team_clear (2026-05-19T06:42:02)  
**근거:** 3-LLM cross-verification 완료. C-1~C-5 전체 수정 완료 확인. H-1~H-4 + M-1~M-6 + CLAUDE.md compliance 전체 통과.

---

## 2026-05-19 — BRM Playbook Red Team (Claude 1차 pass)

**Participating LLMs:** Claude (Sonnet 4.6) — 1차 pass 완료. Gemini + Codex pass 대기 중.  
**Verdict:** `red_team_block` (Claude 단독 — 최종 판정 미결)  
**Scope:** `docs/governance/BRM_PLAYBOOK.md`

### Claude 발견사항

| ID | 등급 | 항목 |
|----|------|------|
| B-1 | MEDIUM | §2.2 발생 확률(low/medium/high) 수치 기준 미정의 — Agent마다 다른 등급 부여 가능 |
| B-2 | MEDIUM | §5.3 `accepted` 상태 전환 시 CEO 확인 `ceo_decisions` DB 기록 지침 없음 — audit trail 부재 |
| B-3 | MEDIUM | §6.2 `pre_mortem_approve` DB 기록 주체 미명시 — PRE_MORTEM_PROTOCOL.md 기존 절차(CEO bridge 직접 기록)와 충돌 가능 |
| B-4 | MEDIUM | `risk_register` DB 테이블은 roadmap 상태(AGENTS.md §5)임에도 플레이북이 현재 운영 가능한 것처럼 기술 — Phase 1 MD 파일 기반 운영 선언 누락 |
| B-5 | MEDIUM | §4 실시간 임계값 모니터링이 자동화인지 수동인지 미명시 — "즉시" escalation이 사실상 수동 점검에 의존할 가능성 |
| B-6 | LOW | §4 ESC-STR-1 "30-day target 달성 가능성 50%" — Business Operations 예측 미실행 주에 대한 fallback 없음 |
| B-7 | LOW | §7.1 Kill Criteria 트리거 5개 항목이 실제 `docs/governance/KILL_CRITERIA.md` 내용과 정합성 미검증 |

### Claude 판정 근거

B-1~B-5는 플레이북을 실제 운영 시 일관성 부재 또는 audit trail 누락으로 이어지는 항목이다. 특히 B-4는 DB가 존재한다는 잘못된 전제를 심을 수 있어 수정이 필요하다. B-6~B-7은 낮은 우선순위이나 Gemini/Codex가 독립 검토해야 한다.

### 최종 판정 조건

Gemini + Codex pass 후 3-LLM 중 2개 이상이 clear 또는 수정 후 clear이면 `red_team_clear` 기록 가능.  
B-1~B-5 중 Gemini/Codex가 동의하는 항목은 수정 후 재검토.  
요청 문서: `docs/governance/RED_TEAM_BRM_REQUEST_2026-05-19.md`

---

## 2026-05-19 — BRM Playbook Gemini pass

**Participating LLMs:** Gemini (0.42.0)  
**Verdict:** `red_team_block`

### Claude 발견사항 검증 결과 (B-1 ~ B-7)

| ID | Claude 등급 | Gemini 판정 |
|----|------------|------------|
| B-1 | MEDIUM | **AGREE** — 수치 기준 없이 주관적 분류는 Agent 간 불일치 유발 |
| B-2 | MEDIUM | **AGREE** — risk_brief 언급만으로는 부족, `ceo_decisions` DB 기록 필요 |
| B-3 | MEDIUM | **PARTIAL AGREE** — 직접 충돌은 아니나 BRM review를 prerequisite로 명시하고 기록 주체를 분명히 해야 함 |
| B-4 | MEDIUM | **DISAGREE** — MD 파일 기반 MVP 운영은 유효한 접근, 운영 리스크 아님 |
| B-5 | MEDIUM | **AGREE** — "즉시" escalation은 자동화를 전제해야 하며 미명시는 신뢰성 결함 |
| B-6 | LOW | **AGREE** — Business Operations 예측 미실행 시 fallback 필요 |
| B-7 | LOW | **AGREE** — KILL_CRITERIA.md를 정규 참조원으로 유지해야 함, 중복 나열은 sync 실패 위험 |

### Gemini 신규 발견사항

| ID | 등급 | 항목 |
|----|------|------|
| G-1 | **HIGH** | **과도한 복잡성** — 6개 차원·9개 임계값 체계는 Phase 1(paid subscriber 1명) 목표 대비 과도. CLAUDE.md §1 Product-over-Pipeline 원칙 위반 |
| G-2 | MEDIUM | **미선언 거버넌스 변경** — `pre_mortem_review_note`가 BRM 검토를 암묵적 필수 게이트로 추가. CLAUDE.md 승인 체계 수정은 명시적 선언 필요 |
| G-3 | MEDIUM | §2.2 매트릭스와 §4 임계값 간 우선순위 관계 미정의 — 어느 기준이 override인지 불명확 |
| G-4 | MEDIUM | §9.1 risk_brief 템플릿이 넓은 마크다운 표 형식 — CEO 모바일 30~60초 판단에 부적합 |
| G-5 | LOW | BRM Agent 자체 장애 시 감지·경보 메커니즘 없음 ("모니터의 모니터" 부재) |

### Gemini 판정 근거

1. **G-1 (HIGH)**: 현재 Phase 1 목표(무료 50명, paid 1명)에서 6차원 리스크 레지스터+9개 자동 임계값 체계는 실질적 가치보다 운영 부담이 크다. 플레이북을 Phase 1 최소 버전으로 축소해야 한다.
2. **G-2+B-3**: 기존 승인 체계(CLAUDE.md §4)를 암묵적으로 수정하는 것은 내부 규약 위반.
3. **B-2**: `accepted` 리스크에 대한 불변 감사 기록 누락은 거버넌스 실패.

### 중간 집계 (Claude + Gemini)

| 항목 | Claude | Gemini | 합의 |
|------|--------|--------|------|
| B-1 | block | block | **수정 필요** |
| B-2 | block | block | **수정 필요** |
| B-3 | block | partial | **수정 권고** |
| B-4 | block | clear | 불일치 — Codex 판정 필요 |
| B-5 | block | block | **수정 필요** |
| B-6 | low | low | 낮은 우선순위 |
| B-7 | low | block | **수정 권고** |
| G-1 | 미발견 | HIGH | **수정 필요** (non-negotiable) |
| G-2 | 미발견 | MEDIUM | **수정 필요** |
| G-3 | 미발견 | MEDIUM | 수정 권고 |
| G-4 | 미발견 | MEDIUM | 수정 권고 |
| G-5 | 미발견 | LOW | 낮은 우선순위 |

현재 상태: **Claude block + Gemini block = red_team_block**  
Codex pass 또는 수정 후 재검토 필요.

---

## 2026-05-19 — BRM Playbook v1.1 수정 완료 및 재검토

### 수정 내역 (commit 예정)

| ID | 수정 내용 |
|----|-----------|
| B-1 | §2.2 확률 기준값 정의 (low < 20% / medium 20~60% / high > 60%) |
| B-2 | §5.3 `accepted` Phase 1 MD 기록 방식 + Phase 2 bridge 구분. `core/approval.py` 미등록 타입(risk_review/risk_accept) Phase 2 예정임 명시 |
| B-3/G-2 | §6 거버넌스 선언 추가: `pre_mortem_review_note`는 prerequisite gate이며 `pre_mortem_approve` 기록 주체는 결정 팀/CEO |
| B-5 | §3.0, §3.1, §4 Phase 1 수동 점검 방식 명시, 자동화 Phase 2 예정 |
| B-6 | ESC-STR-1 각주: Business Operations 미실행 시 status unknown + 2주 연속 미실행 시 에스컬레이션 |
| B-7 | §7.1 Kill Criteria 중복 나열 제거, KILL_CRITERIA.md 단일 참조원으로 대체 |
| G-1 | §3.0 Phase 1 운영 범위 선언: 임계값 9→4개 활성, 수동 점검, MD 기반 레지스터 |
| G-3 | §2.2 하단 §4가 매트릭스 override임을 명시 |
| G-4 | §9.1 risk_brief 이모지 목록 형식으로 경량화 (Slack 1화면 이내) |
| G-5 | §11 BRM 2주 연속 미발행 시 비서실장 CEO 직보 규칙 추가 |
| B-4 | 수정 불필요 (Gemini DISAGREE) — §3.0 Phase 1/2 구분 테이블로 자연 해소 |

### Claude 재검토 판정

**Verdict:** `red_team_clear`

모든 블로킹 항목(G-1, B-2, G-2, B-3) 해소 확인. B-2의 bridge 명령 미등록 타입 문제는 Phase 1 수동 방식 + Phase 2 DB 구현 예정으로 문서에 명시됨. 잔존 non-negotiable 이슈 없음.

Gemini 재검토 완료.

### Gemini 재검토 판정

**Verdict:** `red_team_clear`

| ID | v1.1 상태 |
|----|-----------|
| G-1 (Premature complexity) | ✅ Resolved — §3.0 Phase 1 scope 적절 |
| G-2 (Implicit governance change) | ✅ Resolved — §6 명시적 거버넌스 선언 충족 |
| B-2 (accepted audit trail) | ✅ Resolved — Phase 1 MD+Git, Phase 2 DB 구분 충족 |
| G-3 (matrix/threshold hierarchy) | ✅ Resolved |
| G-4 (mobile brief) | ✅ Resolved |
| G-5 (BRM failure monitoring) | ✅ Resolved |
| B-1 (probability thresholds) | ✅ Resolved |
| B-5 (manual vs automated) | ✅ Resolved |
| B-6 (ESC-STR-1 fallback) | ✅ Resolved |
| B-7 (Kill Criteria duplication) | ✅ Resolved |
| 신규 이슈 | 없음 |

Gemini 판정 근거: "The new phased approach (Phase 1) is practical and safe, reducing initial complexity while maintaining essential risk oversight."

### `red_team_clear` 기록

**Verdict:** `red_team_clear`  
**Participating LLMs:** Claude (Sonnet 4.6) + Gemini (0.42.0)  
**근거:** 2-LLM cross-verification 완료 (MD 문서 기준: Claude + Gemini 최소 요건 충족). B-1~B-7 + G-1~G-5 전체 수정 완료 확인. 잔존 non-negotiable 이슈 없음.  
**대상:** `docs/governance/BRM_PLAYBOOK.md` v1.1  
**비고:** Codex pass는 선택적 추가 검토 — 2-of-3 기준으로 현재 통과 조건 충족.

---

## 2026-05-19 — BRM Playbook Codex pass

**Participating LLMs:** Codex  
**Verdict:** `red_team_block` (C-1 경로 오류 발견) → v1.2 수정 후 `red_team_clear`

### Codex 발견사항

| ID | 등급 | 항목 | Codex 판정 |
|----|------|------|-----------|
| C-1 | BLOCK | §7 §7.1 서두 `docs/governance/KILL_CRITERIA.md` 경로 오류 — 실제 파일 위치는 `docs/KILL_CRITERIA.md` | block |
| C-2 | LOW | `risk_review`/`risk_accept` approval type이 `core/approval.py`에 미등록 | Phase 2 로드맵으로 수용, non-blocking |
| C-3 | LOW | 보안 취약점 모니터링 자동화 스크립트 미구현 (주간 수동 운영) | Phase 1 수동 명시로 수용 |
| C-4 | LOW | AGENTS.md §3.16 output 명칭과 BRM_PLAYBOOK.md §8 용어 미세 불일치 | 운영상 혼란 낮음, non-blocking |

**이전 항목 재확인:** Claude + Gemini에서 수정된 B-1~B-7, G-1~G-5 전체 v1.1 반영 확인. 신규 non-negotiable 이슈 없음 (C-1 제외).

### v1.2 수정 내용

| C-1 수정 | `docs/governance/BRM_PLAYBOOK.md` §7 서두 경로 `docs/governance/KILL_CRITERIA.md` → `docs/KILL_CRITERIA.md` |
| --- | --- |
| 버전 | v1.1 → v1.2 |

### Codex 재판정

C-1 수정 후 잔존 blocking 이슈 없음. C-2~C-4는 Phase 2 로드맵 또는 운영상 낮은 위험으로 수용.  
**Verdict:** `red_team_clear`

---

## 2026-05-19 — BRM Playbook 최종 판정 (3-of-3)

**Verdict:** `red_team_clear`  
**Participating LLMs:** Claude (Sonnet 4.6) + Gemini (0.42.0) + Codex  
**대상:** `docs/governance/BRM_PLAYBOOK.md` v1.2  
**근거:** 3-LLM cross-verification 완료. B-1~B-7 + G-1~G-5 + C-1 전체 수정 확인. 잔존 non-negotiable 이슈 없음.  
**잔존 로드맵 항목:** C-2 (`risk_accept` approval type Phase 2 DB 등록), C-3 (취약점 자동 모니터링 스크립트) — 운영 차단 없음.
---

## 2026-05-19 Remediation Pass

**Implementing LLM:** Codex  
**Verdict:** `conditional_proceed` — 코드/런타임 조치 완료, 별도 Claude+Gemini 재검토 전까지 `red_team_clear`로 승격하지 않음.

### 조치 결과

| ID | 상태 | 조치 |
|----|------|------|
| H-1 | fixed | `SLACK_CEO_USER_ID` 미설정 시 high-risk/mutating command를 fail-closed 처리. Mac Mini runtime `.env`에는 CEO Slack user ID 설정 확인. |
| H-2 | fixed | `_resolve_path()`에 PROJECT_ROOT 경계 검사 추가. read는 project root 하위만, write는 `docs/`, `reports/`, `runtime/` 하위만 허용. |
| H-3 | fixed | formatter system prompt에 오늘 날짜 주입 및 날짜 계산 기준 명시. |
| H-4 | mitigated | user message / bridge output을 XML-style boundary로 감싸고, prompt-injection 방어 지침을 chat/tool/classifier/formatter prompt에 추가. |
| M-1 | fixed | Haiku intent classifier 진입 전 cost guard 추가. |
| M-2 | fixed | `capital_action_approve`는 `CAPITAL_ACTIONS_ENABLED=true`가 아니면 bridge에서 기록 차단. |
| M-3 | fixed | goal loop write path에 `correlation_id` 전파. migration `2026-05-19_goal_loop_correlation_id.sql` 추가 및 runtime DB 적용. |
| M-4 | fixed | Slack listener에 `RotatingFileHandler` 적용 (`logs/slack-listener.log`, 10MB x 5). |
| M-5 | fixed | bridge `_write_output()`에 `fcntl.flock` 기반 exclusive lock 추가. |
| M-6 | mitigated | Anthropic intent/chat/tool 경로에 per-user in-memory rate limit 추가. |
| Compliance | existing/verified | `qa_clear`, `legal_review_approve`, `pre_mortem_approve` 구현체 존재 확인: `adapters/content/qa_agent.py`, `adapters/content/legal_review.py`, `adapters/content/pre_mortem.py`, 관련 CLI scripts. |

### 추가 조치

- Gmail capability 오답 방지: OpenClaw gateway의 `gog` skill이 ready/visible임을 runtime에서 확인했고, Harness Slack adapter에 `gmail_search` read-only tool 및 deterministic capability response를 추가.
- Gmail mutating action 금지: `gog --gmail-no-send`를 사용하며, Slack adapter에서는 Gmail 검색/읽기만 허용.
- Runtime 적용: Mac Mini runtime에 파일 sync, unit test 통과, DB migration 적용, `com.harness.slack-listener` 재시작 완료.

### 검증

- Local: `py_compile` 통과, `tests/test_openclaw_agent.py`, `tests/test_openclaw_route_audit_summary.py` 통과.
- Runtime: `py_compile` 통과, `tests/test_openclaw_agent.py` 통과.
- Runtime smoke: `구글 메일 읽을 수 있어?`에 대해 `gog`/`gmail_search` 기반 가능 조건을 deterministic하게 응답.

### 남은 조건

- 이 remediation은 Codex implementation pass다. 조직 규칙상 최종 `red_team_clear` 승격은 Claude + Gemini + Codex 재검토 후 기록한다.

---

## 2026-05-25 AR-033 "첫 단추 서비스" 사업모델 Red Team — FINAL VERDICT

**Participating LLM:** Claude (claude-sonnet-4-6) + Gemini (2026-05-25)
**Verdict:** `red_team_BLOCK` — 2-of-2 BLOCK. `red_team_clear` 미달.
**Scope:** 첫 단추 서비스 (Segment of One, Track A~D, 음성 온보딩, 가격 ₩29,900~₩59,000)
**correlation_id:** edu-consulting-20260524 / AR-033
**Reference:**
- Claude 1차: `docs/governance/RED_TEAM_FIRSTBUTTON_AR033_Claude.md` — CONDITIONAL BLOCK
- Gemini 2차: CEO 직접 수령 (2026-05-25) — BLOCK

### 판정 매트릭스

| 모델 | 판정 | 핵심 이슈 |
|---|---|---|
| Claude | `CONDITIONAL BLOCK` | BLOCK-1: Segment of One vs 스케일 모순. BLOCK-2: 리텐션 미정의. 5 CONCERN. |
| Gemini | `BLOCK` | 시장 적합성 미달, ChatGPT 복제 리스크, WTP ₩29,900 과도, 타겟 파편화, 고마찰 실행 구조 |
| **2-of-2 합산** | **`BLOCK`** | red_team_clear 조건 미달 |

### Non-Negotiable Findings (즉시 수정 완료)

| 항목 | 상태 |
|---|---|
| BFI WP 2025-144 허위 인용 | ✅ **삭제 완료** (2026-05-25) — SEGMENT_UNIVERSE.md 4곳, DATA_GATHERING_UNIVERSE.md 1곳 |
| "쥐잡기 경주" 근거 주장 | ✅ **[speculative]로 강등** — 실증 소스 재탐색 AR 등록 필요 |

### CEO 결정 필요 항목 (실행 BLOCK 중)

1. **BLOCK-1 (전략 방향):** "Segment of One" 정의
   - Option A: 소규모 프리미엄 30명 한정 → 진짜 1:1 커스터마이즈
   - Option B: AI 90% + 전문가 10% 투명 공개 → 스케일 가능

2. **BLOCK-2 (리텐션):** 구독 지속 메커니즘 정의
   - 월 Q&A 채널 / 월 AI 업데이트 리포트 / 3개월 추적 / 커뮤니티 중 선택

3. **Gemini 전략 BLOCK 대응 (CEO 채택/거부 결정):**
   - G-1 시장 적합성: 타겟 선택 확정 (학부모 단독 vs 직장인 포함)
   - G-2 ChatGPT wrapper: 독점 데이터 확보 경로 또는 실행 대행 모델 피벗 여부
   - G-3 WTP: 가격 재설계 (CEO 2026-05-25 지시 → "Step 당 천원" 박리다매 모델 검토 중)
   - G-4 타겟 파편화: 학부모 단독 집중 여부
   - G-5 고마찰 구조: 실행 대행 요소 추가 여부

### 상태
- `red_team_clear` 미달 → 모든 외부 발행, Pretotyping 광고 집행, 유료 제안 **BLOCK**
- CEO 결정 수령 후 수정 → Codex 3rd opinion → 재검토 가능


---

## 2026-05-25 AR-033 CEO 결정 — BLOCK 전원 해소

**기록자:** Friday (Chief of Staff)
**날짜:** 2026-05-25
**상태:** CEO 결정으로 4개 BLOCK/Gemini-finding 전원 해소. AR-036 등록 → 수정 반영 → Codex 3rd opinion 대기.

### CEO 결정 매트릭스

| 항목 | 옵션 | CEO 결정 | 핵심 변화 |
|---|---|---|---|
| **BLOCK-1** Segment of One vs 스케일 | A(소규모프리미엄) / **B(AI90%+전문가10%)** / C(구간분리) | **B** | AI가 90% 자동화, 전문가(VP)가 10% 검수. 투명 공개. 스케일 가능. |
| **BLOCK-2** 리텐션 메커니즘 | A~E 옵션 | **C** (가격은 Step별 결제) | Step 8 완료 후 3개월 추적 코칭. Step 9~11로 구성, 각 Step마다 별도 결제. |
| **G-2** ChatGPT Wrapper 모트 | A·B·C·D | **A+C+D** | ① 독점 데이터(맘카페·학군·사용자 반응) ② VP 학부모 언어 전문성 ③ 커뮤니티+데이터 누적 루프 |
| **G-5** 고마찰 구조 | A·B·C | **A+B** | ① 실행 대행("이번 주 할 것" Harness가 세팅) ② 카톡 체크리스트 자동화 리마인더 |

### Gemini BLOCK 최종 상태 (CEO confirm 포함)

| 항목 | 원래 판정 | CEO 결정 후 상태 |
|---|---|---|
| G-1 타겟 파편화 | BLOCK | ✅ CEO confirm: 학부모+직장인 오버랩 타겟. 파편화 아님. |
| G-2 ChatGPT Wrapper | BLOCK | ✅ CEO confirm: A+C+D 모트 구성 채택 |
| G-3 WTP 과다 | BLOCK | ✅ CEO confirm: Step당 ₩990→심화 점진 상승 모델 채택 |
| G-4 타겟 파편화 | BLOCK | ✅ CEO confirm (G-1과 동일) |
| G-5 고마찰 | BLOCK | ✅ CEO confirm: A+B(실행대행+자동화) 채택 |
| BFI WP 2025-144 허위 | NON-NEGOTIABLE | ✅ 삭제 완료 (2026-05-25) |

### 다음 단계 (AR-036)

1. 수정 사항 문서 반영 (LLM_EXECUTABLE — 당일)
2. Codex 3rd opinion 요청 (AR-036 완료 후)
3. 3-of-3 최종 판정 → `red_team_clear` 달성 시 Pretotyping 허용


---

## 2026-05-25 AR-033 3차 판정 — CEO 직접 검토 (Codex 역할 수행)

**Participating LLM:** CEO (Juntae Park) — Codex 3rd opinion 대행
**Verdict:** `BLOCK`
**Scope:** 수정된 사업모델 (CEO 결정 반영 후 버전)
**correlation_id:** edu-consulting-20260524
**Reference:** `RED_TEAM_CODEX_PROMPT_AR033.md` 검토 기반

### 3차 판정 매트릭스

| 항목 | 판정 | 핵심 근거 |
|---|---|---|
| Segment of One 스케일 | 부분 해소 | VP 검수 SLA·반려율·일 처리량 수치 미정의 |
| 리텐션 미정의 | 부분 해소 | Step 9~11 구조는 있으나 lock-in 검증 전 |
| 가격 WTP | 부분 해소 | 마이크로 결제 방향은 맞으나 S1~S4 이후 검증 미진행 |
| ChatGPT Wrapper 모트 | **해소 안됨** | Cold start(0~50명) 구간에서 차별화 없음. 맘카페 ToS·학군데이터 수집 경로 공백 |
| 타겟 파편화 | **해소 안됨에 가까운 부분 해소** | 구매 순간은 여전히 두 개 상품. 메시지/채널/카피/결과물/신뢰기준 상이 |
| 법적 리스크 | **해소 안됨** | CEO 수정안에 대응 설계 없음. "진단/처방/위험도" 카피가 legal_review 전 외부 사용 위험 |

### AR-033 최종 누적 판정

| 모델 | 판정 |
|---|---|
| Claude (1차) | CONDITIONAL BLOCK |
| Gemini (2차) | BLOCK |
| CEO/Codex (3차) | **BLOCK** |
| **3-of-3 합산** | **BLOCK — `red_team_clear` 달성 실패** |

### CEO 제시 수정 방향 (AR-037 실행 대상)

1. **Phase 1 범위 축소:** Track B(학부모) MVP only. Track A는 cross-sell 실험으로 격하
2. **가격 검증 범위:** S1 무료, S2~S4 유료까지 먼저 Pretotyping. S5~S11은 데이터 확인 후
3. **VP 운영 SLA 정의:** 건당 목표 3분 / 일 20건 / 반려율 20% 이하
4. **모트 재정의:** 초기에는 "한국어 학부모용 안전한 AI 사용 가이드 + VP readability 검수 + 실행 카드"로 낮춰 말하기
5. **법무 카피 순화:** "진단/처방/위험도" → "자가점검/가이드/참고자료"

### 상태
- `red_team_clear` 미달 지속 → 외부 발행·Pretotyping 광고·유료 제안 **BLOCK 유지**
- AR-037 (수정 5개 실행) → 완료 후 4차 Red Team 재도전 가능


---

## 2026-05-25 AR-038 — 4차 Red Team 재도전 (AR-037 수정 5개 반영 후)

**Reviewer:** Claude Sonnet 4.6 (독립 판정)
**Verdict:** `conditional_approve`
**Preconditions for Pretotyping:** 아래 3개 조건은 Pilot 착수 전까지 이행 (Pretotyping WTP 측정은 즉시 승인)
**correlation_id:** edu-consulting-20260524 / AR-038
**Evidence:** docs/reports/llm_outputs/claude_ar038_edu_red_team_4th_2026-05-25.md

### AR-037 수정 5개 해소 판정

| 항목 | 판정 |
|---|---|
| Phase 1 = Track B MVP only (타겟 오버랩) | ✅ 해소됨 |
| VP SLA 수치 정의 (AI 품질기준 명시) | ✅ 해소됨 |
| 모트 cold start 현실적 재정의 | ✅ 해소됨 (조건부) |
| Phase 1 검증 범위 S1~S4 제한 | ✅ 해소됨 |
| 법무 카피 순화 (진단→자가점검 등) | ✅ 해소됨 |

### 조건부 수정 요구사항 (Pilot 착수 전까지, Pretotyping blocker 아님)
1. Track B Step 구성 "부모 먼저" 업데이트 — CEO "부모 먼저" 원칙을 Step 1~4 콘텐츠 설계에 반영
2. 카카오 채널 Phase별 방식 명시 — "Phase 1=수동 발송, Phase 2=자동화(알림톡)" 명시
3. PIPA 동의 폼 — Pretotyping 랜딩에서 이메일 수집 시 개인정보 동의 포함

### 새로 발견된 약점 (blocker 아님)
- "부모 먼저" 커리큘럼과 Track B Step 구성 간 불일치 (Pilot 전 수정 권고)
- 카카오 알림톡 자동화는 Phase 2 이전 불가 (Phase 1 수동 발송 허용 명문화 확인)
- -0.68 상관 주장의 [speculative] 표기 일관성 점검 필요

### 상태 업데이트 (AR-038 Claude 4차 이후)
| 모델 | 판정 |
|---|---|
| Claude (1차) | CONDITIONAL BLOCK |
| Gemini (2차) | BLOCK |
| CEO/Codex (3차) | BLOCK |
| **Claude (4차)** | **conditional_approve** |
| Gemini (4차) | **대기 중** |
| **현재 상태** | **red_team_clear 미달 — Gemini 4차 판정 후 2-of-2 시 달성** |

→ Gemini 4차 `approve` 또는 `conditional_approve` → `red_team_clear` 달성 → Pretotyping 착수 가능

---

## 2026-05-25 AR-038 — Gemini 4차 판정 완료 → red_team_clear 달성

**Reviewer:** Gemini 1.5/2.0 (독립 판정)
**Verdict:** `conditional_approve`
**Evidence:** docs/reports/llm_outputs/gemini_ar038_edu_red_team_4th_2026-05-25.md
**correlation_id:** edu-consulting-20260524 / AR-038

### Gemini AR-037 수정 5개 해소 판정
| 항목 | 판정 |
|---|---|
| Phase 1 = Track B MVP only | ✅ 해소됨 |
| Phase 1 검증 범위 S1~S4 | ✅ 해소됨 |
| VP SLA 수치 정의 | ✅ 해소됨 |
| 모트 cold start 재정의 | ✅ 해소됨 |
| 법무 카피 순화 | ✅ 해소됨 |

### Gemini 추가 발견 (즉시 수정 완료)
1. **[Pretotyping blocker — 완료]** Track B Step 1~4 "부모 먼저" 업데이트 → EDU_ECONOMICS.md 수정 완료 (2026-05-25)
2. **[non-blocker — 완료]** Cross-sell 동선 모순 통일 → EDU_ECONOMICS.md Track A/B 방향 통일 완료

### ✅ red_team_clear 달성

| 모델 | 판정 |
|---|---|
| Claude (1차) | CONDITIONAL BLOCK |
| Gemini (2차) | BLOCK |
| CEO/Codex (3차) | BLOCK |
| Claude (4차) | conditional_approve |
| **Gemini (4차)** | **conditional_approve** |
| **2-of-2 합산** | **✅ red_team_clear 달성** |

**red_team_clear 기록일:** 2026-05-25
**Pretotyping 착수 조건:** red_team_clear ✅ + legal_review_approve (광고 카피) + qa_clear (랜딩)

---

## LLM Cost-Quality Operating Strategy (2026-06-01)

**대상:** `docs/governance/LLM_COST_QUALITY_STRATEGY.md` — OpenClaw/페르소나 LLM 비용·품질 운영 전략

### Red Team 1차 (v1.0)

| 모델 | 판정 |
|---|---|
| Gemini 2.5 Pro | clear-with-conditions |
| Codex / GPT-5 | block |
| Claude (synthesis) | 2-of-3 미달 → 조건 반영 |

**수렴된 핵심 지적 (2개 모델 독립 수렴):**
1. Lane A(기계적)는 무해한 배관이 아님 — 싼 모델 오류가 비싼 레인으로 cascade. 검증 게이트 필요.
2. Lane B(내부 추론)를 굶기면 Lane C(고객) 입력이 저질화 → "weak thinking 위 polished output".
3. 품질 텔레메트리 없는 볼륨 삭감 = blind austerity + 라벨 Goodharting.

**v1.1 반영:** ① Lane A 검증 게이트+승급 규칙 ② 볼륨 삭감 전 텔레메트리 선행 ③ 수익 추론 코어 보존+B→C 승급 경로

**현재 상태:** v1.1 clear-with-conditions. red_team_clear는 **2차 재검증 후** 확정 (미달성).

### Red Team 2차 (v1.1 → v1.2, 2026-06-01)

| 모델 | 2차 판정 |
|---|---|
| Gemini 2.5 Pro | clear-with-conditions |
| Codex / GPT-5 | clear-with-conditions |
| Claude | clear |
| **합산** | **✅ red_team_clear 달성** |

**원래 3개 지적: 전부 addressed 확인.**

신규 지적 4건 (구현 단계 이슈):
1. Lane A 시맨틱 오류 — spot-check 구현 시 추가
2. promote 태깅 실패 위험 — 고객 카피·가격·추천 auto-promote 정책
3. 복잡도 정의 부족 — 구현 시 ambiguity/요약/cross-agent 기준 추가
4. 텔레메트리 임계값 미정 — 구현 시 X%/Y기간/owner 명시

**✅ red_team_clear 기록일: 2026-06-01**
**다음 단계: 대표 승인 → 구현**

---

## 2026-06-10 — DC 공급망 확장 + Unmatched-Entity Miner (AR-031/032)

- 참여: Claude + Gemini + Codex (cross-LLM 3)
- 1차: Gemini=clear(minor 2), Codex=**block**(blocker 1 + major 3 + minor 1), Claude=findings
- Remediation 7건 반영 후 재확인 → **Codex=clear (5/5 resolved)**
- **✅ red_team_clear: 2026-06-10** — memo: docs/governance/RED_TEAM_DC_SUPPLY_CHAIN_2026-06-10.md
- 잔여: distinct_sources 피드 단위(publisher dedup 향후). 소스 활성화는 legal_review_approve 별도.

### 2026-06-10 (추가) — miner → CEO 결재 wiring

- 참여: Claude + Gemini + Codex
- R1: Gemini=(empty/재실행), Codex=**block** (blocker: 비서실장 명의 위조; major: 불안정 dedup키, 미sanitize 주입, 비원자 append)
- R2: Gemini=clear(4/4), Codex=block(잔여 #4 TOCTOU: 락 전 dedup 조회 경합)
- R3: Codex=**clear** — read→check→append를 단일 flock 내 원자화. 자금이동/auto-seed 없음, opportunity_approve 유지
- **✅ red_team_clear (wiring): 2026-06-10**

### 2026-06-10 (추가) — harness_score 로그 압축 정규화

- 참여: Claude + Gemini + Codex
- 진단: 비정규화 누적합+min(10) cap → 22/24 종목 10 포화 → ibkr_tws_paper_trader 진입정렬 변별력 상실
- R1: Gemini=block(음수 net 페널티), Codex=block(음수 net + 소비처 오인: turtle_auto_trader는 정적 meta)
- R2: 음수 v는 log 도메인 방어만, 소비처 정정 → Gemini=clear, Codex=block(페널티 상위 net floor에 있음 지적)
- R3: 페널티는 상위 net=max(0,total-neg)에 기존부터 반영(회귀 없음) 문서화 → **Codex=clear**
- **✅ red_team_clear: 2026-06-10** — round(2.3*ln(1+v)-1.5), v=net+0.8*dsrc. 분포 3~10, ≥7=상위 9.
- residual: 동적 universe.json(ibkr) vs 정적 HARNESS_UNIVERSE_META(turtle_auto_trader) 통합 미해결. 0미만 심화벌점 별도 스코프.

### 2026-06-10 (추가) — 동적/정적 유니버스 통합 + 0미만 심화 벌점

- 참여: Claude + Gemini + Codex
- 변경: (1) net_score 0 floor 제거(부정 우세 종목 sub-zero 벌점), theme 할인은 긍정 total에만.
  (2) turtle_auto_trader/harness_turtle_scan이 정적 META 대신 동적 universe.json(≥7, alpaca=US) 사용(정적 fallback).
- Codex=clear(minor 3: 청산 독립 확인·state파일 손실 edge·brokers vs region·동일헤드라인 양버킷=기존). Gemini=clear(minor 2: 결합도·docstring).
- 반영: alpaca 로더 region==US belt-and-suspenders 가드 추가, _compute_harness_score docstring 정정(net<0 허용 명시).
- **✅ red_team_clear: 2026-06-10** (AR-034)
- residual: state-file 손실 시 추적 고아(기존), 동일 헤드라인 양버킷 기여(기존), turtle_auto_trader↔scan 결합도(스타일).

### 2026-06-11 — 대시보드 모니터 동적 유니버스 통일

- 참여: Claude + Gemini + Codex
- 변경: alpaca get_full_dashboard(SIGNAL_UNIVERSE ETF→트레이더 동일 함수), ibkr cold-start(configs/universe.json 부재→load_trading_universe(broker=ibkr)).
- R1: Gemini=clear, Codex=block(2 major: alpaca fallback이 트레이더(_STATIC_FALLBACK_META)와 불일치; ibkr ≥7 하드필터가 broker 전체 쓰는 트레이더와 불일치).
- R2: alpaca=load_harness_universe_meta() 직접 사용(fallback까지 일치), ibkr=load_trading_universe(broker=ibkr) 무필터 → **Codex=clear**.
- **✅ red_team_clear: 2026-06-11** (AR-035). display-only, 주문/자금이동 없음. 프론트 빌드 불필요(데이터 소스 교정).

### 2026-06-11 (추가) — 데이터 수집 poll 가시성

- 참여: Claude + Gemini + Codex
- 변경: source_catalog poll 컬럼 + collector heartbeat(ok/empty/failed/skipped) + backend 파생 collection_health/poll_summary + 대시보드 적재/점검 분리. The_Robot_Report staged.
- R1: Gemini=clear(minor 3), Codex=block(3 blocker: 실적재 아닌 카운트, data.go.kr 비200→empty 오분류, RSS bozo 미검출).
- R2: save_raw_signal RETURNING id(실적재만 카운트), data.go.kr _any_200/_items_seen 판정, RSS bozo→failed → **Codex=clear**.
- **✅ red_team_clear: 2026-06-11** (AR-036). 신규 소스(Robot Report)는 enabled:false 게이트 대기.
