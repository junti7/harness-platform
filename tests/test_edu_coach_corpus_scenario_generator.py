import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_generator():
    module_name = "edu_coach_corpus_scenario_generator_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "edu_coach_corpus_scenario_generator.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduCoachCorpusScenarioGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = _load_generator()

    def test_collects_corpus_scenarios_from_multiple_channels(self):
        payload = self.generator.collect_corpus_scenarios(max_cases=80)

        self.assertGreaterEqual(payload["case_count"], 80)
        self.assertGreater(payload["rejected_count"], 0)
        self.assertIn("rejected_reason_counts", payload)
        self.assertGreaterEqual(payload["channel_counts"].get("Naver_카페글", 0), 1)
        self.assertGreaterEqual(payload["channel_counts"].get("Naver_지식iN", 0), 1)
        self.assertGreaterEqual(len(payload["intent_counts"]), 3)
        self.assertIn("source_paths", payload)
        self.assertTrue(all(item["allowed_use"] == "simulation_only" for item in payload["cases"]))
        self.assertTrue(all(item["quality_score"] >= 0.52 for item in payload["cases"]))

    def test_quality_gate_rejects_noise_and_pii(self):
        allowed, metadata = self.generator._quality_gate(
            text="광고 할인 쿠폰 전화번호 주소",
            question="광고 할인 쿠폰 전화번호 주소 알려줘",
            channel="RSS",
            intents=["uncategorized_user_voice"],
        )

        self.assertFalse(allowed)
        self.assertEqual(metadata["allowed_use"], "excluded_from_simulation")
        self.assertTrue(metadata["pii_risk"])
        self.assertIn("low_quality_marker", metadata["noise_reasons"])
        self.assertIn("pii_risk", metadata["noise_reasons"])

    def test_quality_gate_rejects_domain_mismatch(self):
        allowed, metadata = self.generator._quality_gate(
            text="여수 야간관광 프로그램이 조기 마감됐다.",
            question="이런 상황이면 어떻게 해야 해요? 여수 야간관광 프로그램이 조기 마감됐다",
            channel="AI타임스",
            intents=["general_principle"],
        )

        self.assertFalse(allowed)
        self.assertIn("domain_mismatch", metadata["noise_reasons"])

    def test_write_outputs(self):
        payload = self.generator.collect_corpus_scenarios(max_cases=5)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with (
                patch.object(self.generator, "CONFIG_DIR", tmp_path),
                patch.object(self.generator, "REPORT_DIR", tmp_path),
                patch.object(self.generator, "OUTPUT_CONFIG", tmp_path / "edu_coach_corpus_scenarios.json"),
            ):
                paths = self.generator.write_outputs(payload)

        self.assertIn("config_path", paths)
        self.assertIn("utterance_path", paths)
        self.assertIn("report_path", paths)


if __name__ == "__main__":
    unittest.main()
