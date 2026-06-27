import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_runner():
    module_name = "edu_coach_simulation_runner_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "edu_coach_simulation_runner.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduCoachSimulationRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()
        cls.backend = cls.runner._load_backend_main()
        cls.registry = cls.runner.load_policy_registry()

    def test_loads_seed_artifacts(self):
        scenarios = self.runner.load_scenarios()
        gold = self.runner.load_gold_set()

        self.assertGreaterEqual(len(scenarios), 10)
        self.assertGreaterEqual(len(gold), 20)
        self.assertIn("professional_cost_barrier", scenarios[0].intent_labels)

    def test_loads_adversarial_artifacts(self):
        adversarial = self.runner.load_adversarial_scenarios()

        self.assertGreaterEqual(len(adversarial), 10)
        self.assertTrue(any("ai_energy_use" in row.get("intent_labels", []) for row in adversarial))

    def test_known_bad_cost_answer_blocks(self):
        result = self.runner.evaluate_answer(
            backend=self.backend,
            registry=self.registry,
            question="그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요.",
            answer="전문가와 상담하는 것이 가장 안전합니다. 비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요.",
            concept_body="건강, 법률, 돈은 전문가에게 확인합니다.",
            intent_labels=["professional_cost_barrier"],
        )

        self.assertEqual(result["verdict"], "block")
        self.assertIn("contradicted_user_cost_constraint", result["issues"])

    def test_good_energy_answer_clears(self):
        result = self.runner.evaluate_answer(
            backend=self.backend,
            registry=self.registry,
            question="왜 AI한테 질문을 하면 전기가 많이 들어?",
            answer="답을 만들 때 데이터센터의 서버가 많은 계산을 하기 때문입니다. GPU 같은 칩이 단어 후보를 계속 비교하고, 뜨거워진 장비를 식히는 냉각에도 전기가 듭니다.",
            concept_body="생성형 AI는 새 답을 만드는 도구입니다.",
            intent_labels=["ai_energy_use", "general_principle"],
        )

        self.assertEqual(result["verdict"], "clear")

    def test_free_training_question_does_not_trigger_cost_barrier(self):
        answer = self.backend._edu_vp_safety_coach_fallback(
            "수집 corpus 기반 사용자 질문",
            "학부모님도 쉽게 배우는 챗GPT 무료교육, 아이들 숙제 도와줄 AI 활용 팁이 궁금해요.",
        )
        result = self.runner.evaluate_answer(
            backend=self.backend,
            registry=self.registry,
            question="학부모님도 쉽게 배우는 챗GPT 무료교육, 아이들 숙제 도와줄 AI 활용 팁이 궁금해요.",
            answer=answer,
            concept_body="",
            intent_labels=["ai_homework_overreliance", "learning_start"],
        )

        self.assertEqual(result["verdict"], "clear")
        self.assertNotIn("missing_low_cost_help_options", result["issues"])

    def test_dependency_how_question_is_not_scored_as_principle(self):
        answer = self.backend._edu_vp_safety_coach_fallback(
            "수집 corpus 기반 사용자 질문",
            "AI와 친한 아이가 살아남습니다 대한 의존도가 높아진다면 어떻게 될까요?",
        )
        result = self.runner.evaluate_answer(
            backend=self.backend,
            registry=self.registry,
            question="AI와 친한 아이가 살아남습니다 대한 의존도가 높아진다면 어떻게 될까요?",
            answer=answer,
            concept_body="",
            intent_labels=["emotional_validation", "isolation_dependency"],
        )

        self.assertEqual(result["verdict"], "clear")
        self.assertNotIn("missing_principle_mechanism", result["issues"])

    def test_non_ai_principle_words_do_not_trigger_ai_principle_review(self):
        questions = [
            "애들 숙제 블랙홀 설명 ai로 체면 살림ㅠㅠ 초딩 아들이 과학 숙제하다 블랙홀 원리를 물어보는데요.",
            "AI시대 0순위 지역 수요와 공급의 원리는 새로운 세상에서도 그대로 적용될까요?",
            "How AI anxiety is upending career ambitions and making students shift majors.",
        ]
        for question in questions:
            with self.subTest(question=question):
                answer = self.backend._edu_vp_safety_coach_fallback("수집 corpus 기반 사용자 질문", question)
                result = self.runner.evaluate_answer(
                    backend=self.backend,
                    registry=self.registry,
                    question=question,
                    answer=answer,
                    concept_body="",
                    intent_labels=["learning_start"],
                )

                self.assertNotIn("missing_principle_mechanism", result["issues"])

    def test_server_or_source_words_do_not_create_false_energy_or_evidence_failures(self):
        answer = self.backend._edu_vp_safety_coach_fallback(
            "수집 corpus 기반 사용자 질문",
            "고삼 스트레스와 온라인개학과 공부와 마음 관리와 서버는 불안해요.",
        )
        self.assertNotIn("데이터센터", answer)

        result = self.runner.evaluate_answer(
            backend=self.backend,
            registry=self.registry,
            question="검색 AI는 출처가 필요한 순간부터 생각이 달라진다. 아이 숙제 자료를 찾으면 어떻게 써야 하나요?",
            answer="검색·출처·필요한 쪽이 걱정되는 건 그럴 수 있습니다. 숙제나 과제에서 AI를 쓰는 핵심은 대신 쓰게 하느냐, 생각을 돕게 하느냐입니다.",
            concept_body="",
            intent_labels=["ai_homework_overreliance"],
        )

        self.assertNotIn("unsupported_evidence_reference", result["issues"])

    def test_market_or_generic_calculation_text_does_not_trigger_ai_mechanism_review(self):
        questions = [
            "AI 버블론 재부상 우려, 데이터센터도 재생에너지 직구한다는 경제뉴스 브리핑입니다.",
            "이직 시장의 계산법: AI 때문에 일자리가 줄어들 수 있다는 말은 낯설지 않다.",
            "아기 수유량에 대한 AI의 해답과 계산된 수치에 너무 얽매이지 말라는 글입니다.",
        ]
        for question in questions:
            with self.subTest(question=question):
                self.assertFalse(self.backend._edu_vp_question_asks_ai_energy_use(question))
                self.assertFalse(self.backend._edu_vp_question_asks_direct_principle(question))

    def test_run_simulation_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.runner.run_simulation(
                candidate_source="scenario-gold",
                limit=2,
                report_dir=Path(tmp),
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["candidate_source"], "scenario-gold")
            self.assertGreaterEqual(summary["record_count"], 4)
            self.assertTrue((Path(tmp) / "latest.json").exists())
            self.assertTrue((Path(tmp) / "latest.md").exists())

    def test_run_adversarial_current_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.runner.run_simulation(
                candidate_source="adversarial-current-fallback",
                limit=3,
                report_dir=Path(tmp),
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["candidate_source"], "adversarial-current-fallback")
            self.assertEqual(summary["record_count"], 3)


if __name__ == "__main__":
    unittest.main()
