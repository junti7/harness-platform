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
    assert any("never invent an absolute path" in item.lower() for item in result["answerContract"])
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
    from scripts.harness_knowledge_index import (
        _contains_marker,
        _domain_strength,
        _selected_domains,
    )

    assert _selected_domains("교육 사업과 스마트팜") == [
        "education-training",
        "smartfarm",
    ]
    assert _selected_domains("자료 수입 사업") == ["materials-import"]
    assert _contains_marker("schedule", "edu") is False
    assert _contains_marker("trading", "trade") is False
    assert _contains_marker("docs/education/plan.md", "education") is True
    canonical = {
        "path": "docs/education/MASTER_PLAN.md",
        "title": "Master Plan",
        "headings": [],
    }
    unrelated = {
        "path": "docs/reports/red_team.md",
        "title": "교육 Red Team",
        "headings": [],
    }
    assert _domain_strength(canonical, "education-training") > _domain_strength(
        unrelated, "education-training"
    )


def test_model_typo_is_normalized_and_connection_evidence_is_ranked(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    soil_node = repo / "hardware" / "smartfarm" / "soil_node"
    soil_node.mkdir()
    (soil_node / "config.example.esp8266.h").write_text(
        "\n".join(
            [
                "// ESP8266 node configuration",
                "#define SOIL_MOISTURE_PIN A0",
                "#define DHT_PIN 4",
                "#define PUMP_RELAY_PIN 5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "hardware" / "smartfarm" / "README.md").write_text(
        "\n".join(
            [
                "# Smartfarm",
                "ESP8266 physical wiring uses soil A0, DHT22 GPIO4, and relay GPIO5.",
                "The node connects over WiFi and publishes sensor values through MQTT.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "esp8266 fixture"], cwd=repo, check=True)

    payload, metrics = refresh_index(repo, tmp_path / "cache.json")
    result = query_index(
        repo,
        payload,
        metrics,
        "ESP8255에 연결된 것들 알려줘.",
        max_files=5,
        max_excerpts=5,
    )

    assert result["matchedDomains"] == ["smartfarm"]
    assert result["queryNormalization"]["corrections"] == [
        {
            "input": "esp8255",
            "normalized": "esp8266",
            "reason": "nearby repository model identifier",
        }
    ]
    assert result["files"][0]["path"] == (
        "hardware/smartfarm/soil_node/config.example.esp8266.h"
    )
    excerpt = next(
        item["excerpt"]
        for item in result["evidence"]
        if item["path"] == "hardware/smartfarm/soil_node/config.example.esp8266.h"
    )
    assert "SOIL_MOISTURE_PIN A0" in excerpt
    assert "DHT_PIN 4" in excerpt
    assert "PUMP_RELAY_PIN 5" in excerpt
    readme_excerpt = next(
        item["excerpt"]
        for item in result["evidence"]
        if item["path"] == "hardware/smartfarm/README.md"
    )
    assert "WiFi" in readme_excerpt
    assert "MQTT" in readme_excerpt
    assert any(
        "instead of stopping at the typo" in item
        for item in result["answerContract"]
    )


def test_model_normalization_is_fail_safe_for_exact_repeated_and_ambiguous_tokens() -> None:
    from scripts.harness_knowledge_index import _normalize_question

    payload = {
        "files": {
            "esp8266": {
                "path": "hardware/smartfarm/esp8266.md",
                "title": "ESP8266",
                "headings": [],
            },
            "esp8244": {
                "path": "hardware/smartfarm/esp8244.md",
                "title": "ESP8244",
                "headings": [],
            },
        }
    }

    exact, exact_corrections = _normalize_question("ESP8266 연결", payload)
    assert exact == "ESP8266 연결"
    assert exact_corrections == []

    ambiguous, ambiguous_corrections = _normalize_question("ESP8255 연결", payload)
    assert ambiguous == "ESP8255 연결"
    assert ambiguous_corrections == []

    repeated_payload = {
        "files": {
            "esp8266": {
                "path": "hardware/smartfarm/esp8266.md",
                "title": "ESP8266",
                "headings": [],
            }
        }
    }
    repeated, repeated_corrections = _normalize_question(
        "ESP8255와 esp8255 연결", repeated_payload
    )
    assert repeated == "ESP8255와 esp8255 연결 esp8266"
    assert len(repeated_corrections) == 1

    plain, plain_corrections = _normalize_question("스마트팜 연결 현황", payload)
    assert plain == "스마트팜 연결 현황"
    assert plain_corrections == []

    unrelated, unrelated_corrections = _normalize_question(
        "release ESP8255 티켓 상태", repeated_payload
    )
    assert unrelated == "release ESP8255 티켓 상태"
    assert unrelated_corrections == []

    non_model_payload = {
        "files": {
            "gpio8266": {
                "path": "hardware/smartfarm/gpio8266.md",
                "title": "GPIO8266",
                "headings": [],
            }
        }
    }
    non_model, non_model_corrections = _normalize_question(
        "GPIO8255 핀 연결", non_model_payload
    )
    assert non_model == "GPIO8255 핀 연결"
    assert non_model_corrections == []
