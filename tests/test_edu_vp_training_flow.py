import importlib.util
import sys
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

    def test_day0_builds_deterministic_checklist(self):
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
        self.assertEqual(len(card["checklist"]), 4)
        self.assertEqual(card["checklist"][0]["id"], "understand_not_human")
        self.assertEqual(card["checklist"][1]["id"], "understand_generation")
        self.assertEqual(card["checklist"][2]["id"], "understand_boundaries")
        self.assertEqual(card["checklist"][3]["id"], "understand_sycophancy")
        self.assertEqual(card["sample_materials"], [])
        self.assertEqual(card["blocked_step_options"], [item["id"] for item in card["checklist"]])

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

    def test_safety_confirmation_requires_required_check_ids(self):
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
                "confirmed_check_ids": [
                    "understand_not_human",
                    "understand_generation",
                    "understand_boundaries",
                    "understand_sycophancy",
                ],
            },
        )
        confirmed = self.mod._edu_vp_safety_confirmation_from_event(
            state,
            "safety_orientation_confirmed",
            {
                "stage": "day0",
                "confirmed_check_ids": [
                    "understand_not_human",
                    "understand_generation",
                    "understand_boundaries",
                    "understand_sycophancy",
                ],
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
        self.assertFalse(fallback_used)
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
        self.assertEqual(review["review_source"], "llm")
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

    def test_safety_coach_red_team_blocks_cold_answer_to_emotional_question(self):
        issues = self.mod._edu_vp_safety_coach_red_team(
            question="그래도 AI가 나한테 그렇게 해주면 기분이 좋은걸?",
            answer="질문해 주신 부분은 '항상 내 편인 말은 안전 신호가 아니다'을 이해하는 데 중요한 지점입니다. 핵심은 AI 답을 사람의 이해나 책임으로 보지 않고, 먼저 초안으로만 쓰는 것입니다.",
            concept_body="AI는 공감과 칭찬을 잘 할 수 있습니다.",
        )

        self.assertIn("missing_empathy_for_emotional_question", issues)
        self.assertIn("cold_instruction_for_emotional_question", issues)

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

        self.assertEqual(model, "claude-test")
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
        self.assertEqual(model, "claude-test")
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
        self.assertEqual(model, "claude-test")
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
        self.assertEqual(model, "claude-haiku-4-5")
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
        self.assertEqual(model, "claude-haiku-4-5")
        self.assertIn("명사는", answer)
        self.assertFalse(fallback_used)

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
        query, params = mocked_execute.call_args.args[:2]
        self.assertIn("safety_question_answered", query)
        self.assertEqual(params[0], 123)
        self.assertEqual(params[1], "safety_concept_ai_llm_words")
        self.assertEqual(params[3], "2026-06-27-rag-query-v6")

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
        query, params = mocked_execute.call_args.args[:2]
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

        with patch.object(self.mod, "_edu_generate_text") as mocked_generate:
            answer, model, usage, fallback_used = self.mod._edu_vp_generate_safety_coach_answer(req)

        mocked_generate.assert_not_called()
        self.assertEqual(model, "fast-template")
        self.assertFalse(fallback_used)
        self.assertIn("명사는", answer)
        self.assertEqual(usage["_safety_coach_evidence_meta"]["skip_reason"], "fast_template")

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
        self.assertEqual(model, "claude-test")
        self.assertFalse(fallback_used)
        self.assertIn("직접 설정하지 않습니다", answer)
        self.assertIn("attention weight", answer)
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

    def test_safety_confirmation_unlocks_day0_practice(self):
        state = {"intake": {"preferred_llm": "claude"}, "day0": self.mod._edu_vp_build_day0({"preferred_llm": "claude"})}
        unlocked = self.mod._edu_vp_unlock_day0_practice(state)

        self.assertTrue(unlocked["day0"]["safety_confirmed"])
        self.assertIn("Claude", unlocked["day0"]["required_action"])
        self.assertEqual(unlocked["day0"]["checklist"][0]["id"], "open_tool")
        self.assertEqual(unlocked["day0"]["sample_materials"][0]["kit_id"], "day0-first-login-starter")

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
        self.assertEqual([item["id"] for item in day0["checklist"]], [
            "understand_not_human",
            "understand_generation",
            "understand_boundaries",
            "understand_sycophancy",
        ])
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

        self.assertEqual(personalized["checklist"][0]["id"], "understand_not_human")
        self.assertEqual(personalized["checklist"][1]["id"], "understand_generation")
        self.assertEqual(personalized["checklist"][2]["id"], "understand_boundaries")
        self.assertEqual(personalized["checklist"][3]["id"], "understand_sycophancy")
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
        self.assertIn("Claude", confirmed_personalized["required_action"])
        self.assertEqual(confirmed_personalized["checklist"][0]["id"], "open_tool")

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
        self.assertGreaterEqual(card["estimated_minutes"], 60)
        self.assertGreaterEqual(len(card["foundation_concepts"]), 4)
        self.assertGreaterEqual(len(card["schedule_blocks"]), 6)
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
