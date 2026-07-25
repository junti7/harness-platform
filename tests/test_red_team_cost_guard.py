import json

import pytest

from adapters.content import red_team


def test_default_provider_pair_uses_antigravity_not_copilot(monkeypatch):
    monkeypatch.delenv("HARNESS_RED_TEAM_PROVIDERS", raising=False)
    monkeypatch.setattr(red_team, "_provider_available", lambda provider: provider in {"codex", "antigravity"})

    assert red_team._selected_providers() == ("codex", "antigravity")


def test_installed_antigravity_uses_agy_binary(monkeypatch):
    monkeypatch.setattr(red_team.shutil, "which", lambda binary: "/usr/local/bin/agy" if binary.endswith("agy") else None)
    assert red_team._provider_available("antigravity") is True


def test_nonzero_cost_provider_pair_is_rejected(monkeypatch):
    monkeypatch.setenv("HARNESS_RED_TEAM_PROVIDERS", "claude,codex")
    with pytest.raises(ValueError, match="exactly"):
        red_team._selected_providers()


def test_ceo_order_and_zero_paid_budget_are_required(monkeypatch):
    monkeypatch.setenv("RED_TEAM_PAID_BUDGET_USD", "0")
    monkeypatch.setenv("HARNESS_RED_TEAM_PROVIDERS", "codex,antigravity")
    monkeypatch.setattr(red_team, "_verify_antigravity_access", lambda: None)
    with pytest.raises(ValueError, match="ceo-order-id"):
        red_team._require_ceo_order("")

    red_team._require_ceo_order("CEO-20260725-redteam-cost")

    monkeypatch.setenv("RED_TEAM_PAID_BUDGET_USD", "0.01")
    with pytest.raises(ValueError, match=r"\$0"):
        red_team._require_ceo_order("CEO-20260725-redteam-cost")


def test_antigravity_model_access_must_be_live(monkeypatch):
    class Result:
        returncode = 0
        stdout = "gemini-3.1-pro-high\n"

    monkeypatch.setattr(red_team.subprocess, "run", lambda *args, **kwargs: Result())
    with pytest.raises(RuntimeError, match="not currently verified"):
        red_team._verify_antigravity_access()


def test_artifact_hash_cache_reuses_same_provider_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(red_team, "RED_TEAM_CACHE_DIR", tmp_path)
    artifact = {"title": "x", "artifact_path": "docs/x.md", "content": "same"}
    result = {"decision": "red_team_clear"}

    red_team._write_cached_result(artifact, ("codex", "antigravity"), result)

    assert red_team._read_cached_result(artifact, ("codex", "antigravity")) == result
    assert red_team._read_cached_result(artifact, ("codex", "claude")) is None
    cache_payload = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert cache_payload["decision"] == "red_team_clear"


def test_corrupt_cache_fails_closed_without_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(red_team, "RED_TEAM_CACHE_DIR", tmp_path)
    artifact = {"id": 1, "title": "x", "artifact_path": "docs/x.md", "content": "same"}
    path = red_team._cache_path(artifact, ("codex", "antigravity"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unbudgeted retry"):
        red_team._read_cached_result(artifact, ("codex", "antigravity"))


def test_weekly_red_team_is_retired():
    with pytest.raises(RuntimeError, match="retired"):
        red_team.run_weekly_red_team("research_report", 1)


def test_antigravity_command_is_read_only_and_low_effort(monkeypatch):
    monkeypatch.setenv("HARNESS_ANTIGRAVITY_RED_TEAM_MODEL", "gemini-3.6-flash-low")
    command = red_team.PROVIDERS["antigravity"]("review")

    assert command[0].endswith("agy")
    assert command[command.index("--mode") + 1] == "plan"
    assert "--sandbox" in command
    assert command[command.index("--effort") + 1] == "low"
    assert command[command.index("--model") + 1] == "gemini-3.6-flash-low"
