"""Tailnet-only, short-lived mobile OAuth handoff for the gog Gmail runtime."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse


class MobileOAuthError(RuntimeError):
    """Safe-to-display OAuth failure without credentials or authorization codes."""


@dataclass(frozen=True)
class MobileOAuthConfig:
    enabled: bool
    account: str
    client: str
    redirect_uri: str
    gog_bin: str
    keyring_backend: str
    keyring_password: str
    state_path: Path
    openclaw_bin: str = "/opt/homebrew/bin/openclaw"
    discord_target: str = ""
    ttl_seconds: int = 300

    @classmethod
    def from_env(cls) -> "MobileOAuthConfig":
        return cls(
            enabled=os.getenv("HARNESS_GMAIL_MOBILE_OAUTH_ENABLED", "false").lower() in {"1", "true", "yes"},
            account=os.getenv("HARNESS_GMAIL_ACCOUNT", "").strip(),
            client=os.getenv("HARNESS_GMAIL_MOBILE_OAUTH_CLIENT", "mobile").strip(),
            redirect_uri=os.getenv("HARNESS_GMAIL_MOBILE_OAUTH_REDIRECT_URI", "").strip(),
            gog_bin=os.getenv("HARNESS_GMAIL_GOG_BIN", "/opt/homebrew/bin/gog").strip(),
            keyring_backend=os.getenv("HARNESS_GMAIL_KEYRING_BACKEND", "").strip(),
            keyring_password=os.getenv("HARNESS_GMAIL_KEYRING_PASSWORD", "").strip(),
            state_path=Path(os.getenv(
                "HARNESS_GMAIL_MOBILE_OAUTH_STATE_PATH",
                str(Path.home() / ".harness" / "gmail_mobile_oauth_state.json"),
            )).expanduser(),
            openclaw_bin=os.getenv("HARNESS_OPENCLAW_BIN", "/opt/homebrew/bin/openclaw").strip(),
            discord_target=os.getenv("HARNESS_GMAIL_MOBILE_OAUTH_DISCORD_TARGET", "").strip(),
            ttl_seconds=max(60, min(300, int(os.getenv("HARNESS_GMAIL_MOBILE_OAUTH_TTL_SECONDS", "300")))),
        )


Runner = Callable[..., subprocess.CompletedProcess[str]]
_LOCK = threading.Lock()
_STATE_RE = re.compile(r"https://[^\s]+")


def _validate_config(config: MobileOAuthConfig) -> None:
    if not config.enabled:
        raise MobileOAuthError("모바일 Gmail 재인증 기능이 비활성 상태입니다.")
    if not config.account or not config.client or not config.redirect_uri:
        raise MobileOAuthError("모바일 Gmail 재인증 설정이 완전하지 않습니다.")
    if not config.discord_target:
        raise MobileOAuthError("모바일 Gmail 재인증 Discord 완료 알림 대상이 설정되지 않았습니다.")
    parsed = urlparse(config.redirect_uri)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.path.endswith("/callback"):
        raise MobileOAuthError("모바일 OAuth 콜백은 HTTPS callback 주소여야 합니다.")


def _env(config: MobileOAuthConfig) -> dict[str, str]:
    env = os.environ.copy()
    if config.keyring_backend:
        env["GOG_KEYRING_BACKEND"] = config.keyring_backend
    if config.keyring_password:
        env["GOG_KEYRING_PASSWORD"] = config.keyring_password
    return env


def _base_args(config: MobileOAuthConfig) -> list[str]:
    return [
        config.gog_bin, "auth", "add", config.account,
        "--client", config.client,
        "--remote",
        "--redirect-uri", config.redirect_uri,
        "--services", "gmail,calendar",
        "--gmail-scope", "readonly",
        "--force-consent",
        "--timeout", f"{config.ttl_seconds}s",
    ]


def _run(runner: Runner, args: list[str], config: MobileOAuthConfig, timeout: int) -> subprocess.CompletedProcess[str]:
    return runner(args, capture_output=True, text=True, timeout=timeout, check=False, env=_env(config))


def _write_state(config: MobileOAuthConfig, state: str, expires_at: int) -> None:
    path = config.state_path
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = {"state_sha256": hashlib.sha256(state.encode()).hexdigest(), "expires_at": expires_at}
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def start(config: MobileOAuthConfig, *, runner: Runner = subprocess.run, now: int | None = None) -> dict[str, object]:
    _validate_config(config)
    proc = _run(runner, _base_args(config) + ["--step", "1"], config, 20)
    if proc.returncode != 0:
        raise MobileOAuthError("Google 인증 링크 생성에 실패했습니다.")
    match = _STATE_RE.search(proc.stdout or "")
    if not match:
        raise MobileOAuthError("Google 인증 링크를 확인하지 못했습니다.")
    auth_url = match.group(0).strip()
    state = parse_qs(urlparse(auth_url).query).get("state", [""])[0]
    if not state:
        raise MobileOAuthError("Google 인증 상태값을 확인하지 못했습니다.")
    issued_at = int(time.time() if now is None else now)
    with _LOCK:
        _write_state(config, state, issued_at + config.ttl_seconds)
    return {"auth_url": auth_url, "expires_at": issued_at + config.ttl_seconds, "ttl_seconds": config.ttl_seconds}


def exchange(
    config: MobileOAuthConfig,
    callback_url: str,
    *,
    runner: Runner = subprocess.run,
    now: int | None = None,
) -> dict[str, object]:
    _validate_config(config)
    parsed = urlparse(callback_url)
    state = parse_qs(parsed.query).get("state", [""])[0]
    code = parse_qs(parsed.query).get("code", [""])[0]
    if parsed.scheme != "https" or f"{parsed.scheme}://{parsed.netloc}{parsed.path}" != config.redirect_uri:
        raise MobileOAuthError("OAuth 콜백 주소가 일치하지 않습니다.")
    if not state or not code:
        raise MobileOAuthError("Google 승인 결과가 완전하지 않습니다.")

    current = int(time.time() if now is None else now)
    with _LOCK:
        try:
            saved = json.loads(config.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            raise MobileOAuthError("인증 요청이 없거나 이미 사용되었습니다.") from exc
        expected = str(saved.get("state_sha256") or "")
        actual = hashlib.sha256(state.encode()).hexdigest()
        if not hmac.compare_digest(expected, actual):
            raise MobileOAuthError("OAuth 상태값이 일치하지 않습니다.")
        if current > int(saved.get("expires_at") or 0):
            config.state_path.unlink(missing_ok=True)
            raise MobileOAuthError("인증 링크가 만료되었습니다. Discord에서 새 링크를 요청하세요.")
        # Claim before exchange: callbacks are strictly one-use, including failed/replayed exchanges.
        config.state_path.unlink(missing_ok=True)

    proc = _run(runner, _base_args(config) + ["--step", "2", "--auth-url", callback_url], config, 40)
    if proc.returncode != 0:
        raise MobileOAuthError("Google 자격 증명 저장에 실패했습니다. 새 링크로 다시 시도하세요.")

    checks = [
        [config.gog_bin, "auth", "list", "--client", config.client, "--check", "--json"],
        [config.gog_bin, "gmail", "search", "newer_than:1d", "--client", config.client, "-a", config.account, "--max", "1", "--json", "--results-only", "--gmail-no-send"],
        [config.gog_bin, "calendar", "events", "primary", "--client", config.client, "--from", "today", "--max", "1", "-a", config.account, "--json", "--results-only"],
    ]
    for args in checks:
        checked = _run(runner, args, config, 25)
        if checked.returncode != 0:
            raise MobileOAuthError("자격 증명은 저장했지만 Gmail/Calendar 실검증에 실패했습니다.")
    delivery: dict[str, object] = {"attempted": True, "succeeded": False}
    for _attempt in range(3):
        notified = _run(
            runner,
            [
                config.openclaw_bin, "message", "send", "--channel", "discord",
                "--target", config.discord_target,
                "--message", "Gmail 재인증 완료. Gmail·Calendar 실조회까지 통과했습니다.",
                "--json",
            ],
            config,
            25,
        )
        if notified.returncode == 0:
            delivery["succeeded"] = True
            try:
                receipt = json.loads(notified.stdout or "{}")
                delivery["message_id"] = str(
                    receipt.get("messageId") or receipt.get("message_id") or receipt.get("id") or ""
                )
            except json.JSONDecodeError:
                pass
            break
    if not delivery["succeeded"]:
        raise MobileOAuthError("Gmail·Calendar 인증은 완료했지만 Discord 완료 알림 전송에 실패했습니다.")
    return {
        "ok": True,
        "account": config.account,
        "verified": ["auth", "gmail", "calendar"],
        "discord_delivery": delivery,
    }
