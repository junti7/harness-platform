from scripts import retry_dlq


class _Logger:
    def info(self, _message):
        pass

    def warning(self, _message):
        pass


def test_retry_normalizes_legacy_string_score(monkeypatch):
    seen = {}

    def fake_refine(_client, row):
        seen["score"] = row["score"]
        return {"final_title": "ok", "tags": []}

    monkeypatch.setattr(retry_dlq, "refine_signal", fake_refine)
    monkeypatch.setattr(retry_dlq, "get_today_cost", lambda _logger: 0.0)
    monkeypatch.setattr(retry_dlq, "check_and_alert", lambda *_args: None)

    ok = retry_dlq.retry_tier3_signal(
        {"id": 1, "raw_data": {"id": 7, "score": "0.42"}},
        object(),
        True,
        _Logger(),
    )

    assert ok is True
    assert seen["score"] == 0.42
