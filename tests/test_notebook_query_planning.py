from core.notebook_query_planning import (
    SupplementalFacts,
    assess_notebook_answer,
    build_query_plan,
    infer_requirements,
)
from datetime import date

from core.saju_calendar import enrich_saju_question, normalize_relative_saju_dates
import pytest


def test_planner_supports_domain_independent_enricher():
    def price_enricher(question: str):
        return SupplementalFacts("price-api", ("ABC current price: 10",))

    plan = build_query_plan("ABC 현재 가격과 근거", (price_enricher,))
    assert "[price-api] ABC current price: 10" in plan.grounded_question
    assert plan.requirements == ("근거",)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("오늘 좋은 시간대와 피할 시간대", ("좋은 시간대", "피할 시간대")),
        ("오늘 길한 시각과 피해야 할 시각", ("좋은 시간대", "피할 시간대")),
        ("유리한 때와 조심할 때", ("좋은 시간대", "피할 시간대")),
        ("최적의 몇 시와 위험한 몇 시", ("좋은 시간대", "피할 시간대")),
        ("오늘 좋은 시간만", ("좋은 시간대",)),
        ("오늘 흉한 시간만", ("피할 시간대",)),
        ("좋은 결과가 났을 때 주의할 점", ("주의사항",)),
        ("오늘 몇 시가 안 좋을까요?", ("피할 시간대",)),
        ("오늘 좋은 운과 피할 시간대는?", ("피할 시간대",)),
        ("오늘 길운과 피할 시간대는?", ("피할 시간대",)),
        ("좋은 시간은 아닌 때를 알려줘", ("피할 시간대",)),
        ("유리한 시각은 아니다", ("피할 시간대",)),
    ],
)
def test_time_window_requirements_use_composed_semantics(question, expected):
    assert infer_requirements(question) == expected


def test_delivery_contract_rejects_non_answer_even_when_tool_succeeded():
    plan = build_query_plan("전체운과 근거를 알려줘")
    passed, reasons = assess_notebook_answer(
        plan, "정보가 부족하여 확인할 수 없습니다."
    )
    assert not passed
    assert "non_answer_or_refusal" in reasons


def test_delivery_contract_rejects_requirement_echo_refusal():
    plan = build_query_plan("전체운, 재물운, 건강운, 대인운, 주의사항과 근거")
    passed, reasons = assess_notebook_answer(
        plan,
        "전체운, 재물운, 건강운, 대인운, 주의사항에 대한 근거 자료가 없어 답변 불가합니다.",
    )
    assert not passed
    assert "non_answer_or_refusal" in reasons


@pytest.mark.parametrize(
    "answer",
    [
        "요청하신 전체운, 재물운, 건강운, 대인운, 주의사항 항목은 업로드된 출처에 나와 있지 않습니다.",
        "전체운과 재물운의 근거를 제시할 수 없습니다.",
    ],
)
def test_delivery_contract_rejects_semantic_refusal_variants(answer):
    plan = build_query_plan("전체운, 재물운, 건강운, 대인운, 주의사항과 근거")
    passed, reasons = assess_notebook_answer(plan, answer)
    assert not passed
    assert "semantic_non_answer" in reasons


def test_delivery_contract_accepts_complete_answer_with_limitations():
    plan = build_query_plan("전체운, 재물운, 건강운, 대인운, 주의사항과 근거")
    answer = (
        "전체운: 갑기합으로 현실적 판단이 강조됩니다 [1]. "
        "재물운: 정재 작용을 근거로 계약 검토가 중요합니다 [2]. "
        "건강운: 전통 오행 해석상 휴식을 권합니다 [3]. "
        "대인운: 형의 작용을 근거로 언행을 신중히 합니다 [4]. "
        "주의사항: 중요한 결정은 재확인합니다 [5]. "
        "이 해석은 노트북의 십신과 합충형 이론을 적용한 전통적 해석입니다. "
        "개인의 실제 사건을 과학적으로 예측하는 근거는 없으므로 단정하기 어렵고, "
        "근거가 닿지 않는 부분은 추정으로 제한합니다. "
        "각 항목은 보강 계산값과 노트북 인용을 분리해 작성했으며 의료·재무 판단에 사용하지 않습니다."
    )
    passed, reasons = assess_notebook_answer(plan, answer)
    assert passed, reasons


def test_delivery_contract_accepts_semantic_time_window_headings():
    plan = build_query_plan("길한 시각과 피해야 할 시각")
    answer = "길한 시각은 경오시입니다. 피해야 할 시각은 신미시입니다."
    passed, reasons = assess_notebook_answer(plan, answer)
    assert passed, reasons


def test_delivery_contract_accepts_caution_time_heading():
    plan = build_query_plan("피할 시간대")
    passed, reasons = assess_notebook_answer(plan, "주의 시간은 14시입니다.")
    assert passed, reasons


