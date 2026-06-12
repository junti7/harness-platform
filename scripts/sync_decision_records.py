#!/usr/bin/env python3
"""결재·리뷰 기록 자동 sync — 프로덕션(Mac Mini)에서 생성된 결재/감사 기록을 origin으로 환원.

배경:
  APPROVAL_REQUESTS.json(CEO 결재 상태), openclaw_approval_handoffs.jsonl(결재 핸드오프 로그),
  docs/reviews/edu_pilot_red_team/(red-team 리뷰 산출물)는 *프로덕션 런타임이 생성*하는
  비즈니스 결재·감사 기록이다. 코드 드리프트 가드(check_code_drift.py)는 오탐 방지를 위해
  이 경로들을 제외하므로, 이들은 아무도 모르게 dirty로 쌓이다가 ff/배포를 막는다.
  버리는 쓰레기가 아니라 보존해야 할 기록이므로 gitignore가 아니라 *origin 환원*이 정답이다.

안전 설계 — 라이브 작업트리를 절대 건드리지 않는다:
  merge/rebase/checkout/reset/stash 를 쓰지 않는다. 대신 git plumbing 으로
  "origin/main 트리 + 화이트리스트 파일의 현재 워킹트리 내용"을 임시 인덱스에 합성하고,
  parent=origin/main 인 commit 을 만들어 ff-push 한다.
  → HEAD, 인덱스, 다른 런타임 dirty 파일(data/edu_research, paper_trading 등)을 일절 안 만진다.
  → 화이트리스트 외 경로는 어떤 경우에도 커밋되지 않는다(코드는 절대 push 안 됨).

동시성:
  fetch~push 사이 dev(MBP)가 push 하면 non-ff 로 거절된다. 그때는 새 origin/main 위에서
  커밋을 다시 합성해 재시도(기록 경로는 코드와 disjoint 라 항상 선형으로 들어감).

사용:
  PYTHONPATH=. .venv/bin/python scripts/sync_decision_records.py            # 실제 sync
  PYTHONPATH=. .venv/bin/python scripts/sync_decision_records.py --dry-run  # push 없이 진단만
  PYTHONPATH=. .venv/bin/python scripts/sync_decision_records.py --slack    # push/에러 시 Slack

종료 코드: 변경 push=0, no-op=0, 에러=1.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REMOTE = "origin"
BRANCH = "main"

# origin 으로 환원할 화이트리스트.
#  - 정확 파일(EXACT_FILES): 단일 기록/상태 파일
#  - 디렉터리(DIR_PREFIXES): 그 아래 모든 파일(리뷰 산출물 등)
# 이 목록 밖의 어떤 경로도 이 잡은 절대 커밋하지 않는다.
EXACT_FILES = [
    "docs/operations/APPROVAL_REQUESTS.json",
    "docs/reports/openclaw_approval_handoffs.jsonl",
]
DIR_PREFIXES = [
    "docs/reviews/edu_pilot_red_team/",
]

MAX_PUSH_RETRIES = 3

# 낙관적 동시성 마커: 이 sync 가 마지막으로 origin 에 올린 화이트리스트 파일의 blob 해시.
# runtime/ 는 gitignore 라 dirty 를 만들지 않는다. dev(MBP) 등 외부에서 origin 의 같은 파일을
# 우리 모르게 바꾸면(=현재 origin blob != 마커 && prod 워킹본과도 다름) 덮어쓰지 않고 중단한다.
SYNC_STATE_PATH = PROJECT_ROOT / "runtime" / "decision_record_sync_state.json"

# 설계상 명시: 이 잡은 origin 의 화이트리스트 파일을 **추가/갱신만** 한다(삭제 전파 안 함).
# 결재·감사 기록은 한번 origin 에 남으면 보존이 원칙이므로, prod 에서 로컬 삭제돼도 origin 에서
# 지우지 않는다(실수로 감사 기록을 날리는 사고 방지). — Codex red-team MAJOR(삭제) 의도적 결정.


def _git(*args: str, check: bool = True, capture: bool = True) -> str:
    res = subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=capture,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return (res.stdout or "").strip()


def _slack(msg: str) -> None:
    url = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()
    if not url:
        return
    try:
        data = json.dumps({"text": msg}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # Slack 실패가 sync 를 막지 않는다


def _whitelisted_working_paths() -> list[str]:
    """워킹트리에 실제 존재하는 화이트리스트 파일 경로(repo-relative)를 모은다."""
    paths: list[str] = []
    for rel in EXACT_FILES:
        if (PROJECT_ROOT / rel).is_file():
            paths.append(rel)
    for prefix in DIR_PREFIXES:
        base = PROJECT_ROOT / prefix
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    paths.append(p.relative_to(PROJECT_ROOT).as_posix())
    return paths


def _is_stable(rel: str) -> bool:
    """torn-write(런타임이 쓰는 중 절단된 파일) 방지 — JSON/JSONL 파싱 가능해야 안정으로 본다."""
    p = PROJECT_ROOT / rel
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return False
    if rel.endswith(".json"):
        try:
            json.loads(text)
            return True
        except Exception:
            return False
    if rel.endswith(".jsonl"):
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                json.loads(line)
            except Exception:
                return False
        return True
    return True  # .md 등은 검증 대상 아님(생성기가 원자적 기록 가정)


def _hash_object(rel: str) -> str:
    return _git("hash-object", "--", rel)


def _origin_blob(rel: str) -> str | None:
    res = subprocess.run(
        ["git", "rev-parse", f"{REMOTE}/{BRANCH}:{rel}"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
    )
    return res.stdout.strip() if res.returncode == 0 else None


def _load_sync_state() -> dict[str, str]:
    try:
        return json.loads(SYNC_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sync_state(state: dict[str, str]) -> None:
    try:
        SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = SYNC_STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, SYNC_STATE_PATH)  # 원자적 교체
    except Exception:
        pass


def _detect_external_conflict(paths: list[str], state: dict[str, str]) -> list[str]:
    """origin 의 화이트리스트 파일이 우리가 마지막으로 올린 이후 외부(dev)에 의해 바뀌고,
    prod 워킹본과도 달라 덮어쓰면 origin 변경을 잃는 경우를 찾는다(낙관적 동시성)."""
    conflicts: list[str] = []
    for rel in paths:
        o_blob = _origin_blob(rel)
        if o_blob is None:
            continue  # origin 에 없음 → 신규 추가, 충돌 아님
        last = state.get(rel)
        if last is None:
            continue  # 마커 없음(최초) → prod 권위로 채택, 충돌 처리 안 함
        if o_blob != last and o_blob != _hash_object(rel):
            # origin 이 우리 모르게 바뀌었고, prod 가 올리려는 내용과도 다름 → 클로버 위험
            conflicts.append(rel)
    return conflicts


def _build_commit_against_origin(base_sha: str, paths: list[str]) -> tuple[str | None, str]:
    """임시 인덱스에 (origin/main 트리 + 화이트리스트 워킹파일)을 합성해 tree 를 만든다.

    반환: (tree_sha 또는 변경없음이면 None, base_tree_sha)
    라이브 인덱스(.git/index)는 GIT_INDEX_FILE 격리로 절대 건드리지 않는다.
    """
    base_tree = _git("rev-parse", f"{base_sha}^{{tree}}")
    tmp_index = tempfile.NamedTemporaryFile(prefix="sync_didx_", delete=False)
    tmp_index.close()
    try:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = tmp_index.name
        # 임시 인덱스를 origin/main 트리로 초기화
        subprocess.run(["git", "read-tree", base_sha], cwd=str(PROJECT_ROOT), env=env, check=True,
                       capture_output=True, text=True)
        # 화이트리스트 워킹파일을 임시 인덱스에 stage(워킹트리 내용 그대로)
        if paths:
            subprocess.run(["git", "update-index", "--add", "--", *paths],
                           cwd=str(PROJECT_ROOT), env=env, check=True, capture_output=True, text=True)
        tree = subprocess.run(["git", "write-tree"], cwd=str(PROJECT_ROOT), env=env, check=True,
                              capture_output=True, text=True).stdout.strip()
        if tree == base_tree:
            return None, base_tree
        return tree, base_tree
    finally:
        try:
            os.unlink(tmp_index.name)
        except OSError:
            pass


def sync(dry_run: bool = False, slack: bool = False) -> int:
    # 0) origin 최신화
    _git("fetch", REMOTE, "--quiet")

    paths = _whitelisted_working_paths()
    if not paths:
        print("[sync] 화이트리스트 파일이 워킹트리에 없음 — no-op")
        return 0

    # torn-write 방지: 하나라도 불안정(쓰는 중)이면 이번 회차는 통째로 건너뛴다(다음 시각 재시도).
    unstable = [p for p in paths if not _is_stable(p)]
    if unstable:
        print(f"[sync] 불안정 파일 감지(쓰는 중 추정) — 이번 회차 skip: {', '.join(unstable)}")
        return 0

    state = _load_sync_state()
    # 외부(dev) 동시 편집으로 origin 변경을 덮어쓸 위험이면 push 하지 않고 중단 → 사람이 reconcile.
    conflicts = _detect_external_conflict(paths, state)
    if conflicts:
        msg = "외부 변경과 충돌(덮어쓰기 위험) — sync 중단: " + ", ".join(conflicts)
        print(f"[sync] ✖ {msg}", file=sys.stderr)
        if slack:
            _slack(f":warning: decision-record-sync {msg} — 수동 reconcile 필요")
        return 1

    for attempt in range(1, MAX_PUSH_RETRIES + 1):
        base_sha = _git("rev-parse", f"{REMOTE}/{BRANCH}")
        tree, base_tree = _build_commit_against_origin(base_sha, paths)
        if tree is None:
            print(f"[sync] 화이트리스트 기록이 origin/{BRANCH}와 동일 — 변경 없음(no-op)")
            _save_sync_state({**state, **{p: _hash_object(p) for p in paths}})
            return 0

        # 무엇이 바뀌는지 진단(파일 단위)
        changed = _git("diff", "--name-only", base_tree, tree).splitlines()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if dry_run:
            print(f"[sync][dry-run] origin/{BRANCH}({base_sha[:7]}) 대비 push 예정 파일 {len(changed)}개:")
            for c in changed:
                print(f"  - {c}")
            return 0

        msg = (
            "chore(auto): sync prod decision records\n\n"
            f"프로덕션(Mac Mini) 결재·리뷰 기록 {len(changed)}건을 origin/{BRANCH}로 자동 환원.\n"
            + "".join(f"- {c}\n" for c in changed)
            + f"\nsynced_at: {ts}\n"
            "by: scripts/sync_decision_records.py (com.harness.decision-record-sync)\n\n"
            "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
        )
        # 무인 실행이라 author/committer 신원을 명시한다(launchd 컨텍스트에 user.* 미설정이어도
        # 실패하지 않고, 자동 결재기록 커밋이 사람 커밋과 섞이지 않게 봇 신원으로 남긴다).
        commit_env = os.environ.copy()
        commit_env.update({
            "GIT_AUTHOR_NAME": "harness-decision-record-sync",
            "GIT_AUTHOR_EMAIL": "automation@harness.local",
            "GIT_COMMITTER_NAME": "harness-decision-record-sync",
            "GIT_COMMITTER_EMAIL": "automation@harness.local",
        })
        commit_sha = subprocess.run(
            ["git", "commit-tree", tree, "-p", base_sha],
            cwd=str(PROJECT_ROOT), input=msg, text=True, capture_output=True, env=commit_env,
        )
        if commit_sha.returncode != 0:
            print(f"[sync] commit-tree 실패: {commit_sha.stderr.strip()}", file=sys.stderr)
            if slack:
                _slack(f":rotating_light: decision-record-sync commit-tree 실패: {commit_sha.stderr.strip()}")
            return 1
        new_sha = commit_sha.stdout.strip()

        # ff-push (parent=origin/main 이므로 정상 상황에선 항상 ff)
        push = subprocess.run(
            ["git", "push", REMOTE, f"{new_sha}:{BRANCH}"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        )
        if push.returncode == 0:
            print(f"[sync] ✓ push 완료 {base_sha[:7]}→{new_sha[:7]} ({len(changed)}개 기록)")
            _save_sync_state({**state, **{p: _hash_object(p) for p in paths}})
            if slack:
                _slack(
                    f":outbox_tray: 결재·리뷰 기록 {len(changed)}건 origin 환원 "
                    f"(`{new_sha[:7]}`): " + ", ".join(Path(c).name for c in changed)
                )
            return 0

        # non-ff 등 거절 → origin 이 움직였다. fetch 후, 외부가 화이트리스트 파일을 건드렸는지
        # 재확인하고(클로버 방지) 깨끗하면 새 base 위에 재합성.
        print(f"[sync] push 거절(attempt {attempt}/{MAX_PUSH_RETRIES}): {push.stderr.strip()}")
        _git("fetch", REMOTE, "--quiet")
        conflicts = _detect_external_conflict(paths, state)
        if conflicts:
            msg = "재시도 중 외부 변경과 충돌 — 중단: " + ", ".join(conflicts)
            print(f"[sync] ✖ {msg}", file=sys.stderr)
            if slack:
                _slack(f":warning: decision-record-sync {msg} — 수동 reconcile 필요")
            return 1

    print("[sync] 재시도 초과 — push 실패", file=sys.stderr)
    if slack:
        _slack(":rotating_light: decision-record-sync 재시도 초과로 push 실패 — 수동 확인 필요")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="결재·리뷰 기록 origin 자동 sync")
    ap.add_argument("--dry-run", action="store_true", help="push 없이 변경 예정만 출력")
    ap.add_argument("--slack", action="store_true", help="push/에러 시 Slack 알림")
    args = ap.parse_args()
    try:
        return sync(dry_run=args.dry_run, slack=args.slack)
    except Exception as exc:  # noqa: BLE001
        print(f"[sync] 예외: {exc}", file=sys.stderr)
        if args.slack:
            _slack(f":rotating_light: decision-record-sync 예외: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
