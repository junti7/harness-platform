# Jarvis — Channel Assignments

# Charter §4 | 채널 신설 시 SLACK_CHANNEL_CREATION_LOG.md entry 선행 필수

## Home / 운영 채널

| 채널 | 역할 | data_class |
|---|---|---|
| `#exec-president-decisions` | CEO decision card 상신 | confidential |
| `#회의실` (conference room) | persona 토론 소집·중재·수렴 | public-internal |
| `#ops-incidents` | 장애·경보·cap 초과 보고 | public-internal |

## 신설 권한

Jarvis는 새 회의실/작업 채널을 신설할 수 있다. 단 Charter §6에 따라:

1. 신설 **전** `docs/operations/SLACK_CHANNEL_CREATION_LOG.md`에 entry 기록 (date/creator=Jarvis/channel_name/why/basis/participants/data_class/owner/retention).
2. 그 다음 Slack 채널 생성.
3. `scripts/check_slack_channel_log.py`가 일일 reconciliation으로 검증.

## 회의실 운영 규칙

- 소집: order에 2개 이상 persona 협업이 필요할 때.
- 수렴: autonomous CC 깊이 3 hop 초과 시 Jarvis가 강제 정리.
- 산출: consensus 또는 dissent를 DB에 기록 후 CEO card로 상신. 회의실 대화 자체는 system of record 아님.
