from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.harness_knowledge_index import query_index, refresh_index


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "docs" / "trading").mkdir(parents=True)
    (repo / "hardware" / "smartfarm").mkdir(parents=True)
    (repo / "docs" / "trading" / "TURTLE.md").write_text(
        "# Turtle Trading\nPaper only. turtle_gate_clear required.\n", encoding="utf-8"
    )
    (repo / "hardware" / "smartfarm" / "README.md").write_text(
        "# Smartfarm\nDHT22 sensor pilot.\n", encoding="utf-8"
    )
    (repo / ".env").write_text("SECRET=do-not-index\n", encoding="utf-8")
    (repo / "config.json").write_text(
        '{"api_key":"sk-secret-value-1234567890","label":"public"}\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    return repo


def test_incremental_index_and_domain_query(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    cache = tmp_path / "cache" / "index.json"
    payload, first = refresh_index(repo, cache)
    assert first["filesUpdated"] == 3
    assert ".env" not in payload["files"]
    assert "sk-secret-value" not in payload["files"]["config.json"]["searchText"]
    assert "<redacted>" in payload["files"]["config.json"]["searchText"]
    result = query_index(
        repo, payload, first, "현재 Turtle Trading 진행 상태",
        max_files=5, max_excerpts=3,
    )
    assert result["matchedDomains"] == ["turtle-trading"]
    assert result["files"][0]["path"] == "docs/trading/TURTLE.md"
    assert result["recommendedLiveTools"] == ["harness_alpaca_status"]
    assert "turtle_gate_clear" in result["evidence"][0]["excerpt"]
    assert result["readyToAnswer"] is True
    assert result["domainEvidence"]["turtle-trading"][0]["path"] == "docs/trading/TURTLE.md"
    _, second = refresh_index(repo, cache)
    assert second["cacheHit"] is True
    assert second["filesUpdated"] == 0
    assert second["filesReused"] == 3


def test_changed_file_only_is_reindexed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    cache = tmp_path / "index.json"
    refresh_index(repo, cache)
    smartfarm = repo / "hardware" / "smartfarm" / "README.md"
    smartfarm.write_text("# Smartfarm\nESP32 moisture sensor.\n", encoding="utf-8")
    payload, metrics = refresh_index(repo, cache)
    assert metrics["filesUpdated"] == 1
    assert metrics["filesReused"] == 2
    assert "ESP32" in payload["files"]["hardware/smartfarm/README.md"]["searchText"]


def test_cli_returns_compact_json(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    cache = tmp_path / "index.json"
    result = subprocess.run(
        [
            "python3", "scripts/harness_knowledge_index.py", "--repo", str(repo),
            "--cache", str(cache), "--question", "스마트팜 현황",
        ],
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["matchedDomains"] == ["smartfarm"]
    assert payload["files"][0]["path"] == "hardware/smartfarm/README.md"


def test_multi_domain_query_preserves_each_domain() -> None:
    from scripts.harness_knowledge_index import _selected_domains

    assert _selected_domains("교육 사업과 스마트팜") == [
        "education-training",
        "smartfarm",
    ]
    assert _selected_domains("자료 수입 사업") == ["materials-import"]