@pytest.mark.parametrize(
    "answer",
    ["좋은 시간 보내세요. 피해야 할 시간은 참고하세요.", "길시와 주의 시간만 참고하세요."],
)
def test_delivery_contract_rejects_time_labels_without_concrete_window(answer):
    plan = build_query_plan("길한 시각과 피해야 할 시각")
    passed, reasons = assess_notebook_answer(plan, answer)
    assert not passed
    assert "missing:좋은 시간대" in reasons
    assert "missing:피할 시간대" in reasons


def test_delivery_contract_requires_concrete_time_for_each_label():
    plan = build_query_plan("좋은 시간대와 피할 시간대")
    passed, reasons = assess_notebook_answer(
        plan, "좋은 시간대는 경오시입니다. 피할 시간대는 주의하세요."
    )
    assert not passed
    assert "missing:피할 시간대" in reasons


def test_saju_enricher_fails_closed_for_lunar_input():
    with pytest.raises(ValueError, match="음력"):
        enrich_saju_question("음력 1974년 2월 2일 남자 2026년 7월 24일 운세")


def test_saju_enricher_does_not_accept_fake_lunar_conversion_phrase():
    with pytest.raises(ValueError, match="음력"):
        enrich_saju_question(
            "음력 1974년 2월 2일 양력 변환 남자 2026년 7월 24일 운세"
        )


@pytest.mark.parametrize(
    "marker",
    ["陰曆", "陰历", "阴曆", "阴历", "農曆", "农历", "lunar", "음 력", "구력", "윤달", "윤5월"],
)
def test_saju_enricher_rejects_all_supported_lunar_markers_before_date_count(marker):
    with pytest.raises(ValueError, match="음력"):
        enrich_saju_question(f"{marker} 1990년 5월 3일생 남자 사주 전체운")


def test_saju_enricher_fails_closed_for_ambiguous_rat_hour():
    with pytest.raises(ValueError, match="자시"):
        enrich_saju_question("양력 1974년 2월 2일 자시생 남자 2026년 7월 24일 운세")


@pytest.mark.parametrize(
    "question",
    [
        "양력 1974-02-02 유시생 남성의 2026-07-24 사주 운세",
        "양력 1974/02/02 유시생 남성의 2026/07/24 사주 운세",
        "양력 1974.02.02 유시생 남성의 2026.07.24 사주 운세",
    ],
)
def test_saju_enricher_accepts_machine_friendly_solar_dates(question):
    result = enrich_saju_question(question)
    assert result is not None
    assert result.facts[0].startswith("출생 양력 1974-02-02")
    assert result.facts[1].startswith("대상일 양력 2026-07-24")


def test_saju_enricher_fails_closed_for_23_hour_day_boundary():
    with pytest.raises(ValueError, match="23시"):
        enrich_saju_question("양력 1974년 2월 2일 자시 23시생 남자 2026년 7월 24일 운세")


def test_saju_enricher_fails_closed_for_adjacent_23_hour_token():
    with pytest.raises(ValueError, match="23시"):
        enrich_saju_question("양력 1974년 2월 2일 자시23시생 남자 2026년 7월 24일 운세")


@pytest.mark.parametrize("marker", ["오후", "PM", "p.m."])
def test_saju_enricher_rejects_twelve_hour_clock(marker):
    with pytest.raises(ValueError, match="24시간제"):
        enrich_saju_question(
            f"양력 1974년 2월 2일 {marker} 3시생 남자 2026년 7월 24일 운세"
        )


def test_saju_enricher_does_not_treat_duration_as_birth_hour():
    result = enrich_saju_question(
        "양력 1974년 2월 2일생 남자, 2026년 7월 24일 일진 3시간 뒤 상황"
    )
    assert result is not None
    assert len(result.facts[0].split()) < 10
    assert any("출생 시각이 없어" in warning for warning in result.warnings)


def test_saju_enricher_does_not_use_target_day_branch_as_birth_hour():
    result = enrich_saju_question(
        "양력 1974년 2월 2일생 남자 2026년 7월 24일 오시 일진 알려줘"
    )
    assert result is not None
    assert any("출생 시각이 없어" in warning for warning in result.warnings)


def test_saju_enricher_target_20_hour_cannot_disambiguate_birth_rat_hour():
    with pytest.raises(ValueError, match="자시"):
        enrich_saju_question(
            "양력 1974년 2월 2일 자시생 남자 2026년 7월 24일 20시 기준 운세"
        )


def test_saju_enricher_single_date_computational_question_fails_closed():
    with pytest.raises(ValueError, match="두 날짜"):
        enrich_saju_question("1974년 2월 2일생 남자 오늘 전체운과 재물운 알려줘")


