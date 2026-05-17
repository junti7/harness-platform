# CEO Slack Command Patterns

Slack에서 OpenClaw에게 지시할 때는 장문 설명보다 아래 패턴을 우선 사용한다.

## Status / Health

1. `status 확인해줘`
2. `Harness 상태 보여줘`
3. `health check 해줘`
4. `control plane 상태 요약해줘`

## Decision Card

5. `research_report 7 decision card 보여줘`
6. `refined_output 3 결정 카드 보여줘`
7. `signal 12 decision card 만들어줘`
8. `research_report 9 모바일 승인 카드 보여줘`

## Approval Record

9. `refined_output 3 승인 기록해줘 approval_type: report_publish_approve decision: approved reason: mobile approve`
10. `research_report 7 보류 기록해줘 approval_type: qa_clear decision: hold reason: evidence 부족`
11. `signal 14 거절 기록해줘 approval_type: signal_approve decision: rejected reason: low relevance`
12. `research_report 11 승인 기록해줘 approval_type: investment_thesis_approve decision: approved reason: reviewed on mobile`

## Pipeline / Ops

13. `파이프라인 실행해줘`
14. `run pipeline 해줘`
15. `오늘 수동 파이프라인 한 번 돌려줘`
16. `pipeline 상태 이상하면 ops-incidents에 알려줘`

## Routing / Notes

17. `ops note 남겨줘: 오늘 파이프라인 수동 실행 예정`
18. `exec-president-decisions에 승인 대기 메모 남겨줘`

## Review / Clarification

19. `이 요청에 필요한 approval_type 후보만 보여줘`
20. `이 작업이 legal/red-team/qa 중 무엇이 부족한지 알려줘`

## Rules

- 승인 기록은 항상 `target_type id`, `decision`, `approval_type`, `reason`을 포함한다.
- 별도 프로젝트를 지정하지 않으면 기본 컨텍스트는 `harness-platform`이다.
- 짧은 운영 명령은 DM으로 보내고, 사람 간 논의는 각 Slack 채널에 남긴다.
