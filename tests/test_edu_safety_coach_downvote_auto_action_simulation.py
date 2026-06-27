import importlib.util
import sys
import unittest
from pathlib import Path


def _load_script():
    module_name = "edu_safety_coach_downvote_auto_action_sim_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "simulate_edu_safety_coach_downvote_auto_action.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduSafetyCoachDownvoteAutoActionSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = _load_script()

    def test_mock_simulation_proves_downvote_to_next_answer_loop(self):
        summary = self.script.run_simulation(mock=True)

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["review_verdict"], "needs_improvement")
        self.assertTrue(summary["candidate_created"])
        self.assertTrue(summary["policy_hit"])
        self.assertFalse(summary["next_fallback_used"])
        self.assertTrue(summary["next_answer_has_low_cost_options"])
        self.assertIn("missing_low_cost_help_options", summary["review_issues"])
        self.assertEqual(summary["next_model"], "mock-answer-model")
        self.assertTrue(summary["auto_reinforcement_applied"])


if __name__ == "__main__":
    unittest.main()
