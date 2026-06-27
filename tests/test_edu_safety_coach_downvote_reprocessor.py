import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_script():
    module_name = "edu_safety_coach_downvote_reprocessor_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "edu_safety_coach_downvote_reprocessor.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeBackend:
    def __init__(self):
        self.schema_ensured = False
        self.limit = None

    def _ensure_edu_case_schema(self):
        self.schema_ensured = True

    def _edu_vp_reprocess_pending_safety_coach_downvotes(self, *, limit):
        self.limit = limit
        return {"ok": True, "pending_found": 2, "processed": 2}


class EduSafetyCoachDownvoteReprocessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = _load_script()

    def test_run_once_calls_backend_reprocessor(self):
        fake = FakeBackend()
        with patch.object(self.script, "_load_backend", return_value=fake):
            result = self.script.run_once(limit=37)

        self.assertTrue(result["ok"])
        self.assertTrue(fake.schema_ensured)
        self.assertEqual(fake.limit, 37)
        self.assertEqual(result["processed"], 2)


if __name__ == "__main__":
    unittest.main()
