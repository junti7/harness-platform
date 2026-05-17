## FM-001 Status Intent Miss
- input_text: status 확인해줘
- wrong_behavior: 일반 챗봇처럼 "어떤 상태를 원하시나요?"라고 되묻는다.
- expected_behavior: `openclaw_codex_bridge.py status --format text`를 실행하고 핵심 상태를 요약한다.
- root_cause: 짧은 운영 명령이 tool/bridge intent로 분류되지 않았다.
- fix_rule: `status`, `상태`, `health`, `헬스`는 기본적으로 Harness control-plane status intent로 처리한다.
- trigger_patterns: ["status", "상태", "health", "헬스"]

## FM-002 Missing Approval Fields
- input_text: refined_output 3 승인 기록해줘
- wrong_behavior: approval_type 없이 대충 승인 처리하거나 자유서술로 남긴다.
- expected_behavior: `decision`과 `approval_type` 누락을 명시하고, 유효한 예시 한 줄을 보여준다.
- root_cause: canonical approval semantics를 강제하지 않고 자연어를 과도하게 추론했다.
- fix_rule: 승인 기록은 `target_type id + decision + approval_type`가 없으면 실행하지 않는다.
- trigger_patterns: ["승인 기록", "approve", "approval_type", "record-decision"]

## FM-003 Project Context Drift
- input_text: decision card 보여줘
- wrong_behavior: 다른 서비스나 일반 업무 도우미 맥락으로 답한다.
- expected_behavior: 기본 프로젝트를 `harness-platform`으로 보고, 필요한 target type/id를 물어본다.
- root_cause: Slack DM의 기본 작업공간 가정이 프롬프트에 없었다.
- fix_rule: 별도 프로젝트가 명시되지 않으면 기본 컨텍스트는 `harness-platform`이다.
- trigger_patterns: ["decision card", "카드", "harness-platform", "signal", "research_report"]

## FM-004 Governance Overclaim
- input_text: 이거 바로 발행 승인해줘
- wrong_behavior: Legal, Red Team, QA 확인 없이 승인 가능한 것처럼 답한다.
- expected_behavior: 필요한 precondition을 확인하고 누락 시 block 또는 human review를 알린다.
- root_cause: governance guardrail보다 작업 완료 압력이 우선되었다.
- fix_rule: high-impact publish/paid approval은 legal, red-team, qa precondition을 확인하기 전에는 확정하지 않는다.
- trigger_patterns: ["발행 승인", "publish", "qa_clear", "legal_review_approve", "red_team_clear"]
