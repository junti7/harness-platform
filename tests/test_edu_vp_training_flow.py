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

    def test_week0_builds_deterministic_checklist(self):
        card = self.mod._edu_vp_build_week0(
            {
                "preferred_llm": "claude",
                "current_device": "iphone",
                "desktop_os": "mac",
                "biggest_friction": "영어라서 무섭다",
                "learning_goal": "학교 준비물 메시지를 덜 스트레스 받으며 정리하기",
            }
        )

        self.assertIn("Week 0", card["title"])
        self.assertIn("Claude", card["required_action"])
        self.assertEqual(len(card["checklist"]), 4)
        self.assertEqual(card["blocked_step_options"], ["open_tool", "login_ok", "first_prompt", "copy_result"])

    def test_week1_contains_rag_lineage_and_evidence_cards(self):
        fake_bundle = {
            "mode": "db_customer_facing",
            "items": [
                {
                    "title": "부모가 먼저 AI를 써봐야 자녀 대화가 달라진다",
                    "source_kind": "research_policy",
                    "cite": "출처: example",
                    "body": "부모가 먼저 직접 AI를 써본 경험이 있어야 자녀와 감정 섞이지 않은 대화를 시작하기 쉽다는 내용입니다.",
                }
            ],
        }

        with patch.object(self.mod, "_retrieve_evidence_bundle", return_value=fake_bundle):
            card = self.mod._edu_vp_build_week1(
                {
                    "preferred_llm": "claude",
                    "biggest_friction": "뭘 질문해야 할지 모르겠다",
                    "learning_goal": "단톡방 답장을 덜 부담스럽게 만들기",
                }
            )

        self.assertIn("Claude", card["required_action"])
        self.assertEqual(card["retrieval_mode"], "db_customer_facing")
        self.assertTrue(card["customer_facing_safe"])
        self.assertFalse(card["fallback_used"])
        self.assertTrue(card["external_reuse_safe"])
        self.assertEqual(len(card["evidence_cards"]), 1)
        self.assertIn("부모가 먼저 AI를 써봐야", card["evidence_cards"][0]["title"])


if __name__ == "__main__":
    unittest.main()
