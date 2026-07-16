from scripts import run_paper_trading_health_report as health


def test_collect_alpaca_blocks_entry_orders_and_post_lock_positions(monkeypatch):
    monkeypatch.setattr(health, "get_account_summary", lambda: {"ok": True})
    monkeypatch.setattr(health, "get_positions", lambda: [
        {"symbol": "ASX", "qty": 10},
        {"symbol": "META", "qty": 3},
    ])
    monkeypatch.setattr(health, "_trading_get", lambda *_: [
        {"id": "late", "symbol": "DBC", "side": "buy", "type": "market", "qty": "2", "status": "accepted"},
        {"id": "asx-stop", "symbol": "ASX", "side": "sell", "type": "stop", "qty": "10", "status": "new"},
        {"id": "meta-stop", "symbol": "META", "side": "sell", "type": "stop", "qty": "3", "status": "new"},
    ])
    monkeypatch.setattr(health, "load_json", lambda _: {"turtle_positions": {"ASX": {}, "META": {}}})
    monkeypatch.setattr(health, "get_ar018_kpi", lambda *_: {})

    result = health.collect_alpaca()

    assert result["ok"] is False
    assert [order["symbol"] for order in result["active_entry_orders"]] == ["DBC"]
    assert result["unexpected_positions_during_entry_lock"] == ["META"]
