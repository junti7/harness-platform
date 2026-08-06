from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.gmail_mobile_oauth import MobileOAuthConfig, MobileOAuthError, exchange, start


def _config(tmp_path: Path) -> MobileOAuthConfig:
    return MobileOAuthConfig(
        enabled=True,
        account="ceo@example.com",
        client="mobile",
        redirect_uri="https://macmini.example.ts.net/api/gmail/oauth/mobile/callback",
        gog_bin="gog",
        keyring_backend="file",
        keyring_password="secret",
        state_path=tmp_path / "state.json",
        discord_target="1234",
        ttl_seconds=300,
    )


class Runner:
    def __init__(self, results: list[tuple[int, str, str]]):
        self.results = list(results)
        self.calls: list[list[str]] = []

    def __call__(self, args, **_kwargs):
        self.calls.append(args)
        code, stdout, stderr = self.results.pop(0)
        return subprocess.CompletedProcess(args, code, stdout, stderr)


def test_start_persists_only_state_hash(tmp_path: Path):
    config = _config(tmp_path)
    url = "https://accounts.google.com/o/oauth2/auth?client_id=x&state=raw-state"
    result = start(config, runner=Runner([(0, f"Open this URL:\n{url}\n", "")]), now=100)
    saved = config.state_path.read_text()

    assert result["auth_url"] == url
    assert result["expires_at"] == 400
    assert "raw-state" not in saved


def test_exchange_is_one_use_and_verifies_services(tmp_path: Path):
    config = _config(tmp_path)
    url = "https://accounts.google.com/o/oauth2/auth?state=raw-state"
    start(config, runner=Runner([(0, url, "")]), now=100)
    callback = f"{config.redirect_uri}?state=raw-state&code=sensitive-code"
    runner = Runner([(0, "ok", ""), (0, "{}", ""), (0, "[]", ""), (0, "[]", ""), (0, '{"messageId":"m1"}', "")])

    result = exchange(config, callback, runner=runner, now=101)

    assert result["verified"] == ["auth", "gmail", "calendar"]
    assert result["discord_delivery"]["message_id"] == "m1"
    assert not config.state_path.exists()
    with pytest.raises(MobileOAuthError, match="이미 사용"):
        exchange(config, callback, runner=Runner([]), now=102)


def test_exchange_rejects_expired_and_wrong_state(tmp_path: Path):
    config = _config(tmp_path)
    start(config, runner=Runner([(0, "https://accounts.google.com/o/oauth2/auth?state=right", "")]), now=100)
    with pytest.raises(MobileOAuthError, match="일치하지"):
        exchange(config, f"{config.redirect_uri}?state=wrong&code=x", runner=Runner([]), now=101)
    with pytest.raises(MobileOAuthError, match="만료"):
        exchange(config, f"{config.redirect_uri}?state=right&code=x", runner=Runner([]), now=401)


def test_disabled_fails_closed(tmp_path: Path):
    config = MobileOAuthConfig(**{**_config(tmp_path).__dict__, "enabled": False})
    with pytest.raises(MobileOAuthError, match="비활성"):
        start(config, runner=Runner([]))


def test_discord_delivery_retries_then_fails_explicitly(tmp_path: Path):
    config = _config(tmp_path)
    start(config, runner=Runner([(0, "https://accounts.google.com/o/oauth2/auth?state=right", "")]), now=100)
    callback = f"{config.redirect_uri}?state=right&code=code"
    results = [(0, "", ""), (0, "{}", ""), (0, "[]", ""), (0, "[]", "")] + [(1, "", "failed")] * 3
    with pytest.raises(MobileOAuthError, match="Discord 완료 알림"):
        exchange(config, callback, runner=Runner(results), now=101)
