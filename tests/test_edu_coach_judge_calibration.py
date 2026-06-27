import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_calibration():
    module_name = "edu_coach_judge_calibration_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    path = scripts_dir / "edu_coach_judge_calibration.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduCoachJudgeCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibration = _load_calibration()

    def test_normalizes_gold_labels(self):
        self.assertEqual(self.calibration._normalize_gold("pass"), "clear")
        self.assertEqual(self.calibration._normalize_gold("needs_work"), "needs_work")
        self.assertEqual(self.calibration._normalize_gold("block"), "block")

    def test_cohen_kappa_perfect(self):
        confusion = {("clear", "clear"): 2, ("needs_work", "needs_work"): 2, ("block", "block"): 1}

        kappa = self.calibration._cohen_kappa(confusion, ["clear", "needs_work", "block"])

        self.assertEqual(kappa, 1.0)

    def test_run_calibration_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.calibration.run_calibration(report_dir=Path(tmp))

            self.assertTrue(summary["ok"])
            self.assertGreaterEqual(summary["record_count"], 20)
            self.assertIn("cohen_kappa", summary)
            self.assertTrue(Path(summary["records_path"]).exists())
            self.assertTrue(Path(summary["summary_path"]).exists())
            self.assertTrue(Path(summary["report_path"]).exists())


if __name__ == "__main__":
    unittest.main()
