import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_shadow():
    module_name = "edu_coach_structured_packet_shadow_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_edu_coach_structured_packet_shadow.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduCoachStructuredPacketShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shadow = _load_shadow()

    def test_mock_shadow_runs_structured_packet_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.shadow.run_shadow(
                source="adversarial",
                limit=2,
                report_dir=Path(tmp),
                mock=True,
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["record_count"], 2)
            self.assertEqual(summary["structured_packet_used"], 2)
            self.assertEqual(summary["fallback_used"], 0)
            output_path = Path(summary["output_path"])
            if not output_path.is_absolute():
                output_path = Path(self.shadow.ROOT) / output_path
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
