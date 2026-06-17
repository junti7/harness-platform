#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "runtime" / "edu_pattern_intelligence.json"
OUTPUT_PATH = ROOT / "runtime" / "edu_pattern_fact_check.json"


def _atomic_write_json(path: Path, payload: Any) -> None:
    """런타임 아티팩트를 원자적으로 쓴다(tmp 작성 → fsync → os.replace).

    backend 가 이 스크립트를 timeout 으로 돌리다 쓰기 도중 SIGKILL 하면 직접 write_text 는
    잘린 JSON 을 남겨 프론트가 빈 화면으로 떨어진다. 같은 디렉터리 tmp 에 쓰고 fsync 후
    os.replace 로 교체해 torn-file 을 막는다. (호스트 크래시 수준 내구성은 비목표 — timeout/SIGKILL 한정.
    tmp 는 고유 이름이라 충돌하지 않으며, SIGKILL 시 드물게 남는 orphan .tmp 는 무해한 cosmetic 잔여물이다.
    overlap 안전을 위해 다른 writer 의 tmp 를 건드리는 일괄 정리는 하지 않는다.)
    """
    import os
    import shutil
    import sys
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        # mkstemp 는 0600 새 inode 라, os.replace 후 기존 파일의 권한 메타데이터가 사라진다.
        # 하위호환 보존:
        #  - 기존 파일: copystat 으로 mode/flags/xattr(ACL 포함, macOS) 승계 + chown 으로 uid/gid 승계
        #    (SGID 디렉터리/상속 그룹 보존). 동일 사용자 실행이라 chown 은 보통 no-op·허용.
        #  - 신규 파일: mkstemp 기본 0600 유지. write_text(0644)보다 제한적이라 권한 *확대*가 없고
        #    (동일 사용자 reader 는 영향 없음), 전역 umask 조작(스레드 비안전)을 피한다.
        # 메타데이터 승계 실패는 삼키지 않고 stderr 경고만 남긴다(쓰기는 계속 — staleness 회피 우선).
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
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _status_for_pattern(pattern: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    support = int(pattern.get("supporting_evidence_count") or 0)
    distinct_sources = int(pattern.get("distinct_source_types") or 0)
    source_types = set(pattern.get("source_types") or [])
    complaints = int(pattern.get("complaint_count") or 0)
    score = float(pattern.get("pattern_score") or 0.0)

    if support < 2:
        reasons.append("supporting_evidence_count < 2")
    if distinct_sources < 2:
        reasons.append("distinct_source_types < 2")
    if "research_policy" not in source_types and "transcript" not in source_types:
        reasons.append("research_policy or transcript support missing")
    if score < 2.5:
        reasons.append("pattern_score < 2.5")
    if complaints > 0 and support == complaints:
        reasons.append("all support is complaint-driven")

    if not reasons:
        return "supported", ["minimum support, source diversity, and score thresholds passed"]
    if support >= 2 and score >= 2.5:
        return "weakly_supported", reasons
    if support == 0:
        return "needs_more_data", ["no supporting evidence"]
    return "needs_more_data", reasons


def build_fact_check() -> dict[str, Any]:
    payload = _load_json(INPUT_PATH)
    patterns = payload.get("patterns") or []
    results = []
    for pattern in patterns:
        status, reasons = _status_for_pattern(pattern)
        results.append(
            {
                "pattern_id": pattern.get("pattern_id"),
                "label": pattern.get("label"),
                "segment": pattern.get("segment"),
                "status": status,
                "reasons": reasons,
                "metrics": {
                    "supporting_evidence_count": pattern.get("supporting_evidence_count"),
                    "distinct_source_types": pattern.get("distinct_source_types"),
                    "source_types": pattern.get("source_types"),
                    "pattern_score": pattern.get("pattern_score"),
                    "complaint_count": pattern.get("complaint_count"),
                },
            }
        )
    summary = Counter(result["status"] for result in results)
    return {
        "generated_at": _now_iso(),
        "status": "ok" if payload else "missing_input",
        "input_path": str(INPUT_PATH.relative_to(ROOT)),
        "policy": {
            "minimum_supporting_evidence_count": 2,
            "minimum_distinct_source_types": 2,
            "required_anchor_support": "research_policy or transcript",
            "minimum_pattern_score": 2.5,
            "complaint_guard": "complaint-only support cannot auto-pass",
        },
        "summary": dict(summary),
        "patterns": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fact check the latest Edu pattern intelligence artifact.")
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout.")
    parser.add_argument("--write", action="store_true", help="Write runtime artifact.")
    args = parser.parse_args()

    payload = build_fact_check()
    if args.write or not args.stdout:
        _atomic_write_json(OUTPUT_PATH, payload)
    if args.stdout:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
