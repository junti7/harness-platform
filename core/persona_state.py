"""페르소나 자율 활동 일시정지 상태 (단일 출처).

CEO 지시(2026-06-13): 기존 페르소나들의 자율 발화/오케스트레이션 활동을 CEO 별도 지시까지
멈춘다. 목적은 불필요한 페르소나 토큰 소모 차단. 정지 대상은 *페르소나 LLM 발화*뿐이며,
거버넌스/청결/watchdog/backup 등 운영 생명유지 잡은 영향받지 않는다(이 헬퍼를 보지 않음).

활성화(둘 중 하나, 기본은 비정지 → 현행 동작 유지):
  1. env `PERSONA_ACTIVITIES_PAUSED` = 1/true/yes/on
  2. runtime/persona_pause.flag 파일 존재 (scripts/persona_pause.sh on)

flag 파일 경로는 gitignore된 runtime/ 아래라 코드(정지 로직)는 커밋되고 활성화 상태는
런타임 토글로 분리된다. 장기 데몬(slack-listener)은 메시지마다 fresh 평가하므로 재시작 불필요.
"""
from __future__ import annotations

import os
from pathlib import Path

_FLAG_FILE = Path(__file__).resolve().parents[1] / "runtime" / "persona_pause.flag"
_TRUTHY = {"1", "true", "yes", "on"}


def personas_paused() -> bool:
    """페르소나 자율 발화/오케스트레이션이 정지 상태인지. 기본 False(현행 동작)."""
    if os.getenv("PERSONA_ACTIVITIES_PAUSED", "").strip().lower() in _TRUTHY:
        return True
    try:
        return _FLAG_FILE.exists()
    except Exception:
        return False


def pause_reason() -> str:
    """정지 사유(있으면). flag 파일 내용 또는 env 기본 문구."""
    try:
        if _FLAG_FILE.exists():
            note = _FLAG_FILE.read_text(encoding="utf-8").strip()
            if note:
                return note
    except Exception:
        pass
    return "페르소나 활동 일시정지 중 (CEO 지시) — 지시는 DM으로 OpenClaw에게 주세요."
