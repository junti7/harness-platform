# OpenClaw Route Audit Summary (daily) - 2026-05-18

## Summary

- records_reviewed: 22
- blocked_records: 6
- blocked_rate: 27.3%

## Route Counts

- premium_chat: 6
- deterministic_arithmetic: 4
- structured_command_auth_block: 4
- deterministic_newsletter_status: 2
- contextual_risk_block: 2
- structured_bridge: 2
- local_chat: 2

## Risk Counts

- low: 16
- medium: 4
- high: 2

## Blocked Routes

- structured_command_auth_block: 4
- contextual_risk_block: 2

## Model Usage

- none: 14
- claude-sonnet-4-5: 6
- gemma4:latest: 2

## Risk Flags

- high_risk_term: 6
- contextual_reference: 2
- contextual_high_risk_reference: 2

## Recent Blocked Examples

- `contextual_risk_block` | risk=high | message=`그거 보내줘` | reason=⚠️ 이 요청은 이전 대화의 민감한 대상에 대한 참조형 실행 요청으로 감지됐습니다.
- `structured_command_auth_block` | risk=low | message=`파이프라인 실행해줘` | reason=❌ 이 명령은 CEO 승인 surface에서만 실행할 수 있습니다.
- `structured_command_auth_block` | risk=medium | message=`/goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16` | reason=❌ 이 명령은 CEO 승인 surface에서만 실행할 수 있습니다.
- `contextual_risk_block` | risk=high | message=`그거 보내줘` | reason=⚠️ 이 요청은 이전 대화의 민감한 대상에 대한 참조형 실행 요청으로 감지됐습니다.
- `structured_command_auth_block` | risk=low | message=`파이프라인 실행해줘` | reason=❌ 이 명령은 CEO 승인 surface에서만 실행할 수 있습니다.

## Failure Memory Candidates

### Candidate: structured_command_auth_block / high_risk_term
- count: 2
- sample_input: /goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16
- observed_behavior: blocked by `structured_command_auth_block`
- expected_behavior: keep blocked unless a precise target, destination, and required gate are supplied
- root_cause: ambiguous or high-risk Slack instruction needs explicit preflight/human gate
- trigger_terms: ['subscriber']
### Candidate: structured_command_auth_block / no_flags
- count: 2
- sample_input: 파이프라인 실행해줘
- observed_behavior: blocked by `structured_command_auth_block`
- expected_behavior: keep blocked unless a precise target, destination, and required gate are supplied
- root_cause: ambiguous or high-risk Slack instruction needs explicit preflight/human gate
- trigger_terms: []
### Candidate: contextual_risk_block / high_risk_term, contextual_reference, contextual_high_risk_reference
- count: 2
- sample_input: 그거 보내줘
- observed_behavior: blocked by `contextual_risk_block`
- expected_behavior: keep blocked unless a precise target, destination, and required gate are supplied
- root_cause: ambiguous or high-risk Slack instruction needs explicit preflight/human gate
- trigger_terms: ['초안', '뉴스레터']

## Operator Note

Do not automatically append these candidates to `docs/openclaw/OPENCLAW_FAILURE_MEMORY.md`.
Promote only after human review, because rule-based tripwires are not proof of general correctness.
