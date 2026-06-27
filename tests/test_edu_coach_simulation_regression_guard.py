import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_guard():
    module_name = "edu_coach_simulation_regression_guard_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_edu_coach_simulation_regression.py"
    scripts_dir = str(path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduCoachSimulationRegressionGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = _load_guard()

    def test_passes_when_max_corpus_and_adversarial_clear(self):
        def fake_run_simulation(*, candidate_source, report_dir):
            if candidate_source == "adversarial-current-fallback":
                return {"record_count": 378, "verdict_counts": {"clear": 378}, "channel_counts": {}}
            return {
                "record_count": 30264,
                "verdict_counts": {"clear": 30264},
                "channel_counts": {"YouTube": 1649},
            }

        with (
            patch.object(self.guard, "run_simulation", side_effect=fake_run_simulation),
            patch.object(self.guard, "check_freshness", return_value={"ok": True, "failures": []}),
            patch.object(self.guard, "check_latency_budget", return_value={"ok": True, "failures": []}),
        ):
            summary = self.guard.check_regression()

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["failures"], [])

    def test_fails_on_needs_work_or_youtube_drop(self):
        def fake_run_simulation(*, candidate_source, report_dir):
            if candidate_source == "adversarial-current-fallback":
                return {"record_count": 378, "verdict_counts": {"clear": 377, "needs_work": 1}, "channel_counts": {}}
            return {
                "record_count": 30263,
                "verdict_counts": {"clear": 30262, "needs_work": 1},
                "channel_counts": {"YouTube": 100},
            }

        with (
            patch.object(self.guard, "run_simulation", side_effect=fake_run_simulation),
            patch.object(self.guard, "check_freshness", return_value={"ok": True, "failures": []}),
            patch.object(self.guard, "check_latency_budget", return_value={"ok": True, "failures": []}),
        ):
            summary = self.guard.check_regression()

        self.assertFalse(summary["ok"])
        self.assertIn("adversarial_needs_work=1", summary["failures"])
        self.assertIn("corpus_needs_work=1", summary["failures"])
        self.assertIn("corpus_records=30263<min=30264", summary["failures"])
        self.assertIn("youtube_records=100<min=1649", summary["failures"])

    def test_fails_when_fresh_corpus_exceeds_committed_config(self):
        def fake_run_simulation(*, candidate_source, report_dir):
            if candidate_source == "adversarial-current-fallback":
                return {"record_count": 378, "verdict_counts": {"clear": 378}, "channel_counts": {}}
            return {
                "record_count": 30264,
                "verdict_counts": {"clear": 30264},
                "channel_counts": {"YouTube": 1649},
            }

        freshness = {
            "ok": False,
            "failures": ["fresh_youtube=1700>committed_youtube=1649"],
            "committed_youtube": 1649,
            "fresh_youtube": 1700,
        }
        with (
            patch.object(self.guard, "run_simulation", side_effect=fake_run_simulation),
            patch.object(self.guard, "check_freshness", return_value=freshness),
            patch.object(self.guard, "check_latency_budget", return_value={"ok": True, "failures": []}),
        ):
            summary = self.guard.check_regression()

        self.assertFalse(summary["ok"])
        self.assertIn("freshness:fresh_youtube=1700>committed_youtube=1649", summary["failures"])

    def test_fails_when_latency_guard_fails(self):
        def fake_run_simulation(*, candidate_source, report_dir):
            if candidate_source == "adversarial-current-fallback":
                return {"record_count": 378, "verdict_counts": {"clear": 378}, "channel_counts": {}}
            return {
                "record_count": 30264,
                "verdict_counts": {"clear": 30264},
                "channel_counts": {"YouTube": 1649},
            }

        latency = {
            "ok": False,
            "failures": ["fast_rag_timeout_elapsed_ms=900>max=450", "rag_patch_llm_calls=2>max=1"],
        }
        with (
            patch.object(self.guard, "run_simulation", side_effect=fake_run_simulation),
            patch.object(self.guard, "check_freshness", return_value={"ok": True, "failures": []}),
            patch.object(self.guard, "check_latency_budget", return_value=latency),
        ):
            summary = self.guard.check_regression()

        self.assertFalse(summary["ok"])
        self.assertIn("latency:fast_rag_timeout_elapsed_ms=900>max=450", summary["failures"])
        self.assertIn("latency:rag_patch_llm_calls=2>max=1", summary["failures"])


if __name__ == "__main__":
    unittest.main()
