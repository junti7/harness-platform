"""원자적 파일 쓰기 유틸(torn-file 방지).

배경(2026-06-20, Red Team): 여러 프로세스(ibkr_turtle_monitor, ibkr_tws_paper_trader, backend
cold-start/selection-flow)가 같은 상태 파일(ibkr_tws_positions.json)을 교차로 읽고 쓴다.
writer 가 `write_text(json.dumps(...))` 로 비원자적으로 쓰면, 쓰는 도중 reader 가 읽을 때
잘린 JSON(JSONDecodeError)을 만날 수 있다. tmp 에 쓰고 fsync 후 os.replace 로 교체하면
reader 는 항상 '이전 완전본' 또는 '새 완전본' 중 하나만 보게 된다.

(호스트 크래시 수준 내구성은 비목표 — 동시 read/write 중 torn-read 방지가 목표.
tmp 는 고유 이름이라 충돌하지 않으며, SIGKILL 시 드물게 남는 orphan .tmp 는 무해한 cosmetic 잔여물.
overlap 안전을 위해 다른 writer 의 tmp 를 건드리는 일괄 정리는 하지 않는다.)
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


def update_json_atomic(
    path: Path,
    mutate: "Callable[[dict], None]",
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> dict:
    """파일 락 하에 **디스크 최신본**을 읽어 mutate(state) 적용 후 원자적으로 저장한다.

    배경(2026-06-21 사고 — 절대 재발 금지): 같은 JSON 상태 파일(`ibkr_tws_positions.json`)을
    여러 프로세스가 read-modify-write 하는데, 각자 *오래된 in-memory 전체본을 통째로 save* 하면
    last-writer-wins 로 서로의 변경을 덮어쓴다. 실제로 IBKR 트레이더의 reconcile 이 체결된
    SK하이닉스(000660)를 pending→positions 로 승격·저장했는데, 동시에 돈 모니터가 stale 한
    pending(승격 전)을 통째로 다시 써서 승격을 **revert** → 체결 포지션이 손절 모니터링에서
    누락되는 위험이 발생했다.

    이 함수는 ① 동일 파일 전용 `.lock` 에 **exclusive flock** ② 락 안에서 *디스크 최신본 재독*
    ③ `mutate` 로 **호출자의 델타만** 적용 ④ 원자적 교체(atomic_write_json) 로, 동시 writer 들의
    변경이 서로를 덮어쓰지 않게 한다.

    [mutate 계약 — 위반 시 race 부활]
      - 받은 `state` 는 *디스크 최신본*이다. **자기 소유 필드/델타만** 적용한다.
        예) 트레이더: 자기가 추가한 positions 키만 set, pending_orders(자기 소유) 갱신.
            모니터: 자기가 청산한 positions 키만 pop, nav_history/signal_alerts(자기 소유) 갱신.
      - **남이 소유한 필드를 통째로 대입하지 말 것**(예: 모니터가 pending_orders 를 쓰면 안 됨).
      - 손상 shape 내성: state 가 dict 아니면 빈 dict 로 시작한다.

    반환: 저장된 최종 dict(검증/로깅용).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = str(path) + ".lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if not isinstance(current, dict):
                current = {}
        except Exception:
            current = {}
        mutate(current)
        atomic_write_json(path, current, indent=indent, ensure_ascii=ensure_ascii)
        return current
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def atomic_write_json(path: Path, payload: Any, *, indent: int = 2, ensure_ascii: bool = False) -> None:
    """payload 를 path 에 원자적으로 JSON 직렬화한다(tmp → fsync → os.replace).

    기존 파일이 있으면 mode/uid/gid 를 승계(copystat + chown)해 권한 메타데이터를 보존한다.
    신규 파일은 mkstemp 기본 0600 을 유지(권한 확대 없음, 전역 umask 조작 회피). 직렬화 실패 시
    tmp 를 정리하고 예외를 올리며 *기존 파일을 손상시키지 않는다*.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        try:
            if path.exists():
                _st = os.stat(path)
                shutil.copystat(path, tmp)
                try:
                    os.chown(tmp, _st.st_uid, _st.st_gid)
                except (PermissionError, OSError):
                    pass
        except Exception as _meta_err:
            print(f"[atomic_write] metadata carry-over warning for {path.name}: {_meta_err}", file=sys.stderr)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=ensure_ascii, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise
