from adapters.content import refiner


def test_fetch_batch_excludes_signals_already_owned_by_dlq(monkeypatch):
    queries = []

    def fake_execute_query(query, params=None, fetch=False):
        queries.append(query)
        return []

    monkeypatch.setattr(refiner, "execute_query", fake_execute_query)
    refiner._fetch_refine_batch(10)

    assert len(queries) == 2
    assert all("NOT EXISTS" in query for query in queries)
    assert all("dead_letter_queue" in query for query in queries)
    assert all("dlq.item_id = fs.id" in query for query in queries)


def test_dlq_retry_worker_owns_unresolved_signals():
    from scripts import retry_dlq

    assert retry_dlq.MAX_RETRIES == 3
    assert callable(retry_dlq.get_retryable_entries)


def test_irrelevant_result_is_saved_as_terminal(monkeypatch):
    row = {
        "id": 42,
        "title": "out of scope",
        "summary": "",
        "content_hash": "x",
        "source": "test",
        "score": 0.7,
        "extracted_facts": [],
        "domain": "physical_ai",
    }
    saved = []
    monkeypatch.setattr(refiner, "_fetch_refine_batch", lambda _limit: [row])
    monkeypatch.setattr(refiner, "get_today_cost", lambda _logger=None: 0.0)
    monkeypatch.setattr(refiner, "check_and_alert", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        refiner,
        "refine_signal",
        lambda _model, _row: {
            "final_title": "irrelevant",
            "is_relevant": False,
            "tags": ["irrelevant"],
        },
    )
    monkeypatch.setattr(
        refiner,
        "save_refined_output",
        lambda filtered_id, result, model: saved.append((filtered_id, result, model)) or 99,
    )

    assert refiner.refine(correlation_id="test-terminal") == 0
    assert saved == [(42, {"final_title": "irrelevant", "is_relevant": False, "tags": ["irrelevant"]}, f"{refiner.DEFAULT_GEMINI_MODEL}:irrelevant")]
