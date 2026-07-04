from scripts import run_edu_tier3_parallel as tier3


def test_parallel_candidate_fetch_uses_text_gate_by_default(monkeypatch):
    captured = {}

    def fake_execute_query(query, params, fetch=False):
        captured["query"] = query
        captured["params"] = params
        captured["fetch"] = fetch
        return []

    monkeypatch.setattr(tier3, "execute_query", fake_execute_query)

    tier3._fetch_candidates(0.1, 0, 1, 10)

    assert "ILIKE ANY" in captured["query"]
    assert captured["params"] == (0.1, 1, 0, tier3.EDU_TIER3_TEXT_GATE_PATTERNS)
    assert captured["fetch"] is True


def test_parallel_candidate_fetch_can_disable_text_gate(monkeypatch):
    captured = {}

    def fake_execute_query(query, params, fetch=False):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(tier3, "execute_query", fake_execute_query)

    tier3._fetch_candidates(0.1, 0, 1, 10, text_gate=False)

    assert "ILIKE ANY" not in captured["query"]
    assert captured["params"] == (0.1, 1, 0)
