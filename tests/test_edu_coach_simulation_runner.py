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
