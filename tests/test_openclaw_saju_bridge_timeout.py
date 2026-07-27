from types import SimpleNamespace

from scripts import openclaw_codex_bridge as bridge


def _cache_key():
    return bridge._saju_cache_key(
        SimpleNamespace(
            original_question="오늘 운세",
            grounded_question="오늘 운세",
            requirements=(),
            supplemental_facts=(),
        ),
        {
            "source_count": 1,
            "source_revision": "revision",
        },
    )


def test_saju_cache_lock_wait_zero_degrades_when_contended(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "NOTEBOOKLM_CACHE_DIR", tmp_path)
    first_fd, first_status = bridge._acquire_notebooklm_cache_lock(_cache_key())
    try:
        assert first_status == "ready"
        second_fd, second_status = bridge._acquire_notebooklm_cache_lock(
            _cache_key(), wait_s=0
        )
        assert second_fd is None
        assert second_status == "degraded_lock_timeout"
    finally:
        bridge._release_notebooklm_cache_lock(first_fd)


def test_saju_cache_lock_closes_fd_on_flock_oserror(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "NOTEBOOKLM_CACHE_DIR", tmp_path)

    opened_fd = None
    real_open = bridge.os.open
    real_close = bridge.os.close
    closed_fds = []

    def tracking_open(*args, **kwargs):
        nonlocal opened_fd
        opened_fd = real_open(*args, **kwargs)
        return opened_fd

    def tracking_close(fd):
        closed_fds.append(fd)
        return real_close(fd)

    def broken_flock(*_args, **_kwargs):
        raise OSError("synthetic flock failure")

    monkeypatch.setattr(bridge.os, "open", tracking_open)
    monkeypatch.setattr(bridge.os, "close", tracking_close)
    monkeypatch.setattr(bridge.fcntl, "flock", broken_flock)

    fd, status = bridge._acquire_notebooklm_cache_lock(_cache_key(), wait_s=0)

    assert fd is None
    assert status == "degraded_cache_io"
    assert opened_fd in closed_fds


def test_saju_query_budget_exhaustion_releases_cache_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "NOTEBOOKLM_CACHE_DIR", tmp_path)
    monkeypatch.setattr(bridge, "_safe_append_notebooklm_audit", lambda _payload: None)
    monkeypatch.setattr(bridge, "_prune_expired_notebooklm_cache", lambda: True)
    query_called = False

    def fail_if_query_runs(*_args, **_kwargs):
        nonlocal query_called
        query_called = True
        raise AssertionError("query should not run after budget exhaustion")

    monkeypatch.setattr(bridge, "_run_nlm_private_query", fail_if_query_runs)
    monkeypatch.setattr(
        bridge,
        "build_query_plan",
        lambda _question, _enrichers: SimpleNamespace(
            original_question="오늘 운세",
            grounded_question="오늘 운세",
            requirements=(),
            supplemental_facts=(),
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_verified_saju_notebook",
        lambda: {
            "binary": "/tmp/nlm",
            "notebook": {
                "id": bridge.SAJU_NOTEBOOK_ID,
                "title": bridge.SAJU_NOTEBOOK_TITLE,
                "source_count": 1,
                "source_revision": "revision",
                "source_revision_status": "verified",
            },
        },
    )

    payload = bridge.query_saju_notebook("오늘 운세", timeout_s=10)

    assert payload["ok"] is False
    assert payload["error"] == "RuntimeError"
    assert query_called is False
    fd, status = bridge._acquire_notebooklm_cache_lock(
        _cache_key(),
        wait_s=0,
    )
    try:
        assert status == "ready"
    finally:
        bridge._release_notebooklm_cache_lock(fd)
