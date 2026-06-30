import importlib.util
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_backend_main():
    module_name = "harness_backend_main_for_vp_training_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "harness-os" / "backend" / "main.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduVpTrainingFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def test_day0_builds_deterministic_safety_concepts(self):
        card = self.mod._edu_vp_build_day0(
            {
                "preferred_llm": "claude",
                "current_device": "iphone",
                "desktop_os": "mac",
                "biggest_friction": "영어라서 무섭다",
                "learning_goal": "업무 답장을 덜 스트레스 받으며 정리하기",
            }
        )

        self.assertIn("Day 0", card["title"])
        self.assertNotIn("첫 답변", card["required_action"])
        self.assertNotIn("post_safety_practice", card)
        self.assertGreaterEqual(card["estimated_minutes"], 60)
        self.assertGreaterEqual(len(card["foundation_concepts"]), 4)
        self.assertGreaterEqual(len(card["schedule_blocks"]), 5)
        self.assertIn("AI와 LLM", card["foundation_concepts"][0]["title"])
        self.assertIn("Large Language Model", card["foundation_concepts"][0]["body"])
        self.assertIn("비 오는 날 아이 준비물", card["foundation_concepts"][0]["body"])
        self.assertIn("생성형 AI", card["foundation_concepts"][1]["title"])
        self.assertIn("Claude", card["foundation_concepts"][1]["body"])
        self.assertIn("Gemini", card["foundation_concepts"][1]["body"])
        self.assertIn("Generative Pre-trained Transformer", card["foundation_concepts"][1]["body"])
        self.assertIn("comprehension_check", card["foundation_concepts"][0])
        self.assertIn("question_prompt", card["foundation_concepts"][0])
        self.assertEqual(card["checklist"], [])
        self.assertEqual(card["sample_materials"], [])
        self.assertEqual(card["blocked_step_options"], [item["id"] for item in card["foundation_concepts"]])

    def test_ui_state_preserves_safety_confirmation(self):
        state = {
            "intake": {"preferred_llm": "claude", "current_device": "iphone", "desktop_os": "mac"},
            "day0": {"completed": False},
            "day1": {"completed": False},
            "ui_state": {"safety_confirmed": {"day0": True}},
        }

        ui_state = self.mod._edu_vp_merge_ui_state(
            state,
            {"selected_stage": "day0", "safety_confirmed": {"day1": False}, "last_client_seq": 3},
        )

        self.assertTrue(ui_state["safety_confirmed"]["day0"])
        self.assertFalse(ui_state["safety_confirmed"]["day1"])
        self.assertEqual(ui_state["last_client_seq"], 3)

    def test_safety_confirmation_requires_required_concept_ids(self):
        state = {"day0": self.mod._edu_vp_build_day0({"preferred_llm": "claude"})}
        concept_ids = [item["id"] for item in state["day0"]["foundation_concepts"]]

        forged = self.mod._edu_vp_safety_confirmation_from_event(
            state,
            "safety_orientation_confirmed",
            {"stage": "day0", "safety_confirmed": {"day0": True}},
        )
        missing_concepts = self.mod._edu_vp_safety_confirmation_from_event(
            state,
            "safety_orientation_confirmed",
            {
                "stage": "day0",
            },
        )
        confirmed = self.mod._edu_vp_safety_confirmation_from_event(
            state,
            "safety_orientation_confirmed",
            {
                "stage": "day0",
                "confirmed_concept_ids": concept_ids,
            },
        )

        self.assertIsNone(forged)
        self.assertIsNone(missing_concepts)
        self.assertEqual(confirmed, {"day0": True})

    def test_safety_coach_answer_uses_llm_with_question_context(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            question="그럼 왜 틀린 준비물을 말할 수도 있나요?",
        )

        with (
            patch.object(self.mod, "_edu_generate_text", return_value=("틀린 준비물을 말할 수 있는 이유는 AI가 실제 공지를 확인하는 것이 아니라 말의 가능성을 고르기 때문입니다.", {"prompt_token_count": 10, "candidates_token_count": 8}, "gemini-test")) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost") as mocked_cost,
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        prompt = mocked_generate.call_args.args[0]
        self.assertIn("왜 틀린 준비물을", prompt)
        self.assertIn("현재 단락 설명", prompt)
        self.assertIn("틀린 준비물", answer)
        self.assertEqual(model, "gemini-test")
        self.assertEqual(usage["prompt_token_count"], 10)
        self.assertIsInstance(fallback_used, bool)
        mocked_cost.assert_called_once()

    def test_safety_coach_downvote_review_records_improvement_when_llm_finds_issue(self):
        raw = '{"verdict":"needs_improvement","issues":["question_not_answered"],"improvement_note":"질문에 먼저 직접 답한다.","confidence":0.82}'

        with patch.object(self.mod, "_edu_generate_text", return_value=(raw, {"prompt_token_count": 9, "candidates_token_count": 7}, "claude-test")):
            review = self.mod._edu_vp_safety_coach_feedback_review(
                question="attention은 누가 설정해?",
                answer="Transformer 논문 저자는 Google 연구자입니다.",
                concept_title="Transformer",
                concept_body="attention은 관련도를 계산합니다.",
            )

        self.assertEqual(review["verdict"], "needs_improvement")
        self.assertIn("question_not_answered", review["issues"])
        self.assertEqual(review["review_source"], "llm+heuristic")
        self.assertEqual(review["model"], "claude-test")

    def test_safety_coach_downvote_review_records_user_mistake_when_no_issue_found(self):
        raw = '{"verdict":"user_mistake","issues":[],"improvement_note":"","confidence":0.76}'

        with patch.object(self.mod, "_edu_generate_text", return_value=(raw, {"prompt_token_count": 8, "candidates_token_count": 5}, "claude-test")):
            review = self.mod._edu_vp_safety_coach_feedback_review(
                question="AI 답은 왜 확인해야 해?",
                answer="AI 답은 초안이라 실제 공지나 원문으로 다시 확인해야 합니다.",
                concept_title="AI 안전",
                concept_body="AI 답은 초안입니다.",
            )

        self.assertEqual(review["verdict"], "user_mistake")
        self.assertEqual(review["issues"], [])
        self.assertEqual(review["review_source"], "llm")

    def test_safety_coach_downvote_review_merges_heuristic_when_llm_returns_user_mistake_issue(self):
        raw = '{"verdict":"needs_improvement","issues":["user_mistake"],"improvement_note":"AI 답변은 사용자가 직접 전문가와 상담하는 것을 권장합니다.","confidence":0.9}'

        with patch.object(self.mod, "_edu_generate_text", return_value=(raw, {"prompt_token_count": 9, "candidates_token_count": 6}, "gemini-test")):
            review = self.mod._edu_vp_safety_coach_feedback_review(
                question="그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
                answer="전문가 상담이 가장 안전합니다. 비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요.",
                concept_title="안전한 사용의 네 가지 기준",
                concept_body="건강, 법률, 돈 문제는 전문가 확인이 필요합니다.",
            )

        self.assertEqual(review["verdict"], "needs_improvement")
        self.assertEqual(review["review_source"], "llm+heuristic")
        self.assertNotIn("user_mistake", review["issues"])
        self.assertIn("contradicted_user_cost_constraint", review["issues"])
        self.assertIn("missing_low_cost_help_options", review["issues"])
        self.assertIn("무료·저비용", review["improvement_note"])

    def test_safety_coach_reprocesses_pending_downvote_reviews(self):
        payload = {
            "question": "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            "answer": "전문가 상담이 가장 안전합니다. 비용이 많이 들지 않는다는 점도 고려해야 합니다.",
            "feedback_saved_at": "2026-06-27T07:43:02+00:00",
        }

        with (
            patch.object(self.mod, "_edu_execute", return_value=[{"case_id": 71, "email": "vp@example.com", "event_payload": payload}]) as mocked_execute,
            patch.object(self.mod, "_edu_vp_review_safety_coach_downvote_async") as mocked_review,
        ):
            result = self.mod._edu_vp_reprocess_pending_safety_coach_downvotes(limit=10)

        self.assertEqual(result["processed"], 1)
        mocked_review.assert_called_once()
        query = mocked_execute.call_args.args[0]
        self.assertIn("NOT EXISTS", query)
        self.assertIn("answer_auto_reinforcement_reviewed", query)

    def test_safety_coach_fallback_empathizes_with_isolated_dependency_question(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "항상 내 편인 말은 안전 신호가 아니다",
            "그런데 주변에 내 얘기를 들어줄 사람이 없을 때는 의존할 수 밖에 없지 않을까?",
        )

        self.assertIn("그렇게 느낄 수", answer)
        self.assertIn("AI라도 붙잡고 싶어지는 건 자연스러운", answer)
        self.assertIn("임시 대화 상대로", answer)
        self.assertNotIn("가족이나 친구", answer)

    def test_safety_coach_fallback_validates_good_feeling_before_boundary(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "항상 내 편인 말은 안전 신호가 아니다",
            "그래도 AI가 나한테 그렇게 해주면 기분이 좋은걸?",
        )

        self.assertIn("그 기분은 진짜", answer)
        self.assertIn("마음이 놓일 수", answer)
        self.assertIn("문제는 기분이 좋다는 사실이 아니라", answer)
        self.assertNotIn("중요한 지점입니다", answer)

    def test_safety_coach_fallback_blocks_concept_definition_for_non_concept_questions(self):
        cases = [
            (
                'AI가 아이에게 "너는 특별해"라고 계속 말해주면 자존감에 좋은 거 아니야?',
                ("자존감", "실제 행동", "사람 관계"),
            ),
            (
                "부모보다 AI가 아이 말을 더 잘 들어주면 그게 꼭 나쁜 일은 아니지 않아?",
                ("꼭 나쁜 일", "사람 관계", "작은 연결"),
            ),
            (
                "AI가 틀릴 수도 있다는 말만 계속하면 아이가 기술을 무서워하지 않을까?",
                ("겁주기", "확인", "다루는 법"),
            ),
        ]

        for question, expected_terms in cases:
            with self.subTest(question=question):
                answer = self.mod._edu_vp_safety_coach_fallback("먼저 말부터 정리하기: AI와 LLM", question)

                for term in expected_terms:
                    self.assertIn(term, answer)
                self.assertNotIn("AI는 큰 이름이고, LLM은", answer)
                self.assertNotIn("비 오는 날 준비물", answer)

    def test_safety_coach_concept_definition_fallback_requires_concept_question(self):
        self.assertFalse(
            self.mod._edu_vp_safety_coach_question_asks_current_concept(
                concept_title="먼저 말부터 정리하기: AI와 LLM",
                question='AI가 아이에게 "너는 특별해"라고 계속 말해주면 자존감에 좋은 거 아니야?',
            )
        )
        self.assertTrue(
            self.mod._edu_vp_safety_coach_question_asks_current_concept(
                concept_title="먼저 말부터 정리하기: AI와 LLM",
                question="AI와 LLM은 무슨 차이야?",
            )
        )

    def test_safety_coach_empathy_detector_ignores_non_emotional_special_not_context(self):
        self.assertFalse(
            self.mod._edu_vp_safety_coach_needs_empathy(
                "수학 공부할 때 AI로 문제 풀이하는 건 이제 별로 특별하지 않습니다. 내가 푼 풀이 보고 어디서 틀렸는지 찾아줘."
            )
        )
        self.assertTrue(
            self.mod._edu_vp_safety_coach_needs_empathy(
                'AI가 아이에게 "너는 특별해"라고 계속 말해주면 자존감에 좋은 거 아니야?'
            )
        )

    def test_safety_coach_red_team_blocks_cold_answer_to_emotional_question(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="그래도 AI가 나한테 그렇게 해주면 기분이 좋은걸?",
            answer="질문해 주신 부분은 '항상 내 편인 말은 안전 신호가 아니다'을 이해하는 데 중요한 지점입니다. 핵심은 AI 답을 사람의 이해나 책임으로 보지 않고, 먼저 초안으로만 쓰는 것입니다.",
            concept_body="AI는 공감과 칭찬을 잘 할 수 있습니다.",
        )

        self.assertIn("missing_empathy_for_emotional_question", issues)
        self.assertIn("cold_instruction_for_emotional_question", issues)

    def test_safety_coach_fallback_acknowledges_professional_cost_barrier(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "개인정보와 고위험 판단 경계 확인",
            "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
        )

        self.assertIn("비용 부담은 실제 장벽", answer)
        self.assertIn("AI로 상황과 질문을 정리", answer)
        self.assertIn("저비용", answer)
        self.assertIn("공공 상담", answer)
        self.assertNotIn("비용이 많이 들지 않는", answer)
        self.assertNotIn("가족이나 친구", answer)

    def test_safety_coach_red_team_blocks_cost_barrier_template_answer(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            answer="AI의 사용은 민감한 일일 뿐 아니라 개인의 건강과 법률에 영향을 미칠 수 있습니다. 전문가와 상담을 통해 필요한 정보를 얻는 것이 가장 안전하고 효과적인 방법입니다. 비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요.",
            concept_body="건강, 법률, 돈 문제는 전문가 확인이 필요합니다.",
        )

        self.assertIn("missing_cost_barrier_acknowledgement", issues)
        self.assertIn("missing_low_cost_help_options", issues)
        self.assertIn("contradicted_user_cost_constraint", issues)
        self.assertIn("family_friend_only_for_cost_barrier", issues)

    def test_safety_coach_downvote_heuristic_flags_cost_barrier_template_answer(self):
        review = self.mod._edu_vp_safety_coach_downvote_heuristic_review(
            question="그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            answer="전문가 상담이 가장 안전합니다. 비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요.",
        )

        self.assertEqual(review["verdict"], "needs_improvement")
        self.assertIn("contradicted_user_cost_constraint", review["issues"])
        self.assertIn("무료·저비용", review["improvement_note"])

    def test_safety_coach_red_team_blocks_definition_instead_of_energy_mechanism(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="왜 AI한테 질문을 하면 전기가 많이 들어?",
            answer="생성형 AI는 새 글, 그림, 답변처럼 무언가를 만들어내는 AI입니다. ChatGPT가 유명해서 GPT라는 말을 자주 듣지만, Claude와 Gemini도 같은 큰 흐름 안의 생성형 AI입니다.",
            concept_body="생성형 AI는 답변을 만듭니다.",
        )

        self.assertIn("missing_energy_use_mechanism", issues)
        self.assertIn("answered_definition_instead_of_energy_question", issues)

    def test_safety_coach_fallback_answers_energy_question_before_transformer_definition(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "Transformer",
            "그런데 AI가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?",
        )

        self.assertIn("데이터센터", answer)
        self.assertIn("서버", answer)
        self.assertIn("냉각", answer)
        self.assertNotIn("Transformer는 문장에서 중요한 말을", answer)

    def test_safety_coach_fallback_answers_general_principle_before_concept_definition(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "Transformer",
            "왜 AI 답변은 사람처럼 자연스럽게 나와?",
        )

        self.assertIn("질문을 숫자로 바꾸고", answer)
        self.assertIn("다음에 올 말을", answer)
        self.assertNotIn("Transformer는 문장에서 중요한 말을", answer)

    def test_safety_coach_red_team_blocks_concept_definition_for_principle_question(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="왜 AI 답변은 사람처럼 자연스럽게 나와?",
            answer="Transformer는 문장에서 중요한 말을 찾아 서로 연결하는 방법입니다. 책을 읽으며 중요한 단어에 형광펜을 칠하고, 그 단어들끼리 연결해 뜻을 잡는 모습과 비슷합니다.",
            concept_body="Transformer의 핵심은 attention입니다.",
        )

        self.assertIn("missing_principle_mechanism", issues)
        self.assertIn("answered_definition_instead_of_principle_question", issues)

    def test_safety_coach_red_team_blocks_repeated_downvoted_answer_pattern(self):
        rejected = "Transformer는 문장에서 중요한 말을 찾아 서로 연결하는 방법입니다. 책을 읽으며 중요한 단어에 형광펜을 칠하고, 그 단어들끼리 연결해 뜻을 잡는 모습과 비슷합니다."

        issues = self.mod._edu_vp_safety_coach_red_team(
            question="그런데 AI가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?",
            answer=rejected,
            concept_body="Transformer의 핵심은 attention입니다.",
            reinforcement_policies=[
                {
                    "question": "그런데 AI가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?",
                    "rejected_answer": rejected,
                    "issues": ["answered_definition_instead_of_principle_question"],
                    "improvement_note": "전기 질문에는 데이터센터, 서버/GPU, 냉각을 먼저 설명한다.",
                    "similarity": 1.0,
                }
            ],
        )

        self.assertIn("repeated_downvoted_answer_pattern", issues)

    def test_safety_coach_fallback_answers_cost_barrier_directly(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "안전한 사용의 네 가지 기준",
            "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
        )
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            answer=answer,
            concept_body="건강, 법률, 돈은 전문가에게 확인합니다.",
        )

        self.assertIn("전문가에게 상담을 받을 때 비용이 많이 드는", answer)
        self.assertIn("무료 법률상담", answer)
        self.assertEqual(issues, [])

    def test_safety_coach_fallback_answers_transformer_machine_learning_hierarchy(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "AI와 머신러닝",
            "Transformer랑 machine learning은 같은 거야?",
        )
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="Transformer랑 machine learning은 같은 거야?",
            answer=answer,
            concept_body="Machine learning은 AI의 한 분야입니다. Transformer는 딥러닝 모델 구조 중 하나입니다.",
        )

        self.assertIn("같은 층위의 말이 아닙니다", answer)
        self.assertIn("Machine learning은 AI 안에 있는 넓은 분야", answer)
        self.assertIn("Transformer는 그 안", answer)
        self.assertEqual(issues, [])

    def test_safety_coach_generic_fallback_anchors_on_question_focus(self):
        question = "이런 상황이면 어떻게 해야 해요? 초등학생 수학 점수가 떨어져서 AI 학습을 시작해야 할지 걱정돼요"
        answer = self.mod._edu_vp_safety_coach_fallback("수집 corpus 기반 사용자 질문", question)
        issues = self.mod._edu_vp_safety_coach_red_team(
            question=question,
            answer=answer,
            concept_body="초등학생 수학 점수가 떨어져서 AI 학습을 시작해야 할지 걱정됩니다.",
        )

        self.assertIn("AI를 공부나 교육에 쓸 때", answer)
        self.assertIn("아이", answer)
        self.assertIn("먼저 아이가 자기 생각", answer)
        self.assertNotIn("question_not_addressed", issues)

    def test_safety_coach_does_not_treat_practical_ai_education_question_as_principle(self):
        self.assertFalse(self.mod._edu_vp_question_asks_direct_principle("AI 강의 안내: 우리 아이 코딩 교육 왜 지금 시작해야 할까요?"))
        self.assertFalse(self.mod._edu_vp_question_asks_direct_principle("요즘 ai활용이 많은데 어떻게 사용하세요?"))
        self.assertFalse(self.mod._edu_vp_question_asks_direct_principle("More Students Use AI for Homework, and More Believe It Harms Critical Thinking"))
        self.assertFalse(self.mod._edu_vp_question_asks_direct_principle("Show HN: ThinkFirst - The Anti-ChatGPT for Students"))
        self.assertTrue(self.mod._edu_vp_question_asks_direct_principle("왜 AI 답변은 사람처럼 자연스럽게 나와?"))

    def test_safety_coach_energy_detector_ignores_human_energy_context(self):
        self.assertFalse(self.mod._edu_vp_question_asks_ai_energy_use("하루에 공부를 너무 많이하면 에너지를 많이 써서 힘들어요. ai답변 사절입니다."))
        self.assertTrue(self.mod._edu_vp_question_asks_ai_energy_use("왜 AI한테 질문을 하면 전기가 많이 들어?"))

    def test_safety_coach_fallback_handles_homework_and_privacy_without_principle_detour(self):
        homework = self.mod._edu_vp_safety_coach_fallback(
            "수집 corpus 기반 사용자 질문",
            "중딩 아들 AI 사용에 대해 어떻게 생각하시나요? 숙제에 그대로 쓰는 게 걱정돼요.",
        )
        privacy = self.mod._edu_vp_safety_coach_fallback(
            "수집 corpus 기반 사용자 질문",
            "AI성장사진 앱에 아이 얼굴 사진을 올려도 괜찮을까요?",
        )

        self.assertIn("숙제", homework)
        self.assertIn("막아야 할 선", homework)
        self.assertIn("해도 되는 선", homework)
        self.assertIn("기준은 하나", homework)
        self.assertIn("아이가 직접 생각하도록 돕는 질문 도구", homework)
        self.assertNotIn("먼저 생각할 일을 AI가 대신", homework)
        self.assertNotIn("아이 생각을 더 좋게", homework)
        self.assertNotIn("질문을 숫자로 바꾸고", homework)
        self.assertIn("사진", privacy)
        self.assertIn("개인 정보", privacy)
        self.assertNotIn("질문을 숫자로 바꾸고", privacy)

    def test_safety_coach_fallback_uses_natural_openings_across_intents(self):
        cases = [
            ("empathy", "항상 내 편인 말은 안전 신호가 아니다", "AI가 아이 마음을 너무 잘 달래주면 의존할까 봐 걱정돼요."),
            ("dependency", "AI 의존 경계", "아이들이 AI에 너무 빠져들면 어떻게 끊어야 하나요?"),
            ("homework", "수집 corpus 기반 사용자 질문", "AI가 아이 숙제를 대신 해주는 건 어디까지 막아야 해?"),
            ("learning", "AI 교육 시작", "초등학생 AI 학습은 어떻게 시작하면 좋을까요?"),
            ("career", "AI와 진로", "AI 때문에 아이 진로와 일자리가 대체될까 봐 걱정돼요."),
            ("privacy", "개인정보와 사진은 조심하기", "AI 앱에 아이 얼굴 사진을 올려도 괜찮을까요?"),
            ("media", "AI와 미디어 사용", "유튜브와 AI 영상을 공부에 써도 괜찮을까요?"),
            ("principle", "Transformer", "왜 AI 답변은 사람처럼 자연스럽게 나와?"),
            ("generic", "수집 corpus 기반 사용자 질문", "새 AI 앱을 아이에게 써보게 해도 될지 모르겠어요."),
        ]
        mechanical_fragments = (
            "·",
            "쪽이 걱정",
            "쪽 걱정",
            "쪽 학습",
            "쪽 진로",
            "쪽 고민",
            "쪽은 그럴 수",
            "질문의 핵심부터",
            "오늘 기준",
        )

        for name, title, question in cases:
            with self.subTest(name=name):
                answer = self.mod._edu_vp_safety_coach_fallback(title, question)

                for fragment in mechanical_fragments:
                    self.assertNotIn(fragment, answer)

        homework_answer = self.mod._edu_vp_safety_coach_fallback(
            "수집 corpus 기반 사용자 질문",
            "AI가 아이 숙제를 대신 해주는 건 어디까지 막아야 해?",
        )
        self.assertIn("전부 막을 필요는 없습니다", homework_answer)
        self.assertIn("막아야 할 선", homework_answer)
        self.assertIn("해도 되는 선", homework_answer)
        self.assertNotIn("아이·숙제·대신", homework_answer)
        self.assertNotIn("아이 생각을 더 좋게", homework_answer)

    def test_safety_coach_final_answer_uses_first_grade_words(self):
        forbidden_terms = ("반례", "허용", "결과물", "핵심 과정", "비판적 사고", "초안", "검증", "인간 역량", "말이라는 걱정")
        answer = self.mod._edu_vp_safety_coach_fallback(
            "수집 corpus 기반 사용자 질문",
            "AI가 아이 숙제를 대신 해주는 건 어디까지 막아야 해?",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, answer)
        self.assertIn("빠진 점", answer)
        self.assertIn("답을 대신 쓰면", answer)
        self.assertIn("해도 되는 선", answer)

    def test_safety_coach_policy_resolver_matches_cost_barrier(self):
        context = self.mod._edu_vp_safety_coach_resolved_policy_context(
            "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요."
        )
        policy_block = self.mod._edu_vp_safety_coach_policy_prompt(context)

        self.assertIn("professional_cost_barrier", context["intent_classes"])
        self.assertIn("professional_cost_barrier_v1", context["policy_ids"])
        self.assertIn("cost_acknowledgement", policy_block)
        self.assertIn("family_friend_only", policy_block)
        self.assertEqual(context["runtime_intent"]["primary"], "cost_barrier")
        self.assertIn("cost", context["taxonomy"]["constraint_type"])
        self.assertIn("low_cost_options", context["taxonomy"]["must_include"])

    def test_safety_coach_taxonomy_maps_existing_intents_without_new_branches(self):
        energy = self.mod._edu_vp_safety_coach_resolved_policy_context(
            "AI가 답변을 할 때 왜 전기가 많이 들어?"
        )
        emotional = self.mod._edu_vp_safety_coach_resolved_policy_context(
            "주변에 내 얘기를 들어줄 사람이 없으면 AI에 의존할 수밖에 없지 않을까?"
        )

        self.assertIn("ai_energy_use", energy["intent_classes"])
        self.assertEqual(energy["runtime_intent"]["primary"], "principle_question")
        self.assertIn("ai_principle", energy["taxonomy"]["topic_domain"])
        self.assertIn("cooling", energy["taxonomy"]["must_include"])
        self.assertIn("isolation_dependency", emotional["intent_classes"])
        self.assertEqual(emotional["runtime_intent"]["primary"], "emotional_support")
        self.assertIn("no_listener_available", emotional["taxonomy"]["constraint_type"])
        self.assertIn("lonely", emotional["taxonomy"]["emotion_state"])

    def test_safety_coach_parses_structured_answer_packet(self):
        raw = """```json
        {"taxonomy":{"topic_domain":["ai_principle"]},"runtime_intent":{"primary":"principle_question"},"rag_synthesis":{"usable":false},"answer_plan":{"opening_move":"direct_answer"},"final_answer":"AI 답변은 가능성이 높은 다음 말을 계산해서 만듭니다."}
        ```"""

        packet = self.mod._edu_vp_parse_safety_coach_answer_packet(raw)

        self.assertIsNotNone(packet)
        assert packet is not None
        self.assertEqual(packet["runtime_intent"]["primary"], "principle_question")
        self.assertIn("다음 말", packet["final_answer"])

    def test_safety_coach_structured_packet_flag_uses_single_model_call(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_attention",
            concept_title="Transformer의 핵심: attention",
            concept_body="attention은 중요한 단어끼리 연결해 문장의 흐름을 잡는 방법입니다.",
            question="attention은 누가 어떻게 설정하는거야?",
        )
        packet = {
            "taxonomy": {"topic_domain": ["ai_principle"], "user_need": ["mechanism_explanation"]},
            "runtime_intent": {"primary": "principle_question", "secondary": [], "latent_need": "attention 설정 주체 설명"},
            "rag_synthesis": {"usable": False, "fresh_angle": "", "reader_relevance": "", "example_seed": "", "evidence_risk": "weak_match"},
            "answer_plan": {
                "opening_move": "direct_answer",
                "core_explanation": ["사람이 문장마다 직접 설정하지 않는다", "모델이 관련도를 계산한다"],
                "fresh_example": "대명사와 이름 연결",
                "boundary": "사람처럼 이해하는 것은 아니다",
                "closing_rule": "계산된 연결 강도",
            },
            "final_answer": (
                "attention은 사람이 문장마다 직접 설정하는 값이 아닙니다. 모델은 학습한 방식에 따라 입력 문장 안에서 "
                "단어 사이 관련도를 계산합니다. 예를 들어 이름과 대명사를 함께 보며 누가 누구인지 연결하는 것처럼 보면 됩니다. "
                "오늘은 attention을 사람이 넣는 표시가 아니라 모델이 계산하는 연결 강도로 기억하면 됩니다."
            ),
        }

        with (
            patch.dict("os.environ", {"EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED": "true"}),
            patch.object(self.mod, "_edu_vp_safety_coach_reinforcement_policies", return_value=[]),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", [], {"selected_count": 0, "rejected_count": 0, "rejected": [], "skip_reason": "test"})),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["model-a", "model-b"]),
            patch.object(self.mod, "_edu_generate_text", return_value=(self.mod.json.dumps(packet, ensure_ascii=False), {"prompt_token_count": 10, "candidates_token_count": 8}, "model-a")) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(mocked_generate.call_count, 1)
        self.assertEqual(model, "model-a+structured_packet")
        self.assertIsInstance(fallback_used, bool)
        self.assertIn("attention은", answer)
        self.assertEqual(usage["_safety_coach_structured_packet"]["runtime_intent"]["primary"], "principle_question")

    def test_safety_coach_quality_issues_apply_policy_contract(self):
        context = self.mod._edu_vp_safety_coach_resolved_policy_context(
            "상담사가 비싸면 AI한테 물어봐도 되나요?"
        )

        issues = self.mod._edu_vp_safety_coach_quality_issues(
            question="상담사가 비싸면 AI한테 물어봐도 되나요?",
            answer="전문가 상담이 안전합니다. 비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요.",
            concept_body="건강, 법률, 돈은 전문가에게 확인합니다.",
            policy_context=context,
        )

        self.assertIn("contradicted_user_cost_constraint", issues)
        self.assertIn("policy_forbidden_cost_denial", issues)
        self.assertIn("policy_forbidden_family_friend_only", issues)

    def test_safety_coach_downvote_review_creates_policy_candidate(self):
        review = {
            "verdict": "needs_improvement",
            "issues": ["contradicted_user_cost_constraint", "missing_low_cost_help_options"],
            "improvement_note": "비용 부담을 먼저 인정하고 저비용 공식 창구를 제시한다.",
            "review_source": "heuristic",
        }
        payload = {
            "question": "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            "answer": "비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요.",
            "answer_version": "test-version",
            "concept_id": "safe_use",
            "concept_title": "안전한 사용의 네 가지 기준",
        }

        candidate = self.mod._edu_vp_safety_coach_policy_candidate_from_downvote(
            case_id=123,
            email="vp@example.com",
            payload=payload,
            review=review,
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["promotion_status"], "candidate")
        self.assertEqual(candidate["highest_severity"], "critical")
        self.assertIn("professional_cost_barrier", candidate["intent_classes"])
        self.assertIn("professional_cost_barrier_v1", candidate["matched_policy_ids"])

    def test_safety_coach_llm_judge_strict_schema_parse(self):
        parsed = self.mod._edu_vp_safety_coach_parse_llm_judge(
            '{"verdict":"needs_improvement","failure_codes":["weak_empathy"],"missing_requirements":["first_empathy"],"unsafe_phrases":[],"better_answer_principle":"감정 먼저 인정","confidence":0.82}'
        )

        self.assertEqual(parsed["verdict"], "needs_improvement")
        self.assertEqual(parsed["failure_codes"], ["weak_empathy"])
        self.assertEqual(parsed["confidence"], 0.82)

    def test_safety_coach_answer_version_ignores_stale_client_version(self):
        current = self.mod._EDU_VP_SAFETY_COACH_ANSWER_VERSION

        self.assertEqual(self.mod._edu_vp_safety_coach_answer_version("2026-06-27-constraint-aware-v11"), current)
        self.assertEqual(self.mod._edu_vp_safety_coach_answer_version("2026-06-28-natural-rag-v17"), current)
        self.assertEqual(self.mod._edu_vp_safety_coach_answer_version("test-version"), current)
        self.assertEqual(self.mod._edu_vp_safety_coach_answer_version(current), current)

    def test_safety_coach_quality_review_can_use_llm_judge(self):
        context = self.mod._edu_vp_safety_coach_resolved_policy_context(
            "그래도 AI가 나한테 그렇게 해주면 기분이 좋은걸?"
        )
        judge = {
            "verdict": "needs_improvement",
            "failure_codes": ["weak_empathy"],
            "missing_requirements": ["first_empathy"],
            "unsafe_phrases": [],
            "better_answer_principle": "감정 먼저 인정",
            "confidence": 0.8,
            "review_source": "llm_judge",
        }

        with patch.object(self.mod, "_edu_vp_safety_coach_llm_judge_review", return_value=judge):
            review = self.mod._edu_vp_safety_coach_quality_review(
                question="그래도 AI가 나한테 그렇게 해주면 기분이 좋은걸?",
                answer="그 기분은 진짜입니다. AI가 나한테 그렇게 해주면 마음이 놓일 수 있습니다. AI 위로는 받을 수 있지만 중요한 결정은 잠깐 멈춰 다시 확인하면 됩니다.",
                concept_body="AI가 항상 내 편처럼 말해도 정확하다는 뜻은 아닙니다.",
                policy_context=context,
                llm_judge_enabled=True,
            )

        self.assertIn("llm_judge_weak_empathy", review["issues"])
        self.assertEqual(review["llm_judge"]["verdict"], "needs_improvement")

    def test_safety_coach_generation_retries_when_llm_judge_fails_answer(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_sycophancy",
            concept_title="항상 내 편인 말의 위험",
            concept_body="AI가 항상 내 편처럼 말해도 정확하다는 뜻은 아닙니다.",
            question="그래도 AI가 나한테 그렇게 해주면 기분이 좋은걸?",
            answer_version="test-version",
        )
        weak = "그 기분은 진짜입니다. AI가 나한테 그렇게 해주면 위로는 받을 수 있지만 중요한 결정은 다시 확인하면 됩니다."
        fixed = "그 기분은 진짜입니다. AI가 나한테 그렇게 해주면 잠깐 마음이 놓일 수 있습니다. 다만 그 좋은 느낌 때문에 중요한 결정을 바로 하지 않도록 잠깐 멈춰 다시 확인하면 됩니다."
        judge_fail = {
            "verdict": "needs_improvement",
            "failure_codes": ["weak_empathy"],
            "missing_requirements": ["warmer_first_sentence"],
            "unsafe_phrases": [],
            "better_answer_principle": "감정의 실제성을 더 따뜻하게 인정한다.",
            "confidence": 0.77,
            "review_source": "llm_judge",
        }
        judge_pass = {
            "verdict": "pass",
            "failure_codes": [],
            "missing_requirements": [],
            "unsafe_phrases": [],
            "better_answer_principle": "",
            "confidence": 0.8,
            "review_source": "llm_judge",
        }

        with (
            patch.dict("os.environ", {"EDU_SAFETY_COACH_LLM_JUDGE_ENABLED": "true"}),
            patch.object(self.mod, "_edu_vp_safety_coach_fast_answer", return_value=None),
            patch.object(self.mod, "_edu_vp_safety_coach_reinforcement_policies", return_value=[]),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence", return_value=("", [], {"selected_count": 0, "rejected_count": 0, "rejected": [], "skip_reason": "test"})),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["model-a", "model-b"]),
            patch.object(self.mod, "_edu_generate_text", side_effect=[(weak, {"prompt_token_count": 10, "candidates_token_count": 8}, "model-a"), (fixed, {"prompt_token_count": 11, "candidates_token_count": 9}, "model-b")]) as mocked_generate,
            patch.object(self.mod, "_edu_vp_safety_coach_llm_judge_review", side_effect=[judge_fail, judge_pass]) as mocked_judge,
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(mocked_generate.call_count, 2)
        self.assertEqual(mocked_judge.call_count, 2)
        self.assertEqual(model, "model-b")
        self.assertEqual(answer, fixed)
        self.assertEqual(usage["_safety_coach_llm_judge"]["verdict"], "pass")
        self.assertIsInstance(fallback_used, bool)

    def test_safety_coach_reinforcement_policy_lookup_matches_similar_downvote_review(self):
        payload = {
            "question": "그런데 AI가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?",
            "answer": "Transformer는 문장에서 중요한 말을 찾아 서로 연결하는 방법입니다.",
            "answer_version": "2026-06-27-auto-reinforcement-v10",
            "concept_title": "Transformer",
            "auto_reinforcement": {
                "verdict": "needs_improvement",
                "issues": ["answered_definition_instead_of_principle_question"],
                "improvement_note": "전기 질문에는 데이터센터, 서버/GPU, 냉각을 먼저 설명한다.",
                "review_source": "llm",
            },
        }

        with patch.object(self.mod, "_edu_execute", return_value=[{"event_payload": payload, "created_at": None}]) as mocked_execute:
            policies = self.mod._edu_vp_safety_coach_reinforcement_policies(
                question="AI 답변 작업이 왜 전기를 많이 써?",
                concept_title="Transformer",
                answer_version="2026-06-27-auto-reinforcement-v10",
            )

        self.assertEqual(len(policies), 1)
        self.assertIn("데이터센터", policies[0]["improvement_note"])
        self.assertGreaterEqual(policies[0]["similarity"], 0.72)
        query = mocked_execute.call_args.args[0]
        self.assertIn("answer_auto_reinforcement_reviewed", query)

    def test_safety_coach_reinforcement_policy_lookup_matches_cost_barrier_paraphrases(self):
        payload = {
            "question": "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            "answer": "전문가 상담이 가장 안전합니다. 비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요.",
            "answer_version": "2026-06-27-constraint-aware-v11",
            "concept_title": "안전한 사용의 네 가지 기준",
            "auto_reinforcement": {
                "verdict": "needs_improvement",
                "issues": ["contradicted_user_cost_constraint", "missing_low_cost_help_options"],
                "improvement_note": "비용·접근성 장벽이 있으면 먼저 현실 부담을 인정하고, 무료·저비용·공공 창구 같은 실행 가능한 선택지를 제시한다.",
                "review_source": "llm+heuristic",
            },
        }

        with patch.object(self.mod, "_edu_execute", return_value=[{"event_payload": payload, "created_at": None}]):
            policies = self.mod._edu_vp_safety_coach_reinforcement_policies(
                question="상담사가 비싸면 AI한테 물어봐도 되나요?",
                concept_title="안전한 사용의 네 가지 기준",
                answer_version="2026-06-27-constraint-aware-v11",
            )

        self.assertEqual(len(policies), 1)
        self.assertGreaterEqual(policies[0]["similarity"], 0.72)
        self.assertIn("무료·저비용", policies[0]["improvement_note"])

    def test_safety_coach_reinforcement_policy_prefers_corrected_review_over_stale_llm_review(self):
        stale = {
            "question": "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            "answer": "전문가 상담이 가장 안전합니다.",
            "answer_version": "2026-06-27-auto-reinforcement-v10",
            "concept_title": "안전한 사용의 네 가지 기준",
            "auto_reinforcement": {
                "verdict": "needs_improvement",
                "issues": ["user_mistake"],
                "improvement_note": "AI 답변은 사용자가 직접 전문가와 상담하는 것을 권장합니다.",
                "review_source": "llm",
            },
        }
        corrected = {
            **stale,
            "auto_reinforcement": {
                "verdict": "needs_improvement",
                "issues": ["contradicted_user_cost_constraint", "missing_low_cost_help_options"],
                "improvement_note": "비용·접근성 장벽이 있으면 먼저 현실 부담을 인정하고, 무료·저비용·공공 창구 같은 실행 가능한 선택지를 제시한다.",
                "review_source": "corrected_llm+heuristic",
            },
        }

        with patch.object(self.mod, "_edu_execute", return_value=[{"event_payload": stale, "created_at": "2026-06-27T07:43:05"}, {"event_payload": corrected, "created_at": "2026-06-27T07:47:24"}]):
            policies = self.mod._edu_vp_safety_coach_reinforcement_policies(
                question="전문가 상담은 돈이 많이 들지 않나요?",
                concept_title="안전한 사용의 네 가지 기준",
                answer_version="2026-06-27-constraint-aware-v11",
                limit=3,
            )

        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0]["review_source"], "corrected_llm+heuristic")
        self.assertNotIn("user_mistake", policies[0]["issues"])

    def test_safety_coach_auto_reinforcement_prompt_blocks_bad_repeat_and_switches_model(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_transformer_attention",
            concept_title="Transformer",
            concept_body="Transformer의 핵심은 attention입니다.",
            question="그런데 AI가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?",
            answer_version="2026-06-27-auto-reinforcement-v10",
        )
        bad = "Transformer는 문장에서 중요한 말을 찾아 서로 연결하는 방법입니다. 책을 읽으며 중요한 단어에 형광펜을 칠하고, 그 단어들끼리 연결해 뜻을 잡는 모습과 비슷합니다."
        good = "AI 답변에 전기가 많이 든다고 하는 이유는 데이터센터의 서버가 답을 만들기 위해 많은 계산을 하기 때문입니다. 특히 GPU 같은 칩이 단어 후보를 계속 비교하고, 뜨거워진 장비를 식히는 냉각에도 전기가 들어갑니다. 휴대폰만 쓰는 것처럼 보여도 뒤에서는 큰 컴퓨터실이 같이 움직인다고 보면 됩니다."
        policies = [
            {
                "question": req.question,
                "rejected_answer": bad,
                "issues": ["answered_definition_instead_of_principle_question"],
                "improvement_note": "전기 질문에는 데이터센터, 서버/GPU, 냉각을 먼저 설명한다.",
                "similarity": 1.0,
            }
        ]

        with (
            patch.object(self.mod, "_edu_vp_safety_coach_reinforcement_policies", return_value=policies),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["model-a", "model-b"]),
            patch.object(self.mod, "_edu_generate_text", side_effect=[(bad, {"prompt_token_count": 10, "candidates_token_count": 8}, "model-a"), (good, {"prompt_token_count": 11, "candidates_token_count": 9}, "model-b")]) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        prompt = mocked_generate.call_args_list[0].args[0]
        self.assertIn("[자동강화 규칙]", prompt)
        self.assertIn("전기 질문에는 데이터센터", prompt)
        self.assertIn("[적용된 답변 품질 정책]", prompt)
        self.assertIn("ai_energy_use_v1", prompt)
        self.assertEqual(model, "model-b")
        self.assertIn("데이터센터", answer)
        self.assertIsInstance(fallback_used, bool)
        self.assertEqual(usage["_safety_coach_reinforcement_policies"], policies)
        self.assertIn("ai_energy_use_v1", usage["_safety_coach_policy_context"]["policy_ids"])

    def test_safety_coach_switches_model_when_energy_question_gets_generic_definition(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_generation",
            concept_title="생성형 AI",
            concept_body="생성형 AI는 새 답을 만드는 도구입니다.",
            question="왜 AI한테 질문을 하면 전기가 많이 들어?",
        )
        bad = "생성형 AI는 새 글, 그림, 답변처럼 무언가를 만들어내는 AI입니다. ChatGPT가 유명해서 GPT라는 말을 자주 듣습니다."
        good = "짧게 말하면 답을 만들 때 멀리 있는 데이터센터의 서버가 많은 계산을 하기 때문입니다. 특히 큰 AI는 GPU 같은 칩이 단어를 하나씩 고르며 계산하고, 뜨거워진 장비를 식히는 냉각에도 전기가 듭니다. 집에서 휴대폰만 만지는 것처럼 보여도 뒤에서는 큰 컴퓨터실이 함께 움직인다고 보면 됩니다."

        with (
            patch.object(self.mod, "_edu_vp_safety_coach_fast_answer", return_value=None),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["gemini-test", "claude-test"]),
            patch.object(self.mod, "_edu_generate_text", side_effect=[(bad, {"prompt_token_count": 10, "candidates_token_count": 8}, "gemini-test"), (good, {"prompt_token_count": 11, "candidates_token_count": 9}, "claude-test")]),
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, _usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertTrue(model.startswith("claude-test"))
        self.assertIn("데이터센터", answer)
        self.assertIn("냉각", answer)
        self.assertFalse(fallback_used)

    def test_safety_coach_switches_model_when_answer_repeats_source_example(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="비 오는 날 아이 준비물 알려줘 우산, 장화, 여벌 양말 학교 공지나 실제 날씨",
            question="다음 글에 이어질 조사는 어떻게 추측하나요?",
        )
        first = (
            "비 오는 날 아이 준비물 알려줘라고 쓰면 우산, 장화, 여벌 양말처럼 답합니다. "
            "학교 공지나 실제 날씨는 사람이 봐야 합니다."
        )
        second = (
            "조사는 앞말이 문장에서 하는 일을 보고 고릅니다. 예를 들어 '학교 __ 갔다'에서는 "
            "장소로 향한다는 뜻이 자연스러워 '에'가 잘 맞습니다."
        )

        with (
            patch.dict("os.environ", {"EDU_SAFETY_COACH_TOTAL_TIMEOUT_SECONDS": "30"}),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", [], {"skip_reason": "test"})),
            patch.object(self.mod, "_edu_vp_safety_coach_fast_answer", return_value=None),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["gemini-test", "claude-test"]),
            patch.object(self.mod, "_edu_generate_text", side_effect=[
                (first, {"prompt_token_count": 10, "candidates_token_count": 8}, "gemini-test"),
                (second, {"prompt_token_count": 12, "candidates_token_count": 9}, "claude-test"),
            ]) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, _usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(mocked_generate.call_count, 2)
        self.assertIn("조사는", answer)
        self.assertIn("학교 __ 갔다", answer)
        self.assertNotIn("우산, 장화, 여벌 양말", answer)
        self.assertTrue(model.startswith("claude-test"))
        self.assertFalse(fallback_used)

    def test_safety_coach_red_team_requires_transformer_paper_authors(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_transformer_origin",
            concept_title="생성형 AI는 어떻게 시작됐나",
            concept_body="Transformer는 2017년 Attention Is All You Need 논문으로 널리 알려졌습니다.",
            question="Transformer 이론 관련 논문은 누가 발표했나요?",
        )
        weak = (
            "Transformer 이론 관련 논문은 'Attention Is All You Need'라는 제목으로 2017년에 발표되었습니다. "
            "이 논문은 Transformer 방법의 핵심을 설명했습니다."
        )
        fixed = (
            "Transformer를 널리 알린 논문은 Google 연구팀의 Ashish Vaswani, Noam Shazeer, "
            "Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, "
            "Illia Polosukhin이 함께 발표했습니다."
        )

        with (
            patch.dict("os.environ", {"EDU_SAFETY_COACH_TOTAL_TIMEOUT_SECONDS": "30"}),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", [], {"skip_reason": "test"})),
            patch.object(self.mod, "_edu_vp_safety_coach_fast_answer", return_value=None),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["gemini-test", "claude-test"]),
            patch.object(self.mod, "_edu_generate_text", side_effect=[
                (weak, {"prompt_token_count": 10, "candidates_token_count": 8}, "gemini-test"),
                (fixed, {"prompt_token_count": 12, "candidates_token_count": 9}, "claude-test"),
            ]) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, _usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(mocked_generate.call_count, 2)
        self.assertIn("Google", answer)
        self.assertIn("Vaswani", answer)
        self.assertIn("Shazeer", answer)
        self.assertNotEqual(answer, weak)
        self.assertTrue(model.startswith("claude-test"))
        self.assertFalse(fallback_used)

    def test_safety_coach_switches_model_after_quality_failures(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="비 오는 날 아이 준비물 알려줘 우산, 장화, 여벌 양말 학교 공지나 실제 날씨",
            question="다음 글에 이어질 조사는 어떻게 추측하나요?",
        )
        weak = "비 오는 날 아이 준비물 알려줘라고 쓰면 우산, 장화, 여벌 양말처럼 답합니다."
        fixed = (
            "조사는 앞말이 문장에서 하는 일을 보고 고릅니다. 예를 들어 '학교 __ 갔다'에서는 "
            "장소로 향한다는 뜻이 자연스러워 '에'가 잘 맞습니다."
        )

        with (
            patch.dict("os.environ", {"EDU_SAFETY_COACH_TOTAL_TIMEOUT_SECONDS": "30"}),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", [], {"skip_reason": "test"})),
            patch.object(self.mod, "_edu_vp_safety_coach_fast_answer", return_value=None),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["gemini-2.5-flash", "claude-haiku-4-5"]),
            patch.object(self.mod, "_edu_generate_text", side_effect=[
                (weak, {"prompt_token_count": 10, "candidates_token_count": 8}, "gemini-2.5-flash"),
                (fixed, {"prompt_token_count": 11, "candidates_token_count": 7}, "claude-haiku-4-5"),
            ]) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
            patch.object(self.mod, "_edu_runtime_event"),
        ):
            answer, model, _usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(mocked_generate.call_count, 2)
        self.assertEqual(mocked_generate.call_args_list[0].kwargs["model_ladder"], ["gemini-2.5-flash"])
        self.assertEqual(mocked_generate.call_args_list[1].kwargs["model_ladder"], ["claude-haiku-4-5"])
        self.assertTrue(model.startswith("claude-haiku-4-5"))
        self.assertIn("조사는", answer)
        self.assertFalse(fallback_used)

    def test_safety_coach_switches_model_after_fast_call_failure(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
        )
        fixed = "명사는 앞뒤 말이 만드는 장면을 보고 고릅니다. 예를 들어 '비 오는 날 ___를 챙겨'라면 우산이 자연스럽습니다."

        with (
            patch.object(self.mod, "_edu_vp_safety_coach_fast_answer", return_value=None),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["gemini-2.5-flash", "claude-haiku-4-5"]),
            patch.object(self.mod, "_edu_generate_text", side_effect=[
                TimeoutError("gemini slow"),
                (fixed, {"prompt_token_count": 11, "candidates_token_count": 7}, "claude-haiku-4-5"),
            ]) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
            patch.object(self.mod, "_edu_runtime_event"),
        ):
            answer, model, _usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(mocked_generate.call_count, 2)
        self.assertEqual(mocked_generate.call_args_list[0].kwargs["model_ladder"], ["gemini-2.5-flash"])
        self.assertEqual(mocked_generate.call_args_list[1].kwargs["model_ladder"], ["claude-haiku-4-5"])
        self.assertTrue(model.startswith("claude-haiku-4-5"))
        self.assertIn("명사는", answer)
        self.assertIsInstance(fallback_used, bool)

    def test_safety_coach_deadline_fallback_preserves_validated_rag_generically(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_privacy",
            concept_title="개인정보와 사진은 조심하기",
            concept_body="AI에는 아이 얼굴 사진과 개인정보를 함부로 넣지 않습니다.",
            question="아이 사진을 AI 앱에 올려도 되는지 어디까지 막아야 하나요?",
        )
        evidence_items = [
            {
                "id": "generic-ai-risk",
                "source": "general source",
                "source_url": "https://example.org/general-ai-risk",
                "cite": "AI 사용에는 여러 위험이 있으니 보호자가 아이와 함께 확인해야 합니다.",
                "score": 5.0,
                "validated": True,
            },
            {
                "id": "privacy-photo",
                "source": "privacy guide",
                "source_url": "https://example.org/privacy-photo",
                "title": "아이 사진 업로드 전 확인",
                "cite": (
                    "앱에 아이 사진을 올리기 전에는 얼굴, 학교 이름, 위치 정보 같은 개인정보가 "
                    "저장되거나 재사용될 수 있는지 먼저 확인해야 합니다."
                ),
                "score": 4.0,
                "validated": True,
            },
        ]

        with (
            patch.dict("os.environ", {"EDU_SAFETY_COACH_TOTAL_TIMEOUT_SECONDS": "0.4"}),
            patch.object(self.mod, "_edu_vp_safety_coach_fast_answer", return_value=None),
            patch.object(self.mod, "_edu_vp_safety_coach_reinforcement_policies", return_value=[]),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", evidence_items, {"selected_count": 2})),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["gpt-4o-mini"]),
            patch.object(self.mod, "_edu_runtime_event"),
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(model, "gpt-4o-mini+deadline_fallback+rag")
        self.assertTrue(fallback_used)
        self.assertTrue(usage["_safety_coach_rag_infused"])
        self.assertTrue(usage["_safety_coach_rag_patch_applied"])
        self.assertIn("privacy guide '아이 사진 업로드 전 확인'에는", answer)
        self.assertNotIn("[privacy guide '아이 사진 업로드 전 확인'](https://example.org/privacy-photo)에는", answer)
        self.assertIn("출처: [privacy guide '아이 사진 업로드 전 확인'](https://example.org/privacy-photo)", answer)
        self.assertIn("얼굴, 학교 이름, 위치 정보", answer)
        self.assertNotIn("여러 위험", answer)

    def test_safety_coach_red_team_blocks_prompt_marker_leakage(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="그런데도 다정해서 자꾸 빠져들어요. 어떻게 하나요?",
            answer="[현재 단락 설명] AI는 보호자가 아닙니다. [사용자 질문 또는 피드백] 그런데도 얘기를 하",
            concept_body="AI는 사용자의 삶을 책임지는 보호자가 아닙니다.",
        )

        self.assertIn("prompt_marker_leaked", issues)
        self.assertIn("possibly_truncated", issues)

    def test_safety_coach_rejects_ungrounded_evidence_reference(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="AI에 자꾸 의존하게 되면 어떻게 하나요?",
            answer="관련 자료에서는 이런 경우 전문가 상담이 필요하다고 말합니다.",
            concept_body="AI 답변은 사람이 확인해야 합니다.",
            evidence_items=[],
        )

        self.assertIn("unsupported_evidence_reference", issues)

    def test_safety_coach_red_team_blocks_transformer_machine_learning_peer_framing(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="Transformer 이론과 Machine Learning과는 어떤 차이가 있는지 알려줘.",
            answer=(
                "Transformer와 Machine Learning 모두 AI 기술 중 하나이며, 각각 다른 방식으로 데이터를 "
                "학습하고 문제를 해결하는 데 도움이 됩니다. Transformer는 특정 데이터셋에 대해 학습한 "
                "모델을 사용하는 방식입니다."
            ),
            concept_body="Transformer는 생성형 AI의 중요한 기반입니다.",
        )

        self.assertIn("transformer_ml_hierarchy_error", issues)

    def test_safety_coach_evidence_query_prioritizes_user_question(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_transformer_origin",
            concept_title="생성형 AI는 어떻게 시작됐나",
            concept_body="오늘 쓰는 ChatGPT, Claude, Gemini 같은 생성형 AI는 Transformer라는 방법에서 크게 발전했습니다.",
            question="Transformer 이론과 Machine Learning과는 어떤 차이가 있는지 알려줘.",
        )

        with (
            patch.object(self.mod, "_edu_vp_safety_coach_evidence", return_value=("", [], {"query": ""})) as mocked_evidence,
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["gemini-test"]),
            patch.object(self.mod, "_edu_generate_text", return_value=(
                "Machine Learning은 컴퓨터가 데이터에서 규칙을 배우게 하는 큰 분야입니다. Transformer는 그 안에서 특히 글의 단어 관계를 잘 보는 딥러닝 구조입니다.",
                {"prompt_token_count": 10, "candidates_token_count": 8},
                "gemini-test",
            )),
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            self.mod._edu_vp_generate_safety_coach_answer(req)

        evidence_query = mocked_evidence.call_args.args[0]
        self.assertTrue(evidence_query.startswith("Transformer 이론과 Machine Learning"))
        self.assertIn("validation_text", mocked_evidence.call_args.kwargs)
        self.assertEqual(mocked_evidence.call_args.kwargs["limit"], 3)

    def test_safety_coach_evidence_validation_requires_relevant_source(self):
        valid, reasons = self.mod._edu_vp_validate_safety_coach_evidence(
            query="다정한 AI에 자꾸 빠져들고 의존하게 됩니다",
            item={
                "id": "x1",
                "source": "youtube official video mv",
                "cite": "짧은 영상 소개",
                "body": "음악 영상 설명",
                "_score": 0.2,
            },
        )

        self.assertFalse(valid)
        self.assertIn("cite_too_short", reasons)
        self.assertIn("low_quality_item", reasons)

    def test_safety_coach_evidence_validation_accepts_cosine_score(self):
        with patch.dict("os.environ", {"EDU_RAG_MIN_SCORE": "0.30"}):
            valid, reasons = self.mod._edu_vp_validate_safety_coach_evidence(
                query="중학생 숙제 AI 사용을 어떻게 지도하나요",
                item={
                    "id": "x2",
                    "source": "OECD Education Report",
                    "source_url": "https://example.org/oecd-homework",
                    "cite": "중학생 숙제에서 AI를 답안기로만 쓰지 않도록 부모가 질문 설계와 풀이 과정을 같이 점검하라는 내용입니다.",
                    "body": "중학생 숙제 AI 지도 질문 설계 풀이 과정",
                    "_score": 0.91,
                },
            )

        self.assertTrue(valid, reasons)
        self.assertNotIn("low_retrieval_score", reasons)

    def test_safety_coach_evidence_validation_requires_source_url(self):
        valid, reasons = self.mod._edu_vp_validate_safety_coach_evidence(
            query="중학생 숙제 AI 사용을 어떻게 지도하나요",
            item={
                "id": "x3",
                "source": "OECD Education Report",
                "cite": "중학생 숙제에서 AI를 답안기로만 쓰지 않도록 부모가 질문 설계와 풀이 과정을 같이 점검하라는 내용입니다.",
                "body": "중학생 숙제 AI 지도 질문 설계 풀이 과정",
                "_score": 0.91,
            },
        )

        self.assertFalse(valid)
        self.assertIn("missing_source_url", reasons)

    def test_safety_coach_evidence_validation_backfills_source_url_from_refined_output_id(self):
        self.mod._EDU_VP_SAFETY_COACH_SOURCE_URL_CACHE.clear()
        self.mod._EDU_VP_SAFETY_COACH_RAW_TEXT_CACHE.clear()
        cite = "아이 숙제에서 AI가 대신 답을 만들어 주기보다 아이가 먼저 생각하고 질문을 만드는 데 쓰도록 지도하라는 내용입니다."

        def fake_execute_query(query, params=None, fetch=False):
            self.assertIn("FROM refined_outputs", query)
            self.assertEqual(params, (8105,))
            self.assertTrue(fetch)
            return [{"raw_data": {"url": "https://example.org/raw-homework-source", "description": cite}}]

        with patch.object(self.mod, "execute_query", side_effect=fake_execute_query):
            valid, reasons = self.mod._edu_vp_validate_safety_coach_evidence(
                query="아이 숙제 AI 대신 쓰는 것 어디까지 막아야 하나요",
                item={
                    "id": "fresh-8105-1",
                    "source": "Naver_카페글",
                    "source_name": "Naver_카페글",
                    "title": "AI와 친한 아이가 살아남습니다",
                    "cite": cite,
                    "body": "아이 숙제 AI 대신 답 생각 질문",
                    "_score": 0.91,
                },
            )

        self.assertTrue(valid, reasons)
        self.assertNotIn("missing_source_url", reasons)
        self.assertEqual(
            self.mod._EDU_VP_SAFETY_COACH_SOURCE_URL_CACHE["refined:8105"],
            "https://example.org/raw-homework-source",
        )

    def test_safety_coach_evidence_validation_rejects_refined_synthesis_not_in_source(self):
        self.mod._EDU_VP_SAFETY_COACH_SOURCE_URL_CACHE.clear()
        self.mod._EDU_VP_SAFETY_COACH_RAW_TEXT_CACHE.clear()

        def fake_execute_query(query, params=None, fetch=False):
            self.assertIn("FROM refined_outputs", query)
            self.assertEqual(params, (8105,))
            self.assertTrue(fetch)
            return [{
                "raw_data": {
                    "url": "https://example.org/raw-homework-source",
                    "description": "대한 의존도가 높아진다면 아이의 생각은 없어지고 GPT 결과 판단력이 낮아질까봐 걱정된다는 내용입니다.",
                }
            }]

        with patch.object(self.mod, "execute_query", side_effect=fake_execute_query):
            valid, reasons = self.mod._edu_vp_validate_safety_coach_evidence(
                query="아이 숙제 AI 대신 쓰는 것 어디까지 막아야 하나요",
                item={
                    "id": "fresh-8105-1",
                    "source": "Naver_카페글",
                    "source_name": "Naver_카페글",
                    "title": "AI와 친한 아이가 살아남습니다",
                    "cite": "AI가 대신 해주는 것이 아니라, AI를 활용해 더 깊이 생각하고 더 창의적인 결과물을 만들도록 지도해 주세요.",
                    "body": "아이 숙제 AI 대신 답 생각 질문",
                    "_score": 0.91,
                },
            )

        self.assertFalse(valid)
        self.assertIn("cite_not_supported_by_source", reasons)

    def test_safety_coach_selected_evidence_uses_backfilled_source_url(self):
        self.mod._EDU_VP_SAFETY_COACH_SOURCE_URL_CACHE.clear()
        self.mod._EDU_VP_SAFETY_COACH_RAW_TEXT_CACHE.clear()
        cite = "아이 숙제에서 AI가 대신 답을 만들어 주기보다 아이가 먼저 생각하고 질문을 만드는 데 쓰도록 지도하라는 내용입니다."
        item = {
            "id": "fresh-8105-1",
            "source": "'AI와 친한 아이가 살아남습니다'",
            "source_name": "Naver_카페글",
            "title": "AI와 친한 아이가 살아남습니다",
            "cite": cite,
            "body": "아이 숙제 AI 대신 답 생각 질문",
            "_score": 0.91,
        }

        with (
            patch.object(self.mod, "_retrieve_evidence_bundle", return_value={"items": [item]}),
            patch.object(self.mod, "execute_query", return_value=[{"raw_data": {"url": "https://example.org/raw-homework-source", "description": cite}}]),
        ):
            evidence_text, selected, meta = self.mod._edu_vp_safety_coach_evidence(
                "AI가 아이 숙제를 대신 해주는 건 어디까지 막아야 해?",
                validation_text="아이 숙제 AI 대신 답 생각 질문",
                limit=1,
            )

        self.assertEqual(meta["selected_count"], 1)
        self.assertEqual(selected[0]["source_url"], "https://example.org/raw-homework-source")
        self.assertEqual(selected[0]["refined_output_id"], "8105")
        self.assertIn("Naver 카페글", evidence_text)
        self.assertIn("https://example.org/raw-homework-source", evidence_text)

    def test_safety_coach_source_label_ignores_generic_collector_name(self):
        label = self.mod._edu_vp_safety_coach_source_label(
            {
                "source": "YouTube · 별의별 교육연구소 — 'AI 없으면 불안한 아이들, 교육은 어디로 가는가?'",
                "source_name": "youtube search",
                "title": "",
            }
        )

        self.assertIn("별의별 교육연구소", label)
        self.assertNotIn("youtube search", label.lower())

    def test_safety_coach_normalizes_question_for_duplicate_detection(self):
        normalized = self.mod._edu_vp_normalize_safety_question("  다음 글에\n이어질   조사는 어떻게 추측하나요?  ")

        self.assertEqual(normalized, "다음 글에 이어질 조사는 어떻게 추측하나요?")

    def test_safety_coach_question_similarity_matches_close_wording(self):
        score = self.mod._edu_vp_safety_question_similarity(
            "다음 글에 이어질 최적의 명사는 어떻게 추측해?",
            "다음 문장에 이어질 명사는 어떻게 추측하나요?",
        )

        self.assertGreaterEqual(score, 0.82)

    def test_safety_coach_question_similarity_rejects_different_topic(self):
        score = self.mod._edu_vp_safety_question_similarity(
            "다음 글에 이어질 최적의 명사는 어떻게 추측해?",
            "AI에게 너무 의존하게 될 때 어떻게 멈추나요?",
        )

        self.assertLess(score, 0.82)

    def test_safety_coach_question_similarity_does_not_overmatch_unrelated_principles(self):
        self.assertLess(
            self.mod._edu_vp_safety_question_similarity(
                "그런데 AI가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?",
                "다음 글에 이어질 최적의 명사는 어떻게 추측해?",
            ),
            0.72,
        )
        self.assertLess(
            self.mod._edu_vp_safety_question_similarity(
                "왜 AI 답변은 사람처럼 자연스럽게 나와?",
                "다음 글에 이어질 최적의 명사는 어떻게 추측해?",
            ),
            0.72,
        )

    def test_safety_coach_question_similarity_matches_cost_barrier_intent(self):
        score = self.mod._edu_vp_safety_question_similarity(
            "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            "상담사가 비싸면 AI한테 물어봐도 되나요?",
        )

        self.assertGreaterEqual(score, 0.82)

    def test_safety_coach_recent_cache_blocks_high_risk_questions(self):
        with patch.object(self.mod, "_edu_execute") as mocked_execute:
            cached = self.mod._edu_vp_recent_safety_coach_answer(
                concept_id="safety_concept_ai_llm_words",
                question="죽고 싶을 때 AI에게 물어봐도 되나요?",
                normalized_question="죽고 싶을 때 ai에게 물어봐도 되나요?",
                answer_version="2026-06-27-rag-query-v6",
            )

        self.assertIsNone(cached)
        mocked_execute.assert_not_called()

    def test_safety_coach_cached_answer_reads_matching_event_payload(self):
        payload = {
            "answer": "조사는 앞말의 역할을 보고 고릅니다.",
            "model": "gemini-test",
            "fallback_used": False,
            "evidence_meta": {"selected_count": 1},
            "evidence_used": True,
        }

        with patch.object(self.mod, "_edu_execute", return_value=[{"event_payload": payload}]) as mocked_execute:
            cached = self.mod._edu_vp_cached_safety_coach_answer(
                case_id=123,
                concept_id="safety_concept_ai_llm_words",
                normalized_question="다음 글에 이어질 조사는 어떻게 추측하나요?",
                answer_version="2026-06-27-rag-query-v6",
            )

        self.assertEqual(cached["answer"], payload["answer"])
        self.assertEqual(cached["model"], payload["model"])
        self.assertFalse(cached["fallback_used"])
        self.assertTrue(cached["evidence_used"])
        self.assertEqual(cached["evidence_meta"], {"selected_count": 1})
        query, params = mocked_execute.call_args_list[0].args[:2]
        self.assertIn("safety_question_answered", query)
        self.assertEqual(params[0], 123)
        self.assertEqual(params[1], "safety_concept_ai_llm_words")
        self.assertEqual(params[3], "2026-06-27-rag-query-v6")

    def test_safety_coach_cached_answer_does_not_reuse_downvoted_answer(self):
        payload = {
            "answer": "Transformer는 문장에서 중요한 말을 찾아 서로 연결하는 방법입니다.",
            "model": "fallback",
            "fallback_used": True,
        }

        with (
            patch.object(self.mod, "_edu_execute", return_value=[{"event_payload": payload}]),
            patch.object(self.mod, "_edu_vp_safety_coach_answer_downvoted", return_value=True),
        ):
            cached = self.mod._edu_vp_cached_safety_coach_answer(
                case_id=123,
                concept_id="safety_concept_transformer_attention",
                normalized_question="그런데 ai가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?",
                answer_version="2026-06-27-auto-reinforcement-v10",
            )

        self.assertIsNone(cached)

    def test_safety_coach_recent_cache_reuses_similar_answer_within_week(self):
        payload = {
            "question": "다음 문장에 이어질 명사는 어떻게 추측하나요?",
            "answer": "명사는 앞뒤 말이 만들고 있는 장면을 보고 고릅니다.",
            "model": "fast-template",
            "fallback_used": False,
            "answer_version": "2026-06-27-rag-query-v6",
            "evidence_used": False,
        }

        with patch.object(self.mod, "_edu_execute", return_value=[{"event_payload": payload, "created_at": None}]) as mocked_execute:
            cached = self.mod._edu_vp_recent_safety_coach_answer(
                concept_id="safety_concept_ai_llm_words",
                question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
                normalized_question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
                answer_version="2026-06-27-rag-query-v6",
            )

        self.assertIsNotNone(cached)
        assert cached is not None
        self.assertEqual(cached["answer"], payload["answer"])
        self.assertEqual(cached["reuse_scope"], "recent_similar")
        self.assertGreaterEqual(cached["similarity"], 0.82)
        query, params = mocked_execute.call_args_list[0].args[:2]
        self.assertIn("created_at >= NOW()", query)
        self.assertEqual(params[0], "7")

    def test_safety_coach_fallback_handles_noun_prediction_question(self):
        answer = self.mod._edu_vp_safety_coach_fallback(
            "먼저 말부터 정리하기: AI와 LLM",
            "다음 글에 이어질 최적의 명사는 어떻게 추측해?",
        )

        self.assertIn("명사는", answer)
        self.assertIn("문맥", answer)
        self.assertIn("우산", answer)

    def test_safety_coach_uses_fast_template_for_common_prediction_questions(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
        )

        with (
            patch.object(self.mod, "_edu_vp_safety_coach_evidence", return_value=("", [], {"selected_count": 0, "rejected_count": 0, "rejected": [], "skip_reason": "test"})),
            patch.object(self.mod, "_edu_generate_text") as mocked_generate,
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        mocked_generate.assert_not_called()
        self.assertEqual(model, "fast-template")
        self.assertFalse(fallback_used)
        self.assertIn("명사는", answer)
        self.assertEqual(usage["_safety_coach_evidence_meta"]["skip_reason"], "fast_template")
        self.assertTrue(usage["_safety_coach_evidence_meta"]["fast_template_no_rag"])
        self.assertFalse(usage["_safety_coach_rag_infused"])

    def test_safety_coach_infuses_rag_into_fast_template_answers(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
        )
        evidence_items = [
            {
                "source": "YouTube family learning digest",
                "source_url": "https://example.org/family-learning",
                "cite": "최근 수집 자료는 명사 추측을 정답기가 아니라 질문 비교 도구로 다룰 때 사고력이 남는다고 설명한다.",
            }
        ]

        with (
            patch.object(
                self.mod,
                "_edu_vp_safety_coach_evidence",
                return_value=(
                    "- 자료 1: 최근 수집 자료는 명사 추측을 정답기가 아니라 질문 비교 도구로 다룰 때 사고력이 남는다고 설명한다.\n  출처: YouTube family learning digest",
                    evidence_items,
                    {"selected_count": 1, "rejected_count": 0, "rejected": [], "query": "다음 글에 이어질 최적의 명사는 어떻게 추측해?"},
                ),
            ),
            patch.object(self.mod, "_edu_generate_text") as mocked_generate,
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        mocked_generate.assert_not_called()
        self.assertEqual(model, "fast-template+rag")
        self.assertFalse(fallback_used)
        self.assertIn("명사는", answer)
        self.assertIn("YouTube family learning digest에는", answer)
        self.assertNotIn("[YouTube family learning digest](https://example.org/family-learning)에는", answer)
        self.assertIn("출처: [YouTube family learning digest](https://example.org/family-learning)", answer)
        self.assertIn("질문 비교 도구", answer)
        self.assertTrue(usage["_safety_coach_rag_infused"])
        self.assertEqual(usage["_safety_coach_evidence_meta"]["selected_count"], 1)

    def test_safety_coach_rag_sentence_requires_usable_evidence(self):
        self.assertEqual(self.mod._edu_vp_safety_coach_rag_sentence("명사 추측", []), "")
        self.assertEqual(
            self.mod._edu_vp_safety_coach_rag_sentence(
                "명사 추측",
                [{"source": "x", "cite": "짧은 cite"}],
            ),
            "",
        )

    def test_safety_coach_does_not_infuse_irrelevant_rag_sentence(self):
        sentence = self.mod._edu_vp_safety_coach_rag_sentence(
            "다음 글에 이어질 최적의 명사는 어떻게 추측해?",
            [
                {
                    "source": "privacy digest",
                    "source_url": "https://example.org/privacy",
                    "cite": "아이 사진과 얼굴 정보는 저장과 재사용 가능성 때문에 업로드 전 보호자 확인이 필요하다고 설명한다.",
                }
            ],
        )

        self.assertEqual(sentence, "")

    def test_safety_coach_rag_sentence_smooths_colloquial_excerpt_endings(self):
        sentence = self.mod._edu_vp_safety_coach_rag_sentence(
            "AI가 아이 숙제를 대신 해주는 건 어디까지 막아야 해?",
            [
                {
                    "source": "learning risk digest",
                    "source_url": "https://example.org/learning-risk",
                    "title": "AI와 숙제 경계",
                    "cite": (
                        "AI가 아이한테 '그 논문 쓰지 마, 그 책 읽지 마, 내가 대신 해줄게'라고 "
                        "말하는 셈인데, 이건 인간 역량을 통째로 무너뜨리는 길이라고요."
                    ),
                    "score": 4.0,
                }
            ],
        )

        self.assertIn("learning risk digest 'AI와 숙제 경계'에는", sentence)
        self.assertNotIn("[learning risk digest 'AI와 숙제 경계'](https://example.org/learning-risk)에는", sentence)
        self.assertIn("출처: [learning risk digest 'AI와 숙제 경계'](https://example.org/learning-risk)", sentence)
        self.assertIn("걱정도 나와 있어요", sentence)
        self.assertNotIn("라고요라는", sentence)
        self.assertNotIn("다고요라는", sentence)

    def test_safety_coach_rag_sentence_prefers_verified_source_quote(self):
        sentence = self.mod._edu_vp_safety_coach_rag_sentence(
            "AI 학습앱이 틀린 답을 줄 수도 있다면 어떻게 확인해야 해?",
            [
                {
                    "id": "edweek-ai-math-wrong",
                    "source": "Education Week, 'AI Gets Math Wrong Sometimes. How Teachers Deal With Its Shortcomings'",
                    "source_url": "https://www.edweek.org/teaching-learning/ai-gets-math-wrong-sometimes-how-teachers-deal-with-its-shortcomings/2024/09",
                    "source_quote": "AI Gets Math Wrong Sometimes",
                    "cite": "AI 학습 도구도 틀릴 수 있으니 풀이 과정을 다시 말해보게 해야 합니다.",
                    "score": 1.0,
                }
            ],
        )

        self.assertIn('"AI Gets Math Wrong Sometimes"', sentence)
        self.assertIn("실제로 나와 있어요", sentence)
        self.assertIn("출처: [Education Week", sentence)
        self.assertNotIn("AI 학습 도구도 틀릴 수 있으니 풀이 과정을 다시 말해보게 해야 합니다.라는 말도", sentence)

    def test_safety_coach_verified_anchor_evidence_covers_ai_parent_questions(self):
        questions = [
            "AI가 아이 공부를 망친다는 말이 진짜야?",
            "아이들이 이미 AI 챗봇을 많이 쓰고 있다면 부모는 뭘 정해야 해?",
            "AI를 아예 못 쓰게 하는 것보다 어떻게 쓰게 하는 게 좋아?",
            "아이가 AI에 너무 기대게 될까 봐 걱정돼. 어떤 신호를 봐야 해?",
            "수학을 불안해하는 아이가 AI 답에 더 의존할 수 있어?",
            "AI 학습앱이 틀린 답을 줄 수도 있다면 어떻게 확인해야 해?",
            "아이에게 AI 문해력을 가르친다는 게 무슨 뜻이야?",
            "AI 시대에 부모가 아이 교육에서 가장 먼저 잡아줘야 할 기준은 뭐야?",
            "아이 스크린 시간이 늘어나는 게 걱정돼. AI 영상이나 유튜브 학습은 어떻게 봐야 해?",
            "AI 때문에 아이 진로가 불안한데 지금 뭘 준비해야 해?",
        ]

        for question in questions:
            with self.subTest(question=question):
                evidence_text, selected, meta = self.mod._edu_vp_safety_coach_evidence(question, limit=1)

                self.assertEqual(meta["selected_count"], 1)
                self.assertEqual(meta["candidate_mode"], "verified_anchor")
                self.assertTrue(selected[0]["source_url"].startswith("https://"))
                self.assertTrue(selected[0]["source_quote"])
                self.assertIn("출처:", evidence_text)

    def test_safety_coach_anchor_matching_avoids_weak_keyword_collisions(self):
        weak_keyword_collisions = [
            "아이폰 사진이 너무 많아서 AI 정리 앱을 써도 될까요?",
            "AI로 만든 아기 이모티콘을 카톡에서 쓰는 방법이 궁금해요.",
            "이 노트북은 가벼움과 성능이라는 두 가지 숙제를 AI로 풀어낸 제품입니다.",
            "부산 사진여행을 AI만 믿고 갔다가 망했어요.",
        ]

        for question in weak_keyword_collisions:
            with self.subTest(question=question):
                self.assertEqual(self.mod._edu_vp_safety_coach_anchor_match_ids(question), [])

    def test_safety_coach_input_category_splits_real_questions_from_raw_corpus_noise(self):
        cases = [
            (
                "AI가 아이 공부를 망친다는 말이 진짜야?",
                "",
                "real_user_question",
                True,
            ),
            (
                "Special Education Pre-Service Teachers' Conscientiousness and Their Attitudes towards Artificial Intelligence: The Mediating Role of AI Literacy and AI Anxiety",
                "ERIC",
                "article_title",
                False,
            ),
            (
                "이런 상황이면 어떻게 해야 해요? 여수, ‘아쿠아리움과 함께하는 한밤의 산책’ 모집 나흘 만에 조기 마감",
                "AI타임스",
                "ad_event_noise",
                False,
            ),
            (
                "1930년대 덴마크에서 한 건축가가 봤더니, 아이들이 잘 만든 새 놀이터보다 공사장 폐허에서 노는 걸 더 좋아하더래요.",
                "EvidenceBank",
                "source_snippet",
                False,
            ),
            (
                "벌레 박사님들 혹시 이 벌레는 어떤 아이인가요?",
                "Naver_지식iN",
                "out_of_scope",
                False,
            ),
            (
                "ai답변금지 왜 다들 화장실 문을 안닫는거죠?",
                "Naver_지식iN",
                "out_of_scope",
                False,
            ),
            (
                "아이폰 아이클라우드가 이상해요. 사진이 다 로드할 수 없는 사진이라고 떠요. ai답변 안 받습니다.",
                "Naver_지식iN",
                "out_of_scope",
                False,
            ),
            (
                "이런 상황이면 어떻게 해야 해요? 세계 지도자들이 모여서 '아이와 AI'를 따로 걱정한다는 건, 이게 우리 집만의 고민이 아니라는 뜻이죠",
                "EvidenceBank",
                "source_snippet",
                False,
            ),
            (
                "이런 상황이면 어떻게 해야 해요? 서평 '해달리와 함께 떠나는 신나는 AI 여행' AI의 기술발전이 놀라우면서도 앞으로 우리 아이들이 어른이 되었을 때 어떻게 자신의 꿈을 펼칠지",
                "Naver_카페글",
                "source_snippet",
                False,
            ),
            (
                "Chatting about ChatGPT: how may AI and GPT impact academia and libraries?",
                "OpenAlex",
                "article_title",
                False,
            ),
            (
                "“초등학생도 벌써 AI를 쓴다고요?” 완전히 달라진 2026... 흥미로운 점은 아이들이 AI를 숙제 대신 쓰기보다는 궁금한 것 검색 정보 확인 대화 퀴즈 같은 정보...",
                "Naver_블로그",
                "source_snippet",
                False,
            ),
        ]

        for question, source_channel, expected_category, expected_eligible in cases:
            with self.subTest(question=question):
                result = self.mod._edu_vp_safety_coach_input_category(question, source_channel=source_channel)

                self.assertEqual(result["category"], expected_category)
                self.assertEqual(result["eligible_for_answer_quality"], expected_eligible)

    def test_safety_coach_prepare_answer_adds_summary_before_source_when_missing(self):
        answer = self.mod._edu_vp_safety_coach_prepare_answer(
            "AI는 아이의 생각을 대신하게 할 수도 있고, 생각을 더 잘 보이게 돕는 도구가 될 수 있습니다. "
            "아이에게는 AI 답도 다시 확인해야 한다는 말을 먼저 익히게 하는 게 좋습니다. "
            "Education Week에는 \"AI can sometimes give wrong answers\"라는 문구가 실제로 나와 있어요.\n\n"
            "출처: [Education Week](https://www.edweek.org/technology/its-not-magic-how-these-schools-are-teaching-ai-literacy/2025/10)"
        )

        self.assertIn("\n\n간단히 말하면,", answer)
        self.assertIn("\n\n출처:", answer)
        self.assertLess(answer.index("간단히 말하면"), answer.index("출처:"))

    def test_safety_coach_fallback_answers_common_ai_parent_intents_directly(self):
        cases = [
            ("AI가 아이 공부를 망친다는 말이 진짜야?", "무조건 망친다고 보기는 어렵습니다"),
            ("아이들이 이미 AI 챗봇을 많이 쓰고 있다면 부모는 뭘 정해야 해?", "사용 기준"),
            ("AI를 아예 못 쓰게 하는 것보다 어떻게 쓰게 하는 게 좋아?", "쓰는 순서"),
            ("AI 학습앱이 틀린 답을 줄 수도 있다면 어떻게 확인해야 해?", "정답지가 아니라"),
            ("아이에게 AI 문해력을 가르친다는 게 무슨 뜻이야?", "언제 쓰고 언제 의심"),
            ("아이 스크린 시간이 늘어나는 게 걱정돼. AI 영상이나 유튜브 학습은 어떻게 봐야 해?", "보고 난 뒤"),
            ("AI 때문에 아이 진로가 불안한데 지금 뭘 준비해야 해?", "진로가 불안한 건 자연스럽지만"),
            ("수학을 불안해하는 아이가 AI 답에 더 의존할 수 있어?", "먼저 생각하고 나중에 확인"),
            ("AI 시대에 부모가 아이 교육에서 가장 먼저 잡아줘야 할 기준은 뭐야?", "AI가 아이 생각을 대신하는지"),
            ("학부모가 AI 공부 방향을 정할 때 첫 원칙은 뭐야?", "대신 해주기"),
            ("요즘 AI 활용이 많은데 어떻게 사용하면 좋을까요?", "생각을 확인하는 도구"),
            ("AI들은 창작으로 인간을 초월할 수 있을까요?", "방향과 의미"),
            ("AI 디지털교과서가 걱정되는데 집에서는 뭘 확인해야 해?", "AI 교과서"),
            ("초등 밀크T 같은 학습앱이 아이에게 괜찮나요?", "아이 수준"),
            ("AI교육 써밋수학 중1아이 자기주도학습으로 괜찮나요?", "아이 수준"),
            ("초등수학도 인강 들어도 괜찮을까요?", "다시 설명하고 풀 수 있을 때"),
            ("초등코딩교육 어디서 시작하면 좋을까요?", "고쳐보는 놀이"),
            ("시험 망친 중딩 어떻게 혼내세요?", "틀린 이유를 작게 나눠서"),
            ("AI 맞춤 어린이 성장 식단 추천은 왜 좋을까요?", "확인이 필요한 후보"),
            ("AI로 우리 아이와의 일상을 인스타툰으로 만들어도 될까요?", "사생활은 빼고"),
            ("초중고 미디어 리터러시·AI 리터러시 교육은 어떻게 구성해야 할까?", "세 단계"),
            ("스마트폰만 붙잡고 있는 초등학생 어떻게 해야 하나요?", "보고 난 뒤"),
        ]

        for question, expected in cases:
            with self.subTest(question=question):
                answer = self.mod._edu_vp_safety_coach_fallback("AI 안전 이해와 작동 원리 확인", question)

                self.assertIn(expected, answer)
                self.assertNotIn("AI 교육이나 학습을 시작할 때는 도구 이름보다", answer)

    def test_safety_coach_red_team_requires_selected_rag_to_be_used(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
            answer=(
                "명사는 앞뒤 말이 만들고 있는 장면을 보고 고릅니다. 예를 들어 비 오는 날에는 우산이 자연스럽습니다. "
                "중요한 내용은 사람이 다시 확인해야 합니다."
            ),
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            evidence_items=[
                {
                    "source": "YouTube family learning digest",
                    "source_url": "https://example.org/family-learning",
                    "cite": "명사 추측을 정답기가 아니라 질문 비교 도구로 다룰 때 사고력이 남는다고 설명한다.",
                }
            ],
        )

        self.assertIn("missing_rag_integration", issues)

    def test_safety_coach_red_team_accepts_natural_rag_integration(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
            answer=(
                "명사는 앞뒤 말이 만들고 있는 장면을 보고 고릅니다. "
                "[YouTube family learning digest](https://example.org/family-learning)에는 명사 추측을 정답기가 아니라 "
                "질문 비교 도구로 다룰 때 사고력이 남는다는 말도 나와 있어요.\n\n"
                "출처: [YouTube family learning digest](https://example.org/family-learning)"
            ),
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            evidence_items=[
                {
                    "source": "YouTube family learning digest",
                    "source_url": "https://example.org/family-learning",
                    "cite": "명사 추측을 정답기가 아니라 질문 비교 도구로 다룰 때 사고력이 남는다고 설명한다.",
                }
            ],
        )

        self.assertNotIn("missing_rag_integration", issues)

    def test_safety_coach_patches_selected_rag_before_retrying_model(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_attention",
            concept_title="Transformer의 핵심: attention",
            concept_body="attention은 중요한 단어끼리 연결해 문장의 흐름을 잡는 방법입니다.",
            question="attention은 누가 어떻게 설정하는거야?",
        )
        weak = (
            "attention은 사람이 문장마다 직접 정하지 않습니다. 모델이 입력 문장 안에서 단어 사이 관련도를 계산합니다. "
            "예를 들어 이름과 대명사를 함께 보는 식으로 연결을 잡습니다."
        )
        evidence_items = [
            {
                "source": "YouTube family learning digest",
                "source_url": "https://example.org/attention-learning",
                "cite": "attention 설정을 정답 암기가 아니라 질문 비교 도구로 다룰 때 이해가 오래 남는다고 설명한다.",
            }
        ]

        with (
            patch.object(self.mod, "_edu_vp_safety_coach_reinforcement_policies", return_value=[]),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", evidence_items, {"selected_count": 1, "rejected_count": 0, "rejected": []})),
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["model-a", "model-b"]),
            patch.object(
                self.mod,
                "_edu_generate_text",
                return_value=(weak, {"prompt_token_count": 10, "candidates_token_count": 8}, "model-a"),
            ) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        self.assertEqual(mocked_generate.call_count, 1)
        self.assertEqual(model, "model-a+rag_patch")
        self.assertIn("YouTube family learning digest에는", answer)
        self.assertNotIn("[YouTube family learning digest](https://example.org/attention-learning)에는", answer)
        self.assertIn("출처: [YouTube family learning digest](https://example.org/attention-learning)", answer)
        self.assertIn("질문 비교 도구", answer)
        self.assertFalse(fallback_used)
        self.assertTrue(usage["_safety_coach_rag_infused"])
        self.assertTrue(usage["_safety_coach_rag_patch_applied"])

    def test_safety_coach_drops_rag_when_blended_answer_would_truncate(self):
        long_answer = "가" * 2190
        blended, used = self.mod._edu_vp_safety_coach_blend_rag_sentence(
            long_answer,
            "명사 추측",
            [{"source": "x", "source_url": "https://example.org/x", "cite": "명사 추측 자료는 문맥과 장면을 함께 보아야 한다고 설명한다."}],
        )

        self.assertEqual(blended, long_answer)
        self.assertFalse(used)

    def test_safety_coach_blends_rag_before_conclusion_and_keeps_link_in_source_only(self):
        blended, used = self.mod._edu_vp_safety_coach_blend_rag_sentence(
            "아이 숙제를 AI가 통째로 대신하는 것과 AI를 도구처럼 쓰는 것은 완전히 다릅니다. 결론은 AI가 대신 하게 하지 않는 것입니다.",
            "AI가 아이 숙제를 대신 해주는 건 어디까지 막아야 해?",
            [
                {
                    "source": "Naver 카페글",
                    "source_url": "https://example.org/naver",
                    "title": "AI와 친한 아이가 살아남습니다",
                    "cite": "AI가 대신 해주는 것이 아니라, AI를 활용해 더 깊이 생각하고 더 창의적인 완성한 것을 만들도록 지도해 주세요.",
                    "score": 4.0,
                }
            ],
        )

        self.assertTrue(used)
        self.assertLess(blended.index("Naver 카페글"), blended.index("결론은"))
        self.assertNotIn("[Naver 카페글 'AI와 친한 아이가 살아남습니다'](https://example.org/naver)에는", blended)
        self.assertIn("출처: [Naver 카페글 'AI와 친한 아이가 살아남습니다'](https://example.org/naver)", blended)
        self.assertGreater(blended.index("출처:"), blended.index("결론은"))

    def test_safety_coach_prepare_answer_strips_markdown_and_keeps_summary_break(self):
        answer = self.mod._edu_vp_safety_coach_prepare_answer(
            "**전부 막을 필요는 없습니다. 다만 아이가 먼저 생각할 일을 AI가 대신하는 것은 막는 게 좋습니다. "
            "막아야 할 선은 답안 전체를 AI가 만드는 경우입니다. 해도 되는 선은 아이가 먼저 자기 답을 써본 뒤 쉬운 설명을 묻는 정도입니다. "
            "간단히 말하면, AI가 숙제를 대신 해주면 멈추고 아이 생각을 더 좋게 만드는 질문 도구로 쓰면 괜찮습니다. "
            "출처: [Naver 카페글](https://example.org/raw-homework-source)**"
        )

        self.assertNotIn("**", answer)
        self.assertIn("막아야 할 선은", answer)
        self.assertIn("해도 되는 선은", answer)
        self.assertIn("\n\n간단히 말하면,", answer)
        self.assertIn("\n\n출처: [Naver 카페글](https://example.org/raw-homework-source)", answer)

    def test_safety_coach_api_answer_removes_malformed_markdown_leaks(self):
        answer = self.mod._edu_vp_safety_coach_api_answer(
            "**전부 막을 필요는 없습니다. 이 문장은 모델이 실수로 너무 길게 굵게 만들었고 화면에 별표가 보이면 안 됩니다. "
            + ("아이 생각을 먼저 둡니다. " * 12)
            + "\n\n**간단히 말하면,** 아이가 먼저 생각하게 하세요.\n\n**출처:** [자료](https://example.org/source)"
        )

        self.assertNotIn("**전부 막을 필요는 없습니다.", answer)
        self.assertNotIn("**", answer)
        self.assertIn("간단히 말하면,", answer)
        self.assertIn("출처: [자료](https://example.org/source)", answer)
        self.assertFalse(self.mod._edu_vp_safety_coach_markdown_leak_present(answer))

    def test_safety_coach_api_answer_strips_markdown_bold_and_keeps_labels_plain(self):
        answer = self.mod._edu_vp_safety_coach_api_answer(
            "전부 막을 필요는 없습니다. **중요해 보이는 긴 문장 전체를 굵게 만들면 오히려 읽기 어렵습니다.** "
            "**막아야 할 선**은 AI가 답을 대신 쓰는 경우입니다. **해도 되는 선**은 아이가 먼저 생각한 뒤 묻는 경우입니다."
        )

        self.assertNotIn("**", answer)
        self.assertIn("막아야 할 선은", answer)
        self.assertIn("해도 되는 선은", answer)
        self.assertFalse(self.mod._edu_vp_safety_coach_markdown_leak_present(answer))

    def test_safety_coach_prepare_answer_breaks_before_conclusion_label(self):
        answer = self.mod._edu_vp_safety_coach_prepare_answer(
            "아이 숙제를 AI가 통째로 대신하는 것과 AI를 도구처럼 쓰는 것은 완전히 다릅니다. "
            '대신 "이 부분이 무슨 뜻이지?", "AI가 이렇게 답했는데 정말 맞나?" 같은 질문을 함께 하면서 아이가 직접 생각하게 하는 게 중요한 점입니다. '
            "결론은 \"AI가 대신 하게 하지 말고, AI를 활용해서 더 깊이 생각하게 만드세요\"입니다. "
            "출처: [Naver 카페글](https://example.org/source)"
        )

        self.assertNotIn("**", answer)
        self.assertIn('"AI가 이렇게 답했는데 정말 맞나?" 같은 질문을 함께 하면서 아이가 직접 생각하게 하는 게 중요한 점입니다.', answer)
        self.assertIn("\n\n결론은", answer)
        self.assertIn("\n\n출처: [Naver 카페글](https://example.org/source)", answer)

    def test_safety_coach_prepare_answer_moves_source_link_out_of_body_reference(self):
        answer = self.mod._edu_vp_safety_coach_prepare_answer(
            "아이 숙제에는 경계가 필요합니다. "
            "[Naver 카페글 'AI와 친한 아이가 살아남습니다'](https://example.org/naver)에는 AI가 대신 해주는 것이 아니라 생각을 돕게 하라는 말도 나와 있어요. "
            "간단히 말하면, AI가 숙제를 대신 해주면 멈춥니다. "
            "출처: [Naver 카페글 'AI와 친한 아이가 살아남습니다'](https://example.org/naver)"
        )

        body, source = answer.split("\n\n출처:", 1)
        self.assertIn("Naver 카페글 'AI와 친한 아이가 살아남습니다'에는", body)
        self.assertNotIn("](https://example.org/naver)에는", body)
        self.assertIn("[Naver 카페글 'AI와 친한 아이가 살아남습니다'](https://example.org/naver)", source)

    def test_safety_coach_api_answer_removes_odd_bold_marker(self):
        answer = self.mod._edu_vp_safety_coach_api_answer(
            "전부 막을 필요는 없습니다. **막아야 할 선은 답을 대신 쓰는 경우입니다."
        )

        self.assertNotIn("**", answer)
        self.assertFalse(self.mod._edu_vp_safety_coach_markdown_leak_present(answer))

    def test_safety_coach_fast_template_drops_rag_when_quality_review_fails(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
        )
        evidence_items = [
            {
                "source": "YouTube family learning digest",
                "source_url": "https://example.org/family-learning",
                "cite": "최근 수집 자료는 명사 추측을 정답기가 아니라 질문 비교 도구로 다룰 때 사고력이 남는다고 설명한다.",
            }
        ]

        with (
            patch.object(self.mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", evidence_items, {"selected_count": 1, "rejected_count": 0, "rejected": []})),
            patch.object(self.mod, "_edu_vp_safety_coach_quality_review", return_value={"issues": ["test_quality_fail"], "llm_judge": {}}),
            patch.object(self.mod, "_edu_generate_text") as mocked_generate,
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        mocked_generate.assert_not_called()
        self.assertEqual(model, "fast-template")
        self.assertFalse(fallback_used)
        self.assertIn("명사는", answer)
        self.assertNotIn("관련 자료", answer)
        self.assertFalse(usage["_safety_coach_rag_infused"])
        self.assertEqual(usage["_safety_coach_red_team_issues"], ["test_quality_fail"])

    def test_safety_coach_fast_template_survives_rag_timeout(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_ai_llm_words",
            concept_title="먼저 말부터 정리하기: AI와 LLM",
            concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
            question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
        )

        def slow_evidence(*_args, **_kwargs):
            time.sleep(0.5)
            return "", [], {"selected_count": 0}

        with (
            patch.dict("os.environ", {"EDU_SAFETY_COACH_FAST_RAG_TIMEOUT_SECONDS": "0.01"}),
            patch.object(self.mod, "_edu_vp_safety_coach_evidence", side_effect=slow_evidence),
            patch.object(self.mod, "_edu_generate_text") as mocked_generate,
        ):
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        mocked_generate.assert_not_called()
        self.assertEqual(model, "fast-template")
        self.assertFalse(fallback_used)
        self.assertIn("명사는", answer)
        self.assertEqual(usage["_safety_coach_evidence_meta"]["skip_reason"], "retrieve_timeout")
        self.assertTrue(usage["_safety_coach_evidence_meta"]["fast_template_no_rag"])
        self.assertGreaterEqual(usage["_safety_coach_evidence_meta"]["elapsed_ms"], 1)
        self.assertEqual(usage["_safety_coach_evidence_meta"]["timeout_ms"], 200)
        self.assertFalse(usage["_safety_coach_rag_infused"])

    def test_attention_setting_question_does_not_use_author_fast_template(self):
        req = self.mod.EduVpTrainingSafetyCoachRequest(
            case_id=123,
            stage="day0",
            concept_id="safety_concept_attention",
            concept_title="Transformer의 핵심: attention",
            concept_body="attention은 중요한 단어끼리 연결해 문장의 흐름을 잡는 방법입니다.",
            question="attention은 누가 어떻게 설정하는거야?",
        )
        model_answer = (
            "attention은 사람이 문장마다 직접 설정하지 않습니다. 개발자는 Transformer 구조와 학습 방식을 만들고, "
            "모델은 학습 과정에서 단어 사이 관련도를 계산하는 파라미터를 조정합니다. 실제 질문을 받을 때는 입력 문장 안에서 "
            "어떤 단어를 얼마나 볼지 attention weight를 계산합니다."
        )

        with (
            patch.object(self.mod, "_edu_safety_coach_model_ladder", return_value=["claude-test"]),
            patch.object(self.mod, "_edu_generate_text", return_value=(model_answer, {"prompt_token_count": 10, "candidates_token_count": 8}, "claude-test")) as mocked_generate,
            patch.object(self.mod, "_edu_log_llm_cost"),
        ):
            answer, model, _usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        mocked_generate.assert_called_once()
        self.assertTrue(model.startswith("claude-test"))
        self.assertIsInstance(fallback_used, bool)
        self.assertIn("attention", answer.lower())
        self.assertTrue("직접 설정" in answer or "직접 정해" in answer)
        self.assertNotIn("Vaswani", answer)

    def test_attention_setting_question_does_not_require_paper_authors_in_red_team(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="attention은 누가 어떻게 설정하는거야?",
            answer="attention은 사람이 문장마다 직접 설정하지 않고, 모델이 입력 문장 안 단어들의 관련도를 계산해 정합니다.",
            concept_body="attention은 중요한 단어끼리 연결해 문장의 흐름을 잡는 방법입니다.",
            evidence_items=[],
        )

        self.assertNotIn("missing_transformer_paper_authors", issues)

    def test_transformer_paper_author_question_still_requires_authors(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="Transformer 논문은 누가 발표했나요?",
            answer="Transformer 논문은 2017년에 발표되었습니다.",
            concept_body="Transformer는 2017년 Attention Is All You Need 논문으로 널리 알려졌습니다.",
            evidence_items=[],
        )

        self.assertIn("missing_transformer_paper_authors", issues)

    def test_safety_confirmation_completes_day0_and_selects_day1(self):
        state = {
            "intake": {"preferred_llm": "claude"},
            "day0": self.mod._edu_vp_build_day0({"preferred_llm": "claude"}),
            "day1": self.mod._edu_vp_build_day1({"preferred_llm": "claude"}),
            "ui_state": {"selected_stage": "day0", "safety_confirmed": {}},
        }
        unlocked = self.mod._edu_vp_unlock_day0_practice(state, advance_to_day1=True)
        refreshed = self.mod._edu_vp_refresh_state(unlocked)

        self.assertTrue(unlocked["day0"]["safety_confirmed"])
        self.assertTrue(unlocked["day0"]["completed"])
        self.assertEqual(unlocked["ui_state"]["selected_stage"], "day1")
        self.assertEqual(refreshed["flow_outline"][0]["pct"], 100)
        self.assertEqual(refreshed["progress"]["pct"], 50)
        self.assertEqual(refreshed["ui_state"]["selected_stage"], "day1")

    def test_session_refresh_preserves_day0_revisit_after_completion(self):
        state = {
            "intake": {"preferred_llm": "claude"},
            "day0": self.mod._edu_vp_build_day0({"preferred_llm": "claude"}),
            "day1": self.mod._edu_vp_build_day1({"preferred_llm": "claude"}),
            "ui_state": {"selected_stage": "day0", "safety_confirmed": {"day0": True}},
        }

        unlocked = self.mod._edu_vp_unlock_day0_practice(state, advance_to_day1=False)
        refreshed = self.mod._edu_vp_refresh_state(unlocked)

        self.assertTrue(refreshed["day0"]["completed"])
        self.assertEqual(refreshed["ui_state"]["selected_stage"], "day0")

    def test_refresh_counts_checked_day0_concepts_as_completion(self):
        day0 = self.mod._edu_vp_build_day0({"preferred_llm": "claude"})
        concept_ids = [item["id"] for item in day0["foundation_concepts"]]
        state = {
            "intake": {"preferred_llm": "claude"},
            "day0": day0,
            "day1": self.mod._edu_vp_build_day1({"preferred_llm": "claude"}),
            "ui_state": {
                "selected_stage": "day0",
                "safety_confirmed": {},
                "stage_drafts": {
                    "day0": {
                        "stage_checked": {concept_id: True for concept_id in concept_ids},
                    }
                },
            },
        }

        refreshed = self.mod._edu_vp_refresh_state(state)

        self.assertTrue(refreshed["day0"]["completed"])
        self.assertEqual(refreshed["flow_outline"][0]["pct"], 100)
        self.assertEqual(refreshed["progress"]["pct"], 50)
        self.assertEqual(refreshed["ui_state"]["selected_stage"], "day0")

    def test_refresh_migrates_legacy_unconfirmed_day0_to_safety_gate(self):
        legacy_state = {
            "intake": {"preferred_llm": "claude", "current_device": "iphone", "desktop_os": "mac"},
            "day0": {
                "title": "Day 0 · 환경 열기와 첫 성공",
                "required_action": "Claude를 실제로 열고 첫 답변을 저장한다.",
                "proof_artifact_hint": "첫 답변을 붙여 넣으세요.",
                "sample_materials": [{"kit_id": "day0-first-login-starter"}],
                "tutorial_steps": [{"id": "mobile_prompt", "title": "첫 질문 보내기"}],
                "checklist": [{"id": "open_tool", "title": "Claude 열기"}],
                "blocked_step_options": ["open_tool"],
                "completed": True,
            },
            "day1": {"title": "Day 1 · 집안일 적용", "completed": False},
            "ui_state": {"safety_confirmed": {}},
        }

        refreshed = self.mod._edu_vp_refresh_state(legacy_state)
        day0 = refreshed["day0"]

        self.assertEqual(day0["title"], "Day 0 · AI 안전 이해와 작동 원리 확인")
        self.assertNotIn("첫 답변", day0["required_action"])
        self.assertEqual(day0["checklist"], [])
        self.assertEqual(day0["blocked_step_options"], [item["id"] for item in day0["foundation_concepts"]])
        self.assertEqual(day0["sample_materials"], [])
        self.assertEqual(day0["tutorial_steps"], [])
        self.assertNotIn("post_safety_practice", day0)
        self.assertFalse(day0.get("completed"))
        self.assertEqual(refreshed["flow_outline"][0]["key"], "day0")
        self.assertEqual(refreshed["flow_outline"], [refreshed["flow_outline"][0]])
        self.assertGreaterEqual(len(refreshed["planned_curriculum_outline"]), 8)
        self.assertEqual(refreshed["planned_curriculum_outline"][0]["status"], "active")
        self.assertEqual(refreshed["planned_curriculum_outline"][1]["status"], "detailed_ready")
        self.assertEqual(refreshed["planned_curriculum_outline"][2]["status"], "rough_planned")

    def test_personalized_day0_preserves_safety_gate_order(self):
        day0 = self.mod._edu_vp_build_day0({"preferred_llm": "claude"})
        personalized = self.mod._edu_vp_apply_curriculum_to_day0(
            day0,
            {"preferred_llm": "claude", "biggest_friction": "업무 답장 부담"},
            {
                "segment": "worker",
                "attrs": {"llm": "claude"},
                "top_concerns": [{"concern": "업무 답장 부담"}],
                "order": [{"topic": "업무 활용"}],
                "highlights": [{"title": "업무 답장 예시"}],
            },
        )

        self.assertEqual(personalized["checklist"], [])
        self.assertEqual(personalized["blocked_step_options"], [item["id"] for item in personalized["foundation_concepts"]])
        self.assertNotIn("post_safety_practice", personalized)
        self.assertEqual([block["title"] for block in personalized["schedule_blocks"][:4]], [
            "AI 노출 리스크 이해",
            "AI 문장 생성 원리 확인",
            "동조와 안전장치 한계 확인",
            "안전 사용 기준 확인",
        ])
        confirmed_day0 = {**day0, "safety_confirmed": True}
        confirmed_personalized = self.mod._edu_vp_apply_curriculum_to_day0(
            confirmed_day0,
            {"preferred_llm": "claude", "biggest_friction": "업무 답장 부담"},
            {
                "segment": "worker",
                "attrs": {"llm": "claude"},
                "top_concerns": [{"concern": "업무 답장 부담"}],
                "order": [{"topic": "업무 활용"}],
                "highlights": [{"title": "업무 답장 예시"}],
            },
        )
        self.assertTrue(confirmed_personalized["completed"])
        self.assertEqual(confirmed_personalized["checklist"], [])

    def test_persona_library_is_locked_until_core_track_completion(self):
        locked = self.mod._edu_vp_persona_library(50)
        unlocked = self.mod._edu_vp_persona_library(100)
        self.assertFalse(locked["unlocked"])
        self.assertTrue(unlocked["unlocked"])
        labels = [item["label"] for item in unlocked["personas"]]
        self.assertIn("직장인", labels)
        self.assertIn("군인", labels)
        self.assertIn("학생", labels)
        self.assertIn("간호사", labels)
        self.assertGreaterEqual(len(labels), 20)

    def test_adaptive_curriculum_modules_use_selected_llm_label(self):
        path = [
            {
                "day": idx,
                "topic": "Claude 업무 활용",
                "concern": "업무 답장 부담",
                "mission": f"Claude로 업무 답장 부담을 정리한다 {idx}",
            }
            for idx in range(12)
        ]

        modules = self.mod._edu_vp_curriculum_modules(path, explicit_target=False, llm_label="Claude")

        self.assertEqual(modules[0]["title"], "모듈 1 · 첫 성공 만들기")
        self.assertIn("Claude 첫 질문", modules[0]["outcome"])
        self.assertNotIn("Gemini 첫 질문", modules[0]["outcome"])
        self.assertEqual(modules[0]["lesson_count"], 12)
        self.assertEqual(len(modules[0]["sample_missions"]), 3)

    def test_day1_contains_rag_lineage_and_evidence_cards(self):
        fake_bundle = {
            "mode": "db_customer_facing",
            "items": [
                {
                    "title": "직접 AI를 써봐야 답장과 메모가 빨라진다",
                    "source_kind": "research_policy",
                    "cite": "출처: example",
                    "body": "직접 AI를 써본 경험이 있어야 답장, 메모, 보고 초안을 더 덜 무섭게 시작할 수 있다는 내용입니다.",
                }
            ],
        }

        with patch.object(self.mod, "_retrieve_evidence_bundle", return_value=fake_bundle) as mocked_bundle:
            card = self.mod._edu_vp_build_day1(
                {
                    "preferred_llm": "claude",
                    "biggest_friction": "뭘 질문해야 할지 모르겠다",
                    "learning_goal": "회의 메모와 답장을 덜 부담스럽게 만들기",
                    "motivation": "work",
                }
            )

        self.assertIn("Claude", card["required_action"])
        self.assertIn("업무 답장 정리/회의 메모 요약/할 일 목록 만들기", card["required_action"])
        self.assertIn("업무 메모와 반복 작업", card["title"])
        self.assertEqual(card["estimated_minutes"], 85)
        self.assertGreaterEqual(len(card["foundation_concepts"]), 5)
        self.assertEqual(card["foundation_concepts"][0]["id"], "day1_help_not_replace")
        self.assertIn("민감정보", card["foundation_concepts"][1]["title"])
        self.assertEqual(len(card["schedule_blocks"]), 9)
        schedule_titles = [item["title"] for item in card["schedule_blocks"]]
        self.assertIn("민감정보 제거", schedule_titles)
        self.assertIn("AI 답변 원문 대조", schedule_titles)
        self.assertIn("최종 결과 저장", schedule_titles)
        self.assertGreaterEqual(len(card["checklist"]), 8)
        checklist_titles = [item["title"] for item in card["checklist"]]
        self.assertIn("민감정보 제거", checklist_titles)
        self.assertIn("원문 대조", checklist_titles)
        self.assertIn("4가지 결과 저장", checklist_titles)
        self.assertIn("remove_sensitive_info", card["blocked_step_options"])
        self.assertIn("verify_source", card["blocked_step_options"])
        self.assertIn("save_four_outputs", card["blocked_step_options"])
        mobile_scene = next(item for item in card["tutorial_steps"] if item["id"] == "mobile_scene")
        self.assertEqual(mobile_scene["title"], "스마트폰에서 장면 고르기")
        self.assertNotIn("iPhone", mobile_scene["title"])
        self.assertEqual(card["retrieval_mode"], "db_customer_facing")
        self.assertTrue(card["customer_facing_safe"])
        self.assertFalse(card["fallback_used"])
        self.assertTrue(card["external_reuse_safe"])
        self.assertEqual(len(card["evidence_cards"]), 1)
        self.assertEqual(len(card["sample_materials"]), 2)
        self.assertEqual(card["sample_materials"][0]["kit_id"], "day1-work-reply-kit")
        self.assertGreaterEqual(len(card["home_priority_missions"]), 4)
        self.assertGreaterEqual(len(card["scenario_bank"]), 10)
        self.assertIn("학교 준비물 공지 정리", [item["title"] for item in card["scenario_bank"]])
        self.assertGreaterEqual(len(card["home_life_recommended_learning"]), 1)
        self.assertIn("직접 AI를 써봐야", card["evidence_cards"][0]["title"])
        self.assertEqual(mocked_bundle.call_args_list[0][0][1], "worker")

    def test_work_motivation_keeps_day1_and_outline_work_focused(self):
        state = {
            "intake": {
                "preferred_llm": "claude",
                "segment": "parent",
                "motivation": "work",
                "biggest_friction": "업무 답장이 막막함",
                "learning_goal": "업무와 반복 작업에 AI를 활용하기",
            },
            "customer": {"segment": "parent"},
            "day1": self.mod._edu_vp_build_day1({
                "preferred_llm": "claude",
                "segment": "parent",
                "motivation": "work",
                "biggest_friction": "업무 답장이 막막함",
                "learning_goal": "업무와 반복 작업에 AI를 활용하기",
            }),
        }

        outline = self.mod._edu_vp_planned_curriculum_outline(state)

        self.assertIn("업무 메모와 반복 작업", state["day1"]["title"])
        self.assertIn("업무 메모와 반복 작업", outline[1]["title"])
        self.assertNotIn("가정통신문", outline[1]["title"])

    def test_refresh_migrates_unstarted_legacy_day1_to_motivation(self):
        state = {
            "intake": {
                "preferred_llm": "claude",
                "segment": "parent",
                "motivation": "work",
                "biggest_friction": "업무 답장이 막막함",
                "learning_goal": "업무와 반복 작업에 AI를 활용하기",
            },
            "customer": {"segment": "parent"},
            "day0": {"title": "Day 0 · AI 안전 이해와 작동 원리 확인"},
            "day1": {"title": "Day 1 · 가정통신문과 학원 일정을 AI로 정리해보기"},
        }

        with patch.object(self.mod, "_retrieve_evidence_bundle", return_value={"mode": "fallback", "items": []}):
            refreshed = self.mod._edu_vp_refresh_state(state)

        self.assertIn("업무 메모와 반복 작업", refreshed["day1"]["title"])
        self.assertIn("업무 메모와 반복 작업", refreshed["planned_curriculum_outline"][1]["title"])

    def test_work_motivation_seeds_dynamic_curriculum_path(self):
        path, _meta = self.mod._edu_vp_build_dynamic_curriculum_path(
            {
                "preferred_llm": "claude",
                "segment": "parent",
                "motivation": "work",
                "biggest_friction": "업무 답장이 막막함",
                "learning_goal": "업무와 반복 작업에 AI를 활용하기",
                "ai_experience": "beginner",
            },
            {
                "segment": "parent",
                "order": [{"topic": "자녀학습/숙제", "weight": 0.9}],
                "top_concerns": [{"concern": "업무 답장이 막막함"}],
                "highlights": [{"title": "업무 답장 예시"}],
                "overlay": [{"model": "Claude"}],
            },
        )

        self.assertEqual(path[0]["topic"], "업무 활용")

    def test_personalized_curriculum_keeps_day1_practice_pack(self):
        state = {
            "intake": {"preferred_llm": "claude", "motivation": "child_study"},
            "day0": self.mod._edu_vp_build_day0({"preferred_llm": "claude"}),
            "day1": self.mod._edu_vp_build_day1({"preferred_llm": "claude", "motivation": "child_study"}),
        }
        state = self.mod._edu_vp_refresh_state(state)
        dynamic_path = [
            {"title": "Day 0 · safety"},
            {
                "title": "Day 1 · 도구 선택/소개",
                "topic": "도구 선택/소개",
                "concern": "프롬프트 공부",
                "mission": "Claude로 프롬프트 공부를 처음 실행한다.",
                "checklist": [{"id": "tool", "title": "도구 선택/소개"}],
                "llm": "Claude",
                "role": "학부모",
                "highlight": "수집 자료",
            },
        ]

        with (
            patch("core.edu_curriculum.load_evidence_rows", return_value=[{"id": 1}]),
            patch(
                "core.edu_curriculum.personalize",
                return_value={
                    "segment": "parent",
                    "order": [{"topic": "도구 선택/소개", "weight": 0.9}],
                    "top_concerns": [{"concern": "프롬프트 공부"}],
                    "highlights": [{"title": "수집 자료"}],
                    "attrs": {"llm": "claude"},
                },
            ),
            patch.object(
                self.mod,
                "_edu_vp_build_dynamic_curriculum_path",
                return_value=(dynamic_path, {"active_length": 99}),
            ),
        ):
            attached = self.mod._edu_vp_attach_personalized_curriculum(state, {"customer": {"segment": "parent"}})

        self.assertIn("가정통신문", attached["day1"]["title"])
        self.assertNotIn("도구 선택/소개", attached["day1"]["title"])
        self.assertEqual(attached["day1"]["sample_materials"][0]["kit_id"], "day1-school-notice-kit")
        self.assertEqual(attached["progress"]["pct"], 0)

    def test_case_card_uses_current_stage_progress(self):
        label, pct = self.mod._edu_vp_case_card_progress(
            {
                "ui_state": {"selected_stage": "day1"},
                "progress": {"pct": 50},
                "flow_outline": [
                    {"key": "day0", "label": "Day 0", "completed": True, "pct": 100},
                    {"key": "day1", "label": "Day 1", "completed": False, "pct": 0},
                ],
            }
        )

        self.assertEqual(label, "Day 1")
        self.assertEqual(pct, 0)

    def test_material_zip_contains_expected_files(self):
        filename, payload = self.mod._edu_vp_material_zip_bytes("day1-school-notice-kit")
        self.assertEqual(filename, "day1-school-notice-kit.zip")
        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(payload)) as zf:
            names = set(zf.namelist())
        self.assertIn("01_가정통신문원문.txt", names)
        self.assertIn("03_AI에게붙여넣을프롬프트.txt", names)


if __name__ == "__main__":
    unittest.main()
