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
    assert "AND NOT" in captured["query"]
    assert captured["params"] == (
        0.1,
        1,
        0,
        tier3.EDU_TIER3_SOURCE_ALLOWLIST,
        tier3.EDU_TIER3_TEXT_GATE_PATTERNS,
        tier3.EDU_TIER3_AUDIENCE_PATTERNS,
        tier3.EDU_TIER3_TEXT_DENY_PATTERNS,
    )
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


def test_rule_skip_fetch_excludes_high_precision_keep_gate(monkeypatch):
    captured = {}

    def fake_execute_query(query, params, fetch=False):
        captured["query"] = query
        captured["params"] = params
        captured["fetch"] = fetch
        return []

    monkeypatch.setattr(tier3, "execute_query", fake_execute_query)

    tier3._fetch_rule_skip_candidates(0.1, 0, 1, 50)

    assert "edu-triage" not in captured["query"]
    assert "AND NOT (" in captured["query"]
    assert "fs.source = ANY(%s)" in captured["query"]
    assert "outside-curated-source-allowlist" in captured["query"]
    assert "missing-required-topic-or-audience-signal" in captured["query"]
    # Keep gate 바깥 모든 row가 terminal triage 대상이어야 한다. 별도 pre-filter를 두면
    # allowlist 안이지만 topic/audience marker가 없는 row가 영구 backlog로 남는다.
    assert "OR NOT (fs.source = ANY(%s))" not in captured["query"]
    assert captured["params"] == (
        tier3.EDU_TIER3_TRIAGE_SKIP_SOURCES,
        tier3.EDU_TIER3_SOURCE_ALLOWLIST,
        tier3.EDU_TIER3_TRIAGE_SKIP_PATTERNS,
        0.1,
        1,
        0,
        tier3.EDU_TIER3_SOURCE_ALLOWLIST,
        tier3.EDU_TIER3_TEXT_GATE_PATTERNS,
        tier3.EDU_TIER3_AUDIENCE_PATTERNS,
        tier3.EDU_TIER3_TEXT_DENY_PATTERNS,
        50,
    )
    assert captured["fetch"] is True


def test_rule_skipped_output_is_recorded_as_irrelevant():
    row = {
        "title": "취준생 AI 자기소개서 작성",
        "summary": "취업 준비 기사",
        "source": "GoogleNews_취준생AI",
    }

    result = tier3._rule_skipped_output(row, "source-skip")

    assert result["is_relevant"] is False
    assert result["final_title"] == row["title"]
    assert "tier3-triage-skip" in result["tags"]
    assert result["triage_reason"] == "source-skip"
