from scripts import collect_naver_community as naver


def test_collection_stops_at_segment_capacity(monkeypatch):
    monkeypatch.setattr(naver, "MAX_ITEMS_PER_SEGMENT", 3)
    monkeypatch.setattr(naver, "PAGES", 1)
    monkeypatch.setattr(naver, "TARGETS", [("blog", "블로그")])
    monkeypatch.setattr(naver, "QUERIES", {"parent": ["q"]})
    monkeypatch.setattr(naver.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        naver,
        "_search",
        lambda *_args, **_kwargs: [
            {"title": f"item-{i}", "link": f"https://example.com/{i}"}
            for i in range(10)
        ],
    )

    rows = naver.collect("parent")

    assert len(rows) == 3
