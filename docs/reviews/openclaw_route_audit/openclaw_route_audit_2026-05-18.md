# OpenClaw Route Audit Summary - 2026-05-18

## Summary

- records_reviewed: 11
- blocked_records: 3
- blocked_rate: 27.3%

## Route Counts

- premium_chat: 3
- deterministic_arithmetic: 2
- structured_command_auth_block: 2
- deterministic_newsletter_status: 1
- contextual_risk_block: 1
- structured_bridge: 1
- local_chat: 1

## Risk Counts

- low: 8
- medium: 2
- high: 1

## Blocked Routes

- structured_command_auth_block: 2
- contextual_risk_block: 1

## Model Usage

- none: 7
- claude-sonnet-4-5: 3
- gemma4:latest: 1

## Risk Flags

- high_risk_term: 3
- contextual_reference: 1
- contextual_high_risk_reference: 1

## Recent Blocked Examples

- `contextual_risk_block` | risk=high | message=`그거 보내줘` | reason=⚠️ 이 요청은 이전 대화의 민감한 대상에 대한 참조형 실행 요청으로 감지됐습니다.
- `structured_command_auth_block` | risk=low | message=`파이프라인 실행해줘` | reason=❌ 이 명령은 CEO 승인 surface에서만 실행할 수 있습니다.
- `structured_command_auth_block` | risk=medium | message=`/goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16` | reason=❌ 이 명령은 CEO 승인 surface에서만 실행할 수 있습니다.

## Failure Memory Candidates

- No repeated blocked pattern reached the promotion threshold.

## Operator Note

Do not automatically append these candidates to `docs/openclaw/OPENCLAW_FAILURE_MEMORY.md`.
Promote only after human review, because rule-based tripwires are not proof of general correctness.
