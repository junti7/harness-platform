from scripts.summarize_kimi_shadow_eval import summarize


def test_summarize_kimi_shadow_eval_groups_sources(monkeypatch):
    monkeypatch.setenv("KIMI_COST_INPUT_PER_MTOK_USD", "3")
    monkeypatch.setenv("KIMI_COST_OUTPUT_PER_MTOK_USD", "15")

    result = summarize(
        [
            {
                "source": "openclaw_ollama_chat",
                "ok": True,
                "json_valid": True,
                "latency_ms": 100,
                "prompt_token_count": 1000,
                "candidates_token_count": 100,
            },
            {
                "source": "openclaw_ollama_chat",
                "ok": False,
                "latency_ms": 200,
                "error_type": "HTTPStatusError",
            },
        ]
    )

    assert result["total"] == 2
    assert result["ok_rate"] == 0.5
    assert result["estimated_cost_usd"] == 0.0045
    assert result["by_source"]["openclaw_ollama_chat"]["total"] == 2
    assert result["errors"] == {"HTTPStatusError": 1}
