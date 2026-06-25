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
        self.assertIn("Claude", card["required_action"])
        self.assertGreaterEqual(card["estimated_minutes"], 60)
        self.assertGreaterEqual(len(card["foundation_concepts"]), 4)
        self.assertGreaterEqual(len(card["schedule_blocks"]), 5)
        self.assertIn("사람의 판단자", card["foundation_concepts"][0]["title"])
        self.assertIn("LLM", card["foundation_concepts"][1]["title"])
        self.assertEqual(len(card["checklist"]), 7)
        self.assertEqual(card["checklist"][0]["id"], "understand_not_human")
        self.assertEqual(card["checklist"][1]["id"], "understand_generation")
        self.assertEqual(card["checklist"][2]["id"], "understand_boundaries")
        self.assertEqual(len(card["sample_materials"]), 1)
        self.assertEqual(card["sample_materials"][0]["kit_id"], "day0-first-login-starter")
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

        forged = self.mod._edu_vp_safety_confirmation_from_event(
            state,
            "safety_orientation_confirmed",
            {"stage": "day0", "safety_confirmed": {"day0": True}},
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
                ],
            },
        )

        self.assertIsNone(forged)
        self.assertEqual(confirmed, {"day0": True})

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
        self.assertEqual([block["title"] for block in personalized["schedule_blocks"][:3]], [
            "AI 노출 리스크 이해",
            "LLM 작동 원리 확인",
            "안전 사용 기준 확인",
        ])

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
                }
            )

        self.assertIn("Claude", card["required_action"])
        self.assertIn("학원 일정 정리/학교 공지 요약/가정통신문 정리/병원 예약 정리/엄마모임과 가족모임 충돌 정리", card["required_action"])
        self.assertGreaterEqual(card["estimated_minutes"], 60)
        self.assertGreaterEqual(len(card["foundation_concepts"]), 4)
        self.assertGreaterEqual(len(card["schedule_blocks"]), 6)
        self.assertEqual(card["retrieval_mode"], "db_customer_facing")
        self.assertTrue(card["customer_facing_safe"])
        self.assertFalse(card["fallback_used"])
        self.assertTrue(card["external_reuse_safe"])
        self.assertEqual(len(card["evidence_cards"]), 1)
        self.assertEqual(len(card["sample_materials"]), 4)
        self.assertEqual(card["sample_materials"][0]["kit_id"], "day1-school-notice-kit")
        self.assertGreaterEqual(len(card["home_priority_missions"]), 4)
        self.assertGreaterEqual(len(card["scenario_bank"]), 10)
        self.assertIn("학교 준비물 공지 정리", [item["title"] for item in card["scenario_bank"]])
        self.assertGreaterEqual(len(card["home_life_recommended_learning"]), 1)
        self.assertIn("직접 AI를 써봐야", card["evidence_cards"][0]["title"])
        self.assertEqual(mocked_bundle.call_count, 3)
        first_args, first_kwargs = mocked_bundle.call_args_list[0]
        second_args, second_kwargs = mocked_bundle.call_args_list[1]
        third_args, third_kwargs = mocked_bundle.call_args_list[2]
        self.assertIn("학원 일정 학교 공지 가정통신문", first_args[0])
        self.assertEqual(first_args[1], "parent")
        self.assertEqual(first_kwargs["k"], 4)
        self.assertIn("학원 일정 학교 공지 가정통신문 병원 예약 엄마모임 가족모임", second_args[0])
        self.assertEqual(second_args[1], "parent")
        self.assertEqual(second_kwargs["k"], 4)
        self.assertIn("네이버 맘카페 학원 일정", third_args[0])
        self.assertEqual(third_args[1], "parent")
        self.assertEqual(third_kwargs["k"], 6)

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
