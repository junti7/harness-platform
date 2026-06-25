from datetime import datetime, timezone

from core.edu_curriculum import personalize


def _row(**overrides):
    base = {
        "klass": "perishable",
        "buckets": ["활용-학습/숙제"],
        "model_tags": ["chatgpt"],
        "item_created_at": datetime(2026, 6, 25, tzinfo=timezone.utc),
        "segment": "parent",
        "title": "ChatGPT로 숙제하는 우리 아이, 말려야 할까요?",
        "collect_query": "중학생 챗GPT 사용",
        "refined_id": 1,
        "source": "Naver_블로그",
        "raw_title": "생성형 AI 강사 챗GPT 강사 피지컬 AI 강사 소현규 교육 후기",
        "raw_description": "인천광역시교육청서구도서관 학교도서관 AI 실무교육 후기",
        "raw_body": "",
        "url": "https://blog.naver.com/sbk8004/224312216722",
        "body": "ChatGPT로 숙제하는 아이를 어떻게 지도할지 요약합니다.",
    }
    base.update(overrides)
    return base


def test_personalize_filters_article_when_source_context_mismatches_query():
    res = personalize(
        [_row()],
        llm="chatgpt",
        level="beginner",
        motivation="child_study",
        env="pc",
        job="parent",
        now=datetime(2026, 6, 25, tzinfo=timezone.utc),
    )

    assert res["highlights"] == []


def test_personalize_keeps_child_study_article_and_uses_source_title():
    row = _row(
        refined_id=2,
        collect_query="고등학생 AI 공부",
        raw_title="경기광주 중3·고등학생 여름방학 특강 AI 시대 질문하는 공부법",
        raw_description="고등학생과 중학생이 AI를 공부와 학습에 활용하는 수업 안내",
        url="https://blog.naver.com/example/1",
    )
    res = personalize(
        [row],
        llm="chatgpt",
        level="beginner",
        motivation="child_study",
        env="pc",
        job="parent",
        now=datetime(2026, 6, 25, tzinfo=timezone.utc),
    )

    assert len(res["highlights"]) == 1
    assert res["highlights"][0]["title"] == row["raw_title"]
    assert res["highlights"][0]["generated_title"] == row["title"]
    assert res["highlights"][0]["relevance_score"] >= 0.65
