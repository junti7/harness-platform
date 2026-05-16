# Red Team Diagnosis Response
# Date: 2026-05-14
# Scope: Apply / reject decisions for external red-team feedback on harness-platform

---

## 1. Executive Verdict

외부 레드팀 진단의 큰 방향은 맞다.

특히 다음 네 가지는 현재 코드/운영 현실과 직접 충돌하므로 채택한다.

1. 파이프라인 고도화를 제품 가치로 착각하지 말 것
2. DB/schema/model identity를 "기초 위생"이 아니라 hard gate로 볼 것
3. 운영 취약성을 artifact quality blocker로 취급할 것
4. Physical AI 해석을 한국 현장 의사결정과 더 강하게 연결할 것

다만 아래 항목은 그대로 받지 않는다.

- `5월 14일 발행일은 절대 타협 불가`
  - 이유: 발행 일정은 중요하지만 `qa_clear`, `red_team_clear`, `legal_review_approve`를 무시하는 절대 명령이 될 수 없다.
  - 적용 방식: "미루기 위한 완벽주의"는 금지하되, 품질/법률 게이트는 유지한다.

- `현대차 울산 공장 AMR 도입 비용`, `삼성 HBM 병목` 같은 구체 문맥을 프롬프트에 강제 기입
  - 이유: source-backed가 아니면 쉽게 환각을 강제한다.
  - 적용 방식: "구체적 한국 pain point와 연결"은 채택하되, 수치/사실은 반드시 source 기반일 때만 서술한다.

---

## 2. Adopted Actions

### 2.1 Product-over-Pipeline rule 채택

반영 파일:

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AUTOMATION_EXECUTION_PLAN.md`

적용 내용:

- 새 infra 작업은 `artifact quality`, `factual trust`, `paid conversion` 중 하나를 직접 개선할 때만 우선순위를 가진다.
- pipeline sophistication 자체를 성공처럼 보고하지 않는다.

### 2.2 System integrity preflight 채택

반영 파일:

- `scripts/system_integrity_check.py`
- `run_pipeline.py`
- `scripts/openclaw_codex_bridge.py`
- `scripts/openclaw_ops_sync.py`

적용 내용:

- pipeline 시작 전 DB 테이블/컬럼, 핵심 env, 모델 식별 상태를 점검한다.
- 누락 시 즉시 실패 처리한다.
- OpenClaw status / ops brief에도 integrity 결과를 노출한다.

### 2.3 Fact posture 강화 채택

반영 파일:

- `configs/prompts/physical_ai_analyst.md`
- `adapters/content/qa_agent.py`
- `docs/QA_PLAYBOOK.md`

적용 내용:

- 핵심 claim은 `verified / company-self-report / speculative` 중 하나로 분류해야 한다.
- QA는 self-report를 독립 검증처럼 서술하면 block 사유로 본다.

### 2.4 Korea-specific decision utility 강화 채택

반영 파일:

- `configs/prompts/physical_ai_analyst.md`
- `docs/QA_PLAYBOOK.md`

적용 내용:

- 단순 글로벌 뉴스 요약이 아니라, 한국 제조/반도체/물류/도입 현장의 pain point와 연결하도록 프롬프트를 강화했다.
- 단, 근거 없는 특정 비용/공장 내부 수치는 금지한다.

---

## 3. Explicit Rejections

### Reject A — Hard publish date over governance gates

적용하지 않음.

이유:

- Harness의 현재 위험은 "발행 지연" 못지않게 "약한 리포트를 유료 가치처럼 포장"하는 데 있다.
- deadline이 `qa_clear`, `red_team_clear`, `legal_review_approve`를 압도하면, 장기적으로 더 큰 신뢰 손실을 만든다.

대신 적용한 원칙:

- 발행을 미루기 위한 완벽주의는 금지
- 하지만 gate bypass도 금지

### Reject B — Force specific local claims without source support

적용하지 않음.

이유:

- "현대차 울산 공장 AMR 도입 비용" 같은 문구를 source 없이 강제하면, prompt가 insight가 아니라 fabrication pressure가 된다.
- SemiAnalysis급 글의 핵심은 구체성 자체가 아니라 **검증 가능한 구체성**이다.

대신 적용한 원칙:

- 한국 현장 맥락 연결은 의무
- 구체 수치/사실은 source-backed일 때만 허용

---

## 4. Net Result

이번 반영은 새로운 기능 확장이 아니라 다음 착시를 줄이는 데 초점을 맞췄다.

- "파이프라인이 복잡하니 제품도 좋다"
- "DB나 모델 식별 불일치는 나중에 고치면 된다"
- "운영 보고 timeout은 부차적 문제다"
- "한국 맥락은 대충 프롬프트에 넣으면 된다"

현재 상태는 여전히 premium artifact 품질이 병목이다.

하지만 이제 최소한:

- schema/env/model mismatch는 hard blocker가 됐고
- ops health에 integrity가 보이며
- Tier 3 prompt와 QA 기준이 "돈 되는 해석" 쪽으로 더 조여졌다.
