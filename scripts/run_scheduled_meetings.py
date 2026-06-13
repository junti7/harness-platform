"""도래한 예약 회의를 실행 (launchd가 1분마다 호출).

core.meeting_scheduler에 저장된 예약 중 시각이 된 것을 orchestrate로 실행하고
완료 표시한다. 멱등(idempotent): 실행 즉시 status를 바꿔 중복 실행을 막는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.meeting_scheduler import due_meetings, mark_done  # noqa: E402


def main() -> int:
    due = due_meetings()
    if not due:
        return 0

    from core.persona_state import personas_paused

    if personas_paused():
        # CEO 지시로 페르소나 활동 일시정지 — 예약 회의를 실행하지 않고 보류(상태 유지).
        # 정지 해제 시 due 상태로 남아 그때 실행된다.
        print(f"paused: {len(due)} meeting(s) deferred (personas paused)")
        return 0

    from adapters.content.orchestrator import orchestrate

    for rec in due:
        mark_done(rec["id"], status="running")  # 중복 실행 방지
        try:
            orchestrate(rec["order"], correlation_id=rec["id"])
            mark_done(rec["id"], status="done")
            print(f"executed {rec['id']}: {rec['order']!r}")
        except Exception as exc:  # noqa: BLE001
            mark_done(rec["id"], status="failed")
            print(f"failed {rec['id']}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
