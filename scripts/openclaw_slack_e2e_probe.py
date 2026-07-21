#!/usr/bin/env python3
"""Run a real-user Slack DM probe against the Mac Mini OpenClaw listener.

The human Slack token is deliberately read from macOS Keychain, never from
the project .env file or probe output.  Default mode checks prerequisites only;
--send is the explicit external-write step.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)
API_BASE = "https://slack.com/api"
DEFAULT_SERVICE = "harness-openclaw-slack-e2e-user-token"
DEFAULT_ACCOUNT = "junti7"
PROBE_TEXT = "오늘 온 메일 내용 요약해"
REJECTED_OUTPUT = (
    "최근 메일", "검색 조건", "본문 확인", "#outlook", "-webkit-text-size-adjust",
    "첫 항목 기준", "요점:",
)


class ProbeError(RuntimeError):
    """A safe, operator-actionable E2E failure."""


def _progress(message: str) -> None:
    print(f"[Slack E2E] {message}", file=sys.stderr, flush=True)


def _keychain_token(service: str, account: str) -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        text=True,
        capture_output=True,
        check=False,
    )
    token = result.stdout.strip()
    stderr = result.stderr.lower()
    if "user interaction is not allowed" in stderr or "interaction not allowed" in stderr:
        raise ProbeError(
            "SSH 세션에서는 macOS login Keychain을 읽을 수 없습니다. "
            "Mac Mini 화면에 직접 로그인한 Terminal에서 이 프로브를 실행하세요."
        )
    if result.returncode != 0 or not token.startswith("xoxp-"):
        raise ProbeError(
            "Keychain에 Slack 사용자 토큰이 없습니다. Slack OAuth 재승인 후 "
            f"service={service}, account={account}으로 xoxp 토큰을 저장하세요."
        )
    return token


def _api(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = httpx.post(
            f"{API_BASE}/{method}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProbeError(f"Slack API {method} 호출에 실패했습니다: {type(exc).__name__}") from exc
    if not data.get("ok"):
        raise ProbeError(f"Slack API {method} 거부: {data.get('error', 'unknown_error')}")
    return data


def _validate_answer(text: str) -> list[str]:
    failures = [f"금지된 기계형 표현: {term}" for term in REJECTED_OUTPUT if term.lower() in text.lower()]
    if not ("오늘은 업무상 처리할 메일이 없습니다." in text or "오늘 확인할 메일이" in text):
        failures.append("결론 문장이 없습니다")
    if "로그인 링크" in text and "직접 요청한 경우" not in text:
        failures.append("로그인 링크 안전 안내가 불완전합니다")
    return failures


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_bot_reply(messages: list[dict[str, Any]], bot_user_id: str, sent_ts: float) -> dict[str, Any] | None:
    candidates = [
        message for message in messages
        if float(message.get("ts", "0")) > sent_ts
        and (message.get("bot_id") or message.get("user") == bot_user_id)
    ]
    return min(candidates, key=lambda message: float(message["ts"])) if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw Slack DM E2E probe; --send performs one real user DM.")
    parser.add_argument("--send", action="store_true", help="Send the approved probe DM and wait for the bot reply.")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--keychain-service", default=os.environ.get("OPENCLAW_SLACK_E2E_KEYCHAIN_SERVICE", DEFAULT_SERVICE))
    parser.add_argument("--keychain-account", default=os.environ.get("OPENCLAW_SLACK_E2E_KEYCHAIN_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--artifact", type=Path, default=ROOT / "runtime" / "openclaw_slack_e2e_probe.json")
    args = parser.parse_args()

    artifact: dict[str, Any] = {"probe": "openclaw_slack_dm_e2e", "sent": False, "status": "blocked"}
    try:
        _progress("Keychain 사용자 토큰 확인 중")
        user_token = _keychain_token(args.keychain_service, args.keychain_account)
        bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
        ceo_user_id = os.environ.get("SLACK_CEO_USER_ID", "").strip()
        if not bot_token.startswith("xoxb-") or not ceo_user_id:
            raise ProbeError("SLACK_BOT_TOKEN 또는 SLACK_CEO_USER_ID 설정이 없습니다.")
        user_auth = _api(user_token, "auth.test", {})
        bot_auth = _api(bot_token, "auth.test", {})
        if user_auth.get("user_id") != ceo_user_id:
            raise ProbeError("Keychain 사용자 토큰 소유자가 SLACK_CEO_USER_ID와 다릅니다.")
        artifact.update({"user_id_verified": True, "bot_user_id": bot_auth.get("user_id")})
        if not args.send:
            artifact["status"] = "ready"
            _write_artifact(args.artifact, artifact)
            print(json.dumps(artifact, ensure_ascii=False))
            return 0

        _progress("CEO 사용자 토큰 확인 완료; OpenClaw DM 열기")
        channel = _api(user_token, "conversations.open", {"users": bot_auth["user_id"]})["channel"]
        marker = uuid.uuid4().hex[:8]
        _progress("승인된 테스트 DM 전송")
        sent = _api(user_token, "chat.postMessage", {"channel": channel["id"], "text": PROBE_TEXT})
        sent_ts = float(sent["ts"])
        artifact.update({"sent": True, "probe_id": marker, "channel_id": channel["id"]})
        _progress(f"OpenClaw 응답 대기 중 (최대 {args.timeout_seconds}초)")
        deadline = time.monotonic() + args.timeout_seconds
        reply: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            history = _api(user_token, "conversations.history", {"channel": channel["id"], "limit": 30})
            reply = _find_bot_reply(history.get("messages", []), bot_auth["user_id"], sent_ts)
            if reply:
                break
            time.sleep(2)
        if not reply:
            raise ProbeError("시간 내 OpenClaw 응답이 없습니다. Mac Mini Slack listener 로그를 확인하세요.")
        answer = str(reply.get("text", ""))
        failures = _validate_answer(answer)
        artifact.update({"reply_received": True, "quality_failures": failures, "status": "pass" if not failures else "fail"})
        _write_artifact(args.artifact, artifact)
        print(json.dumps(artifact, ensure_ascii=False))
        return 0 if not failures else 2
    except ProbeError as exc:
        artifact["reason"] = str(exc)
        _write_artifact(args.artifact, artifact)
        print(json.dumps(artifact, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
