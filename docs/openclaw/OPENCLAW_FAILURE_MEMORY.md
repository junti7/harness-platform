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

## FM-005 Briefing Collapsed To Status
- input_text: AI 교육 사업 관련해서 지금까지 진행된 내용을 요약해서 브리핑 하세요.
- wrong_behavior: topic briefing 요청을 `status` bridge로 축약해 현재 control-plane 상태만 반환한다.
- expected_behavior: business topic briefing은 일반 비서 브리핑 경로로 보내고, 필요 시 관련 파일/기록을 짧게 확인해 요약한다.
- root_cause: `브리핑/요약` 같은 보고 요청이 Haiku intent router에서 status intent로 과잉 분류되었다.
- fix_rule: `브리핑`, `요약`, `정리`가 포함된 주제 브리핑 요청은 read-only status tool classification에서 제외한다.
- trigger_patterns: ["브리핑", "요약", "정리", "AI 교육 사업", "진행된 내용"]

## FM-006 Meeting Summon Misread As Minutes Status
- input_text: Pretotyping 랜딩 페이지 제작하려면 어떻게 해야할지 논의하기 위한 회의 소집해.
- wrong_behavior: 새 회의 소집 요청을 `minutes-latest` 조회로 오인해 최근 회의록만 보여준다.
- expected_behavior: `회의 소집`은 orchestration request로 취급하고 전사/가상 회의 소집 경로 또는 일반 작업 계획 경로로 보낸다.
- root_cause: `회의`와 `어떻게`가 함께 들어간 문장을 모두 회의 상태 조회로 우회 매칭했다.
- fix_rule: `회의 소집`, `소집해`, `회의 열어`, `논의하기 위한 회의` 패턴은 `minutes-latest` bypass에서 제외한다.
- trigger_patterns: ["회의 소집", "소집해", "논의하기 위한 회의", "Pretotyping"]