def test_saju_enricher_target_first_later_appointment_is_not_birth_hour():
    result = enrich_saju_question(
        "2026년 7월 24일 일진을 1974년 2월 2일생 남자 기준으로 알려줘, 오시에 약속"
    )
    assert result is not None
    assert any("출생 시각이 없어" in warning for warning in result.warnings)


@pytest.mark.parametrize("hour", ["24", "25", "30"])
def test_saju_enricher_rejects_out_of_range_birth_hour(hour):
    with pytest.raises(ValueError, match="00시부터 23시"):
        enrich_saju_question(
            f"양력 1974년 2월 2일 {hour}시생 남자 2026년 7월 24일 운세"
        )


def test_saju_enricher_rejects_multiple_birth_branch_names():
    with pytest.raises(ValueError, match="둘 이상"):
        enrich_saju_question(
            "양력 1974년 2월 2일 유시생 미시생 남자 2026년 7월 24일 운세"
        )


def test_saju_enricher_rejects_more_than_birth_and_target_dates():
    with pytest.raises(ValueError, match="두 날짜"):
        enrich_saju_question(
            "1974년 2월 2일 남자 2026년 7월 23일과 2026년 7월 24일 운세"
        )


def test_saju_enricher_assigns_earlier_date_as_birth_regardless_of_word_order():
    result = enrich_saju_question(
        "2026년 7월 24일 일진을 1974년 2월 2일 유시생 남자 기준으로 알려줘"
    )
    assert result is not None
    assert result.facts[0].startswith("출생 양력 1974-02-02")
    assert result.facts[1].startswith("대상일 양력 2026-07-24")


def test_saju_enricher_fails_closed_on_solar_term_boundary_day():
    with pytest.raises(ValueError, match="절기 경계일"):
        enrich_saju_question("양력 1974년 2월 4일 10시 남자 2026년 7월 24일 운세")


def test_saju_enricher_rejects_duplicate_dates_without_type_error():
    with pytest.raises(ValueError, match="역할이 모호"):
        enrich_saju_question("1990년 5월 3일생 남자 1990년 5월 3일 운세")


def test_relative_target_date_uses_explicit_korea_calendar_date():
    normalized = normalize_relative_saju_dates(
        "1974년 2월 2일 유시생 남자 내일 운세",
        today=date(2026, 7, 24),
    )
    assert "2026년 7월 25일(Asia/Seoul 기준 내일)" in normalized


def test_relative_today_and_yesterday_are_resolved():
    today = normalize_relative_saju_dates(
        "1974년 2월 2일생 오늘 일진", today=date(2026, 7, 24)
    )
    yesterday = normalize_relative_saju_dates(
        "1974년 2월 2일생 어제 운세", today=date(2026, 7, 24)
    )
    assert "2026년 7월 24일(Asia/Seoul 기준 오늘)" in today
    assert "2026년 7월 23일(Asia/Seoul 기준 어제)" in yesterday


@pytest.mark.parametrize("phrase", ["오늘의 운세", "오늘은 운세", "오늘도 운세"])
def test_relative_date_allows_common_korean_particles(phrase):
    normalized = normalize_relative_saju_dates(
        f"1974년 2월 2일생 남자의 {phrase}",
        today=date(2026, 7, 24),
    )
    assert "2026년 7월 24일(Asia/Seoul 기준 오늘)" in normalized


def test_relative_words_in_non_saju_question_are_unchanged():
    question = "오늘과 내일의 차이를 설명해줘"
    assert normalize_relative_saju_dates(question, today=date(2026, 7, 24)) == question


def test_relative_date_does_not_rewrite_compound_day_word():
    question = "1974년 2월 2일생 남자의 내일모레 운세"
    assert normalize_relative_saju_dates(question, today=date(2026, 7, 24)) == question


def test_computational_plan_requests_expert_sections():
    plan = build_query_plan(
        "1974년 2월 2일 유시생 남자 2026년 7월 24일 운세",
        (enrich_saju_question,),
    )
    assert "[전문가형 명리 분석 형식]" in plan.grounded_question
    assert "세운·월운·일진" in plan.grounded_question
    assert "종합운·일/사업·재물·대인관계·건강·실행 조언" in plan.grounded_question


def test_computational_plan_rejects_brief_answer_even_if_it_mentions_fortune():
    plan = build_query_plan(
        "1974년 2월 2일 유시생 남자 2026년 7월 24일 운세와 일진",
        (enrich_saju_question,),
    )
    passed, issues = assess_notebook_answer(
        plan, "운세와 일진입니다. 원국 일간 천간 지지 재물 대인 건강 참고."
    )
    assert not passed
    assert "expert_answer_too_short" in issues


def test_time_window_followup_has_distinct_cache_requirements():
    requirements = infer_requirements("오늘 좋은 시간대와 피할 시간대를 뽑아줘")
    assert requirements == ("좋은 시간대", "피할 시간대")
