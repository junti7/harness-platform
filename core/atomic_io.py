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

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


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
