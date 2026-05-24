# OpenClaw Task-Packet Message Payloads (Version 1.1)

본 문서는 `STRATEGY_PIVOT_INTERNAL_INVESTMENT.md` 전략에 따라 정의된 7개 Action Required(AR-016 ~ AR-022) 과제들을 OpenClaw 에이전트 오케스트레이터 및 `dispatch_llm_task_packet.py`가 즉시 파싱 및 자동 실행할 수 있도록 표준 JSON Task-Packet 포맷으로 정립한 스펙 명세서입니다.

> **v1.1 변경사항 (2026-05-24)**: AR 번호 기존 AR-009~015와 충돌 방지를 위해 AR-016~022로 재부여. `.env` 보안 파일 input_artifacts에서 제거.

---

## 📌 Task Packet Schema Overview
모든 패킷은 다음의 스키마를 준수합니다:
* `generated_at`: ISO 8601 타임스탬프 (생성 시각)
* `owner`: 발행 주체 (`"Codex Chief of Staff"`)
* `task_kind`: 에이전트별 태스크 카테고리
* `title`: 과제명
* `objective`: 상세 수행 지침 (Objective)
* `input_artifacts`: 입력 참조 파일 경로 목록
* `output_artifacts`: 출력 산출물 파일 경로 목록
* `checks`: 검증 통과용 체크리스트
* `notes`: 구현 주의사항 및 마크업

---

## 🚀 7대 Action Required Task-Packets

```json
[
  {
    "generated_at": "2026-05-24T16:03:00",
    "owner": "Codex Chief of Staff",
    "task_kind": "orchestration_pivot",
    "title": "[AR-016] 사업구조 전환 — 내부 투자 엔진 전환 착수 총괄",
    "objective": "Jarvis, 오늘부터 Harness의 사업 모델을 B2C 뉴스레터 발행에서 내부 투자 의사결정 엔진(B2I)으로 전면 전환한다. 기존 Substack/Maily 외부 뉴스레터 발행 및 독자 모집 계획은 전면 보류(hold)하며, 이를 위해 5대 협력 부서(KITT, Watchman, Ledger, Vision, TARS)에 상세 AR 지시를 하달하고 관리하라. 최종 결정을 SOUL.md에 기록하고 오케스트레이션 루프의 변수들을 재지정하라.",
    "input_artifacts": [
      "docs/operations/ACTION_REQUIRED_REGISTRY.json",
      "AGENTS.md"
    ],
    "output_artifacts": [
      "SOUL.md"
    ],
    "checks": [
      "SOUL.md에 2026-05-24 자 전략 전환 결정 명시 기록 완료 여부",
      "기존의 모든 B2C 뉴스레터 발행 관련 AR을 보류(hold) 상태로 일괄 전환 완료 여부",
      "전환에 따른 신규 AR-017~AR-022를 레지스트리에 온전하게 등록 완료 여부"
    ],
    "notes": [
      "비서실장으로서의 최종 오버헤드 통제 및 에스컬레이션 임계값 설정을 포함할 것.",
      "경과 사항은 slack_channel_exec_president_decisions에 CEO 모바일 카드로 보고할 것."
    ],
    "callback_route": "agent_openclaw_routing"
  },
  {
    "generated_at": "2026-05-24T16:03:00",
    "owner": "Codex Chief of Staff",
    "task_kind": "legal_review",
    "title": "[AR-017] 내부 투자 운영 법률 검토 및 자기계정 적법성 진단",
    "objective": "KITT, 당사 자본을 미국 Interactive Brokers(IBKR) 해외 계좌에 예치하여 미국 및 한국 상장 ETF를 자기계정으로 직접 운용 및 매매하는 형태에 대해 한국 자본시장법 및 관련 약관 규정상 적법성을 진단하라. 외국환거래법상 자금 송금 시 세관/한국은행 사전 신고 의무 준수 여부, 소득세 과세 방식(양도소득세 등), 그리고 당사 LLM 분석 리포트를 사내에서 참고하는 행위가 투자자문업/일임업에 저촉되는지 여부를 명백하게 규명하라.",
    "input_artifacts": [
      "AGENTS.md"
    ],
    "output_artifacts": [
      "docs/reports/legal/self_trading_review_2026-05.md"
    ],
    "checks": [
      "자기계정 거래가 투자일임업/자문업 등록 예외 대상(원칙적 적법)인지 명문화 여부",
      "해외 송금 시 외국환거래법상 요구되는 신고 절차의 가이드라인 제시 여부",
      "cross-LLM 검증(Claude + GPT reasoning 2개 모델 독립 검토) 후 legal_review_approve 서명 완료 여부"
    ],
    "notes": [
      "외부 전문 변호사 법률 자문이 요구되는 리스크 파트는 legal_review_block으로 마킹하고 예산 청구를 기재할 것."
    ],
    "callback_route": "agent_openclaw_routing"
  },
  {
    "generated_at": "2026-05-24T16:03:00",
    "owner": "Codex Chief of Staff",
    "task_kind": "risk_assessment",
    "title": "[AR-018] 투자 사업 전환 리스크 레지스터 업데이트 및 킬스위치 제안",
    "objective": "Watchman, B2I 모델 전환에 따른 신규 리스크 5대 요소(자본 손실, Physical AI 테마 편중, IBKR API 세션 끊김, 외국환거래법 저촉, LLM 환각 주문 오류)를 식별하고 리스크 레지스터를 긴급 개정하라. 특히, 초기 예산 $7,000 USD 대비 최대 허용 자본 손실 폭(Stop-Loss)을 규정하여, 한도 도달 시 모든 거래를 강제 차단하는 킬스위치 트리거를 KILL_CRITERIA.md에 반영하라.",
    "input_artifacts": [
      "docs/governance/RISK_REGISTER.md",
      "docs/governance/KILL_CRITERIA.md"
    ],
    "output_artifacts": [
      "docs/governance/RISK_REGISTER.md",
      "docs/governance/KILL_CRITERIA.md"
    ],
    "checks": [
      "신규 리스크 5대 요소의 발생 확률, 영향도, 완화 조치 추가 완료 여부",
      "KILL_CRITERIA.md 내에 초기 자본 대비 명확한 투자 중단 트리거 한도(% 및 절대금액) 추가 여부"
    ],
    "notes": [
      "주간 red-team 검증을 통해 Bear Case 분석과 Hallucination 방지 조치가 병행되었는지 체크할 것."
    ],
    "callback_route": "agent_openclaw_routing"
  },
  {
    "generated_at": "2026-05-24T16:03:00",
    "owner": "Codex Chief of Staff",
    "task_kind": "capital_planning",
    "title": "[AR-019] 투자 초기 자본 준비 상태 점검 및 예산 시나리오 제안",
    "objective": "Ledger, 사내 현금흐름 및 자본 현황을 조사하여 리스크 한도 내에서 가용한 초기 투자 여유 자금을 정확히 산출하라. 초기 투자 규모 시나리오 3가지(Conservative: 소액, Balanced: 중액, Aggressive: 대액)를 제안하고, 매월 지출되는 고정 LLM API 비용 대비 투자 소득 분기점(BEP)을 계산하여 capital_readiness_note를 리포트하라.",
    "input_artifacts": [
      "harness-os/backend/main.py"
    ],
    "output_artifacts": [
      "docs/reports/finance/capital_plan_2026-05.md"
    ],
    "checks": [
      "초기 투자 예산 $7,000 USD에 부합하는 unit economics 시나리오 산출 완료 여부",
      "LLM 소모 비용(5월 누적 $4.72 등) 대비 재무적 burn rate 가이드라인 제시 여부"
    ],
    "notes": [
      "실제 자본 집행은 대표의 capital_action_approve 승인이 떨어질 때까지 strictly 보류 상태를 명시할 것."
    ],
    "callback_route": "agent_openclaw_routing"
  },
  {
    "generated_at": "2026-05-24T16:03:00",
    "owner": "Codex Chief of Staff",
    "task_kind": "thesis_template",
    "title": "[AR-020] Physical AI 투자 thesis 표준 템플릿 설계",
    "objective": "Vision, 기존 Physical AI 리서치 파이프라인(Tier 1~3) 정제 보고서 출력을 즉각 투자 매매 판단으로 매핑할 수 있도록 '표준 투자 Thesis 템플릿'을 설계하라. 템플릿은 신호 개요, 투자 근거(Thesis), 타깃 ETF/종목 명세, 진입 트리거(Entry), 청산/익절 트리거(Exit), Thesis 무효화 조건(Invalidation), 확신 점수(Confidence)를 반드시 포함하도록 구성해야 한다.",
    "input_artifacts": [
      "DESIGN.md"
    ],
    "output_artifacts": [
      "docs/trading/INVESTMENT_THESIS_TEMPLATE.md"
    ],
    "checks": [
      "DESIGN.md 철학인 'Decision Card' 규격과 일체화되어 모바일 스캔이 60초 내로 가능한 구조인지 검증 여부",
      "Entry & Exit 및 무효화(Stop-Loss) 정의 슬롯 완비 여부"
    ],
    "notes": [
      "불필요한 서술형 문장을 지양하고 핵심 지표 위주의 risk-first 테이블 구조로 디자인할 것."
    ],
    "callback_route": "agent_openclaw_routing"
  },
  {
    "generated_at": "2026-05-24T16:03:00",
    "owner": "Codex Chief of Staff",
    "task_kind": "technical_onboarding",
    "title": "[AR-021] IBKR 온보딩 기술 준비 상태 점검 및 자동화 backlog 도출",
    "objective": "TARS, 실거래 자동화를 위한 API 인프라 준비 상태를 파악하라. ibkr_onboarding_status.json의 미구현 6단계 스텝을 검증하고, gateway 동작을 통한 인증 활성화 및 scripts/ibkr_cp_client.py에 구현되어 있는 기능 스코프(시세/주문/잔고)를 상세 기술 점검하여 paper trading 테스트 플랜을 정의하라.",
    "input_artifacts": [
      "docs/trading/ibkr_onboarding_status.json",
      "docs/trading/etf_whitelist_v0.json"
    ],
    "output_artifacts": [
      "docs/reports/technical/ibkr_readiness_2026-05.md"
    ],
    "checks": [
      "온보딩 6단계 스텝의 기술적 완료 조건 명시 및 해결 방법 도출 여부",
      "IBKR Client Portal API 연동 에러(preflight.ok=false) 원인 파악 및 해결 절차 수립 여부"
    ],
    "notes": [
      "GitHub Copilot CLI 및 Codex의 Feasibility Agent를 활용하여 누락된 라이브러리 및 Gateway 연결 스펙을 조사할 것."
    ],
    "callback_route": "agent_openclaw_routing"
  },
  {
    "generated_at": "2026-05-24T16:03:00",
    "owner": "Codex Chief of Staff",
    "task_kind": "kpi_transition",
    "title": "[AR-022] KPI 및 Goal Loop 전환 및 SOUL.md 갱신",
    "objective": "Friday, 사업 운영 모델의 코어 KPI를 기존 B2C 구독 지표에서 내부 투자 지표(IBKR 개설 완료율, Thesis 생성 및 검증 성공률, 포트폴리오 MDD 준수율 등)로 완전 재설정하라. 또한, SOUL.md의 히스토리에 이 중대한 사업 모델 전환 결정을 박제하고, 기존 open_ar들 중 뉴스레터 관련 과제는 hold로 분류하며 Goal Loop의 파라미터 변수들을 신규 모델에 맞추어 갱신하라.",
    "input_artifacts": [
      "SOUL.md",
      "docs/operations/ACTION_REQUIRED_REGISTRY.json"
    ],
    "output_artifacts": [
      "SOUL.md",
      "docs/operations/ACTION_REQUIRED_REGISTRY.json"
    ],
    "checks": [
      "기존 subscription 기반 KPI 비활성화 및 신규 투자 KPI로의 goal_health_brief 재설계 완료 여부",
      "SOUL.md 역사 기록 완료 및 hold 과제 처리 완료 여부"
    ],
    "notes": [
      "가장 신속하게 처리되어야 하는 과제이므로, Jarvis 오케스트레이션 개시 직후 24시간 이내에 최종 리포트를 작성할 것."
    ],
    "callback_route": "agent_openclaw_routing"
  }
]
```
