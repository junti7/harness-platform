# AR (Action Required) Protocol
# Version: 1.0 | [매우 중요] 비서실장 일일 이행 점검 규약

---

## 1. AR이란

AR(Action Required)은 대표님 또는 부대표님과 **명시적으로 약속한 실행 항목**이다.

AR은 말로만 끝나지 않는다. 기한 내에 이행되지 않으면 비서실장이 이행을 촉구하고,
그래도 이행되지 않으면 대표님께 즉시 보고한다.

AR이 되는 항목:
- 오케스트레이션 회의의 **권고 액션(Recommended Actions)**
- 대표님/부대표님이 직접 지시한 항목
- 게이트 이행 약속 (legal_review_approve, red_team_clear, pre_mortem_approve, qa_clear 등)
- Slack DM으로 접수된 명시적 지시

---

## 2. AR 구조

```json
{
  "id": "AR-20260522-001",
  "title": "TARS님 스티비 연동 계획 추가",
  "owner": "tars",
  "source_correlation_id": "orch-7f6f6d0b",
  "priority": "high",
  "status": "open",
  "created_at": "2026-05-22T21:50:45",
  "due_by": "2026-05-24",
  "description": "메일리 어댑터와 동일한 구조로 스티비 연동 계획 작성",
  "evidence_required": "stibee_publisher.py 설계 문서 또는 코드 PR",
  "last_checked_at": null,
  "reminder_count": 0,
  "completed_at": null,
  "completion_note": null
}
```

### Priority 기준

| Priority | 기한 기본값 | 이행 촉구 시점 |
|----------|-------------|---------------|
| `critical` | 당일 | 6시간 후 미완 시 즉시 CEO 보고 |
| `high`     | 2영업일 | 기한 당일 오전 경고 + 초과 시 즉시 보고 |
| `medium`   | 5영업일 | 기한 초과 시 보고 |
| `low`      | 14일 | 기한 초과 시 보고 |

---

## 3. 비서실장 일일 점검 사이클 (08:00 KST)

```
1. AR 목록 로드 (docs/reports/ar_tracker.jsonl)
2. 기한 초과(overdue) AR 확인
   → 담당 페르소나에게 즉시 이행 촉구 메시지 발송
   → CEO #exec-president-decisions 에 즉시 보고
3. 오늘 기한(due today) AR 확인
   → 담당자에게 오늘 내 완료 요청
4. 진행 중(in_progress) AR 현황 질의
   → 담당 페르소나에게 진행 현황 보고 요청
5. 전체 AR 현황 요약을 CEO 채널에 보고
   → 완료: N건 / 진행중: N건 / 지연: N건
```

---

## 4. 이행 촉구 에스컬레이션

| 단계 | 조건 | 액션 |
|------|------|------|
| 1차 촉구 | 기한 당일 오전 | 담당 페르소나 채널 경고 |
| 2차 촉구 | 기한 + 1일 초과 | CEO 채널 보고 + 담당자 직접 ping |
| 3차 촉구 | 기한 + 3일 초과 | CEO 모바일 카드로 긴급 보고 + `reminder_count` 기록 |
| 강제 종결 | 기한 + 7일 초과 | CEO 확인 후 `waived` 또는 재할당 |

---

## 5. AR 완료 조건

AR은 다음 중 하나가 충족될 때만 `completed`로 표시된다:
- 담당 페르소나가 `completion_note`에 결과물(파일 경로, URL, 요약)을 첨부
- 대표님 또는 부대표님이 직접 완료 확인
- 비서실장이 결과물을 검증하고 `completed` 상태로 갱신

"보고했다", "작업했다"는 말만으로는 완료 처리하지 않는다.

---

## 6. 저장 위치

- AR 원장: `docs/reports/ar_tracker.jsonl`
- 일일 점검 로그: `logs/ar_checker.log`
- 관련 프로토콜: `docs/governance/GATE_TRACKER.md` (게이트 → AR 연동)
