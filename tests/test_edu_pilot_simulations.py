import unittest

from scripts.run_edu_pilot_simulations import Scenario, evaluate_transcript


class EduPilotSimulationTests(unittest.TestCase):
    def test_neutral_profile_flags_wrong_gender_salutation(self):
        scenario = Scenario(
            id="neutral_parent",
            label="neutral",
            segment="parent",
            profile={"preferred_salutation": "neutral"},
            turns=["중학생이에요.", "숙제할 때 AI 써요.", "정답부터 찾아요.", "수학 숙제에서 그래요."],
            specificity_tokens=["중학생", "숙제", "정답", "수학"],
            min_offer_turn=4,
        )
        transcript = [
            {"role": "ai", "text": "오프너"},
            {"role": "user", "text": "중학생이에요."},
            {"role": "ai", "text": "어머님, 중학생이면 숙제 때문에 많이 막히시죠."},
            {"role": "user", "text": "숙제할 때 AI 써요."},
            {"role": "ai", "text": "원래 이런 경우엔 정답부터 찾게 되죠."},
        ]
        result = evaluate_transcript(scenario, transcript, show_offer_turn=None, curriculum=None)
        self.assertTrue(result["flags"]["wrong_salutation"])
        self.assertIn("사용자가 선택하지 않은 성별/호칭을 추정해 부른다.", result["customer_complaints"])

    def test_internal_salutation_enum_leak_is_flagged(self):
        scenario = Scenario(
            id="father_parent",
            label="father",
            segment="parent",
            profile={"preferred_salutation": "father"},
            turns=["중학생이에요.", "숙제할 때 AI 써요.", "정답부터 찾아요.", "수학 숙제에서 그래요."],
            specificity_tokens=["중학생", "숙제", "정답", "수학"],
            min_offer_turn=4,
        )
        transcript = [
            {"role": "ai", "text": "오프너"},
            {"role": "user", "text": "중학생이에요."},
            {"role": "ai", "text": "네, father. 중학생이면 숙제 때문에 많이 막히시죠."},
        ]
        result = evaluate_transcript(scenario, transcript, show_offer_turn=None, curriculum=None)
        self.assertTrue(result["flags"]["enum_leak"])
        self.assertIn("내부 호칭 코드(father/mother/neutral)가 답변 문장에 그대로 새어 나와 매우 부자연스럽다.", result["customer_complaints"])

    def test_offer_too_early_and_low_specificity_are_flagged(self):
        scenario = Scenario(
            id="worker",
            label="worker",
            segment="worker",
            profile={"preferred_salutation": "neutral"},
            turns=["사무직이에요.", "AI가 무서워요.", "문서가 어렵고요.", "회의 정리도 막막해요."],
            specificity_tokens=["사무직", "문서", "회의"],
            min_offer_turn=4,
        )
        transcript = [
            {"role": "ai", "text": "오프너"},
            {"role": "user", "text": "사무직이에요."},
            {"role": "ai", "text": "요즘 다들 많이 막히세요. 참 다양합니다."},
            {"role": "user", "text": "AI가 무서워요."},
            {"role": "ai", "text": "열에 아홉은 같은 데서 막혀요."},
            {"role": "user", "text": "문서가 어렵고요."},
            {"role": "ai", "text": "원래 이런 경우엔 조급해지죠."},
            {"role": "user", "text": "회의 정리도 막막해요."},
            {"role": "ai", "text": "수많은 사례를 보면 그래요."},
        ]
        result = evaluate_transcript(scenario, transcript, show_offer_turn=2, curriculum=None)
        self.assertTrue(result["flags"]["offer_too_early"])
        self.assertTrue(result["flags"]["low_specificity"])
        self.assertIn("신뢰가 쌓이기 전에 다음 단계 제안이 빨리 나온다.", result["customer_complaints"])

    def test_specificity_and_actionability_raise_score(self):
        scenario = Scenario(
            id="parent",
            label="parent",
            segment="parent",
            profile={"preferred_salutation": "father"},
            turns=["고등학생이에요.", "전공 고민이 커요.", "공대와 인문계 사이에서 망설여요.", "취업이 걱정돼요."],
            specificity_tokens=["고등학생", "전공", "공대", "인문계", "취업"],
            min_offer_turn=4,
        )
        transcript = [
            {"role": "ai", "text": "오프너"},
            {"role": "user", "text": "고등학생이에요."},
            {"role": "ai", "text": "고등학생이면 대학 전공과 취업 얘기가 빨리 붙습니다."},
            {"role": "user", "text": "전공 고민이 커요."},
            {"role": "ai", "text": "아버님 댁은 공대냐 인문계냐보다, 아이가 어떤 문제를 오래 붙드는지부터 보셔야 합니다."},
            {"role": "user", "text": "공대와 인문계 사이에서 망설여요."},
            {"role": "ai", "text": "비슷한 보호자 사례를 보면 공대/인문계보다 '취업 후 어떤 일을 좋아할지'를 먼저 정리했을 때 덜 흔들립니다."},
            {"role": "user", "text": "취업이 걱정돼요."},
            {"role": "ai", "text": "오늘은 아이와 '좋아하는 문제 3개'를 적어 보고, 내일은 그 문제를 푸는 전공을 같이 찾아보세요."},
        ]
        curriculum = {
            "modules": [
                {"do_now": "오늘 아이와 좋아하는 문제 3개를 적어 보세요."},
            ]
        }
        result = evaluate_transcript(scenario, transcript, show_offer_turn=5, curriculum=curriculum)
        self.assertFalse(result["flags"]["low_specificity"])
        self.assertGreaterEqual(result["subscores"]["personalization"], 15)
        self.assertGreaterEqual(result["subscores"]["conversion_readiness"], 10)

    def test_jargon_and_showy_authority_are_flagged(self):
        scenario = Scenario(
            id="teacher_candidate",
            label="teacher",
            segment="parent",
            profile={"preferred_salutation": "neutral"},
            turns=["교대 준비 중이에요.", "AI가 어렵고 불안해요.", "학생을 어떻게 가르쳐야 할지 모르겠어요.", "실제로 뭘 해야 하죠?"],
            specificity_tokens=["교대", "학생", "가르쳐"],
            min_offer_turn=4,
        )
        transcript = [
            {"role": "ai", "text": "오프너"},
            {"role": "user", "text": "교대 준비 중이에요."},
            {"role": "ai", "text": "P1 관점에서 보면 AI 리터러시와 self-efficacy가 핵심입니다."},
            {"role": "user", "text": "AI가 어렵고 불안해요."},
            {"role": "ai", "text": "이 데이터셋과 프레임워크를 이해하면 세그먼트별 접근이 가능합니다."},
            {"role": "user", "text": "학생을 어떻게 가르쳐야 할지 모르겠어요."},
            {"role": "ai", "text": "수많은 사례를 보면 이런 workflow 정렬이 중요합니다."},
        ]
        result = evaluate_transcript(scenario, transcript, show_offer_turn=None, curriculum=None)
        self.assertTrue(result["flags"]["jargon_overload"])
        self.assertTrue(result["flags"]["showy_authority"])
        self.assertIn("영어·전문 용어가 섞여 AI 초보자가 바로 이해하기 어렵다.", result["customer_complaints"])

    def test_low_empathy_is_flagged(self):
        scenario = Scenario(
            id="parent_low_empathy",
            label="parent",
            segment="parent",
            profile={"preferred_salutation": "neutral"},
            turns=["아이 숙제 때문에 싸워요.", "제가 더 지쳐요.", "어떻게 해야 하죠?", "오늘 뭘 하면 되죠?"],
            specificity_tokens=["숙제", "지쳐", "오늘"],
            min_offer_turn=4,
        )
        transcript = [
            {"role": "ai", "text": "오프너"},
            {"role": "user", "text": "아이 숙제 때문에 싸워요."},
            {"role": "ai", "text": "숙제 문제는 구조적으로 접근해야 합니다."},
            {"role": "user", "text": "제가 더 지쳐요."},
            {"role": "ai", "text": "AI 사용 패턴을 분류하고 규칙을 세우면 됩니다."},
        ]
        result = evaluate_transcript(scenario, transcript, show_offer_turn=None, curriculum=None)
        self.assertTrue(result["flags"]["weak_empathy"])
        self.assertIn("내 감정을 짧게라도 받아주는 느낌이 부족하다.", result["customer_complaints"])


if __name__ == "__main__":
    unittest.main()
