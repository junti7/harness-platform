# OpenClaw Route Audit Summary (route-audit) - 2026-05-31

## Summary

- records_reviewed: 431
- blocked_records: 83
- blocked_rate: 19.3%

## Route Counts

- local_chat: 80
- premium_chat: 60
- structured_command_auth_block: 56
- deterministic_arithmetic: 54
- structured_bridge: 50
- economy_chat: 45
- deterministic_newsletter_status: 27
- contextual_risk_block: 27
- deterministic_status_brief: 17
- deterministic_gmail_summary: 8
- premium_tool_agent: 3
- bypass_ar_list: 2
- intent_bridge: 1
- bypass_minutes_latest: 1

## Route Classes

- other: 137
- deterministic: 106
- local: 80
- premium: 63
- economy: 45

## Risk Counts

- low: 346
- medium: 58
- high: 27

## Blocked Routes

- structured_command_auth_block: 56
- contextual_risk_block: 27

## Model Usage

- none: 242
- gemma4:latest: 80
- claude-sonnet-4-5: 63
- claude-haiku-4-5: 46

## Response Length

- overall_avg_response_chars: 65.5
- route::deterministic_newsletter_status avg_chars=305.0
- route::contextual_risk_block avg_chars=168.0
- route::deterministic_status_brief avg_chars=133.4
- route::deterministic_gmail_summary avg_chars=90.0
- route::structured_command_auth_block avg_chars=87.0
- route::premium_chat avg_chars=14.0
- route::economy_chat avg_chars=11.5
- route::local_chat avg_chars=8.7
- route::deterministic_arithmetic avg_chars=6.5
- route::structured_bridge avg_chars=2.0
- trailing_7d_avg_chars: 65.5
- on_after_2026-05-31_avg_chars: 65.5

## Target Query Routing

### top risk / risk
- total: 32
- deterministic/local/economy/premium: 17/0/10/5
- premium_avoided_rate: 84.4%
- before_2026-05-31: total=15, premium=5
- on_after_2026-05-31: total=17, premium=0
- route::deterministic_status_brief = 17
- route::economy_chat = 10
- route::premium_chat = 5

### mail / gmail
- total: 8
- deterministic/local/economy/premium: 8/0/0/0
- premium_avoided_rate: 100.0%
- before_2026-05-31: total=0, premium=0
- on_after_2026-05-31: total=8, premium=0
- route::deterministic_gmail_summary = 8

### status / ops
- total: 31
- deterministic/local/economy/premium: 0/0/0/0
- premium_avoided_rate: 100.0%
- before_2026-05-31: total=23, premium=0
- on_after_2026-05-31: total=8, premium=0
- route::structured_bridge = 31


## Risk Flags

- high_risk_term: 85
- contextual_reference: 45
- contextual_high_risk_reference: 27

## Recent Blocked Examples

- `contextual_risk_block` | risk=high | message=`그거 보내줘` | reason=⚠️ 이 요청은 이전 대화의 민감한 대상에 대한 참조형 실행 요청으로 감지됐습니다.
- `structured_command_auth_block` | risk=low | message=`파이프라인 실행해줘` | reason=❌ 이 명령은 CEO 승인 surface에서만 바로 실행할 수 있습니다.
- `structured_command_auth_block` | risk=medium | message=`/goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16` | reason=❌ 이 명령은 CEO 승인 surface에서만 바로 실행할 수 있습니다.
- `contextual_risk_block` | risk=high | message=`그거 보내줘` | reason=⚠️ 이 요청은 이전 대화의 민감한 대상에 대한 참조형 실행 요청으로 감지됐습니다.
- `structured_command_auth_block` | risk=low | message=`파이프라인 실행해줘` | reason=❌ 이 명령은 CEO 승인 surface에서만 바로 실행할 수 있습니다.

## Failure Memory Candidates

### Candidate: structured_command_auth_block / high_risk_term
- count: 28
- sample_input: /goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16
- observed_behavior: blocked by `structured_command_auth_block`
- expected_behavior: keep blocked unless a precise target, destination, and required gate are supplied
- root_cause: ambiguous or high-risk Slack instruction needs explicit preflight/human gate
- trigger_terms: ['subscriber']
### Candidate: structured_command_auth_block / no_flags
- count: 28
- sample_input: 파이프라인 실행해줘
- observed_behavior: blocked by `structured_command_auth_block`
- expected_behavior: keep blocked unless a precise target, destination, and required gate are supplied
- root_cause: ambiguous or high-risk Slack instruction needs explicit preflight/human gate
- trigger_terms: []
### Candidate: contextual_risk_block / high_risk_term, contextual_reference, contextual_high_risk_reference
- count: 27
- sample_input: 그거 보내줘
- observed_behavior: blocked by `contextual_risk_block`
- expected_behavior: keep blocked unless a precise target, destination, and required gate are supplied
- root_cause: ambiguous or high-risk Slack instruction needs explicit preflight/human gate
- trigger_terms: ['초안', '뉴스레터']

## Operator Note

Do not automatically append these candidates to `docs/openclaw/OPENCLAW_FAILURE_MEMORY.md`.
Promote only after human review, because rule-based tripwires are not proof of general correctness.
