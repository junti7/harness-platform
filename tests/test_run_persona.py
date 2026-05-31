import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from agents.registry import get_persona
from scripts import run_persona


class RunPersonaTests(unittest.TestCase):
    def test_build_live_company_context_from_status_file(self):
        with TemporaryDirectory() as tmpdir:
            status_path = Path(tmpdir) / "openclaw_status.json"
            status_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-05-30T11:30:00",
                        "runtime": {
                            "slack_phase": "phase1",
                            "capital_actions_enabled": "false",
                        },
                        "integrations": {
                            "postgres": {"available": True},
                            "notion": {"available": True},
                            "slack_bot": {"available": True},
                            "slack_webhook": {"available": False},
                        },
                        "services": {"ollama_11434": True},
                        "integrity": {"ok": True},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(run_persona, "OPENCLAW_STATUS_PATH", status_path):
                context = run_persona._build_live_company_context()

        self.assertIn("[LIVE COMPANY CONTEXT]", context)
        self.assertIn("generated_at: 2026-05-30T11:30:00", context)
        self.assertIn("capital_actions_enabled: false", context)
        self.assertIn("top_risks: Capital actions gated off", context)

    def test_build_prompt_includes_live_company_context(self):
        persona = get_persona("vision")
        with patch.object(
            run_persona,
            "_build_live_company_context",
            return_value="[LIVE COMPANY CONTEXT]\n- top_risks: Capital actions gated off\n",
        ):
            prompt = run_persona._build_prompt(persona, "상품 패키징 의견 주세요", "cid-1234")

        self.assertIn("[LIVE COMPANY CONTEXT]", prompt)
        self.assertIn("top_risks: Capital actions gated off", prompt)
        self.assertIn("[TASK]\n상품 패키징 의견 주세요", prompt)

    def test_load_latest_open_ar(self):
        with TemporaryDirectory() as tmpdir:
            ar_path = Path(tmpdir) / "ar_tracker.jsonl"
            ar_path.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "AR-1", "owner": "Vision", "status": "completed", "title": "done"}, ensure_ascii=False),
                        json.dumps(
                            {
                                "id": "AR-2",
                                "owner": "KITT",
                                "status": "open",
                                "title": "법률 검토 진행",
                                "due_by": "2026-06-01",
                            },
                            ensure_ascii=False,
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            with patch.object(run_persona, "AR_TRACKER_PATH", ar_path):
                summary = run_persona._load_latest_open_ar()

        self.assertIn("latest_ar: AR-2", summary)
        self.assertIn("owner=KITT", summary)
        self.assertIn("status=open", summary)

    def test_load_latest_orchestration_summary(self):
        with TemporaryDirectory() as tmpdir:
            runs_path = Path(tmpdir) / "orchestration_runs.jsonl"
            runs_path.write_text(
                json.dumps(
                    {
                        "correlation_id": "orch-1234",
                        "ts": "2026-05-30T11:40:00",
                        "personas": ["Vision(상품기획팀)", "KITT(법무팀)"],
                        "decision": "가격 변경은 보류하고 법률 검토를 먼저 진행합니다.",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with patch.object(run_persona, "ORCHESTRATION_RUNS_PATH", runs_path):
                summary = run_persona._load_latest_orchestration_summary()

        self.assertIn("latest_meeting: orch-1234", summary)
        self.assertIn("personas=2", summary)
        self.assertIn("latest_decision:", summary)

    def test_load_goal_kpi_context(self):
        def fake_query_rows(query, params=None):
            normalized = " ".join(query.split())
            if "FROM strategic_goals" in normalized:
                return [
                    {
                        "id": 7,
                        "title": "Physical AI Weekly paid conversion",
                        "status": "active",
                        "target_metric": "paid_subscribers",
                        "target_value": 100,
                        "current_value": 24,
                        "unit": "subs",
                    },
                    {
                        "id": 8,
                        "title": "Physical AI Weekly free subscriber growth",
                        "status": "active",
                        "target_metric": "free_subscribers",
                        "target_value": 1200,
                        "current_value": 980,
                        "unit": "subs",
                    },
                ]
            if "FROM goal_forecasts" in normalized:
                if params == (7,):
                    return [{"probability_to_hit": 0.62, "recommended_mode": "local_revision"}]
                if params == (8,):
                    return [{"probability_to_hit": 0.71, "recommended_mode": "stay_course"}]
                return [{"probability_to_hit": 0.62, "recommended_mode": "local_revision"}]
            if "FROM goal_progress_snapshots" in normalized:
                if params == (7,):
                    return [{"health_status": "yellow", "variance": -12.0}]
                if params == (8,):
                    return [{"health_status": "green", "variance": 8.0}]
                return [{"health_status": "yellow", "variance": -12.0}]
            if "FROM subscriber_snapshots" in normalized:
                return [
                    {"snapshot_date": "2026-05-29", "free_subscribers": 1200, "paid_subscribers": 24},
                    {"snapshot_date": "2026-05-28", "free_subscribers": 1188, "paid_subscribers": 22},
                ]
            return []

        with patch.object(run_persona, "_query_rows", side_effect=fake_query_rows):
            summary = run_persona._load_goal_kpi_context()

        self.assertIn("latest_goal: #7", summary)
        self.assertIn("latest_goal: #8", summary)
        self.assertIn("latest_forecast: goal=#7 | health=yellow | p_hit=62% | mode=local_revision", summary)
        self.assertIn("latest_forecast: goal=#8 | health=green | p_hit=71% | mode=stay_course", summary)
        self.assertIn("latest_kpi: 2026-05-29 | free=1200 (+12) | paid=24 (+2)", summary)

    def test_build_prompt_includes_goal_kpi_context(self):
        persona = get_persona("vision")
        with patch.object(run_persona, "_build_live_company_context", return_value=""), patch.object(
            run_persona, "_load_latest_open_ar", return_value=""
        ), patch.object(run_persona, "_load_latest_orchestration_summary", return_value=""), patch.object(
            run_persona, "_load_goal_kpi_context", return_value="- latest_goal: #7 | status=active\n- latest_goal: #8 | status=active\n"
        ):
            prompt = run_persona._build_prompt(persona, "상품 패키징 의견 주세요", "cid-5678")

        self.assertIn("latest_goal: #7 | status=active", prompt)
        self.assertIn("latest_goal: #8 | status=active", prompt)
        self.assertIn("[TASK]\n상품 패키징 의견 주세요", prompt)

    def test_tars_prompt_includes_engineering_style_rule(self):
        persona = get_persona("tars")
        with patch.object(run_persona, "_build_live_company_context", return_value=""), patch.object(
            run_persona, "_load_latest_open_ar", return_value=""
        ), patch.object(run_persona, "_load_latest_orchestration_summary", return_value=""), patch.object(
            run_persona, "_load_goal_kpi_context", return_value=""
        ):
            prompt = run_persona._build_prompt(persona, "배포 위험만 말해줘", "cid-tars")

        self.assertIn("무엇을 바꿀지 -> 위험 -> 바로 할 테스트", prompt)

    def test_ledger_prompt_includes_finance_style_rule(self):
        persona = get_persona("ledger")
        with patch.object(run_persona, "_build_live_company_context", return_value=""), patch.object(
            run_persona, "_load_latest_open_ar", return_value=""
        ), patch.object(run_persona, "_load_latest_orchestration_summary", return_value=""), patch.object(
            run_persona, "_load_goal_kpi_context", return_value=""
        ):
            prompt = run_persona._build_prompt(persona, "비용만 말해줘", "cid-ledger")

        self.assertIn("숫자 -> 의미 -> 한도/다음 액션", prompt)

    def test_kitt_prompt_includes_legal_style_rule(self):
        persona = get_persona("kitt")
        with patch.object(run_persona, "_build_live_company_context", return_value=""), patch.object(
            run_persona, "_load_latest_open_ar", return_value=""
        ), patch.object(run_persona, "_load_latest_orchestration_summary", return_value=""), patch.object(
            run_persona, "_load_goal_kpi_context", return_value=""
        ):
            prompt = run_persona._build_prompt(persona, "법적 위험만 말해줘", "cid-kitt")

        self.assertIn("허용/보류/금지 -> 근거 법령 1개 -> 필요한 게이트/다음 액션", prompt)

    def test_watchman_prompt_includes_risk_style_rule(self):
        persona = get_persona("watchman")
        with patch.object(run_persona, "_build_live_company_context", return_value=""), patch.object(
            run_persona, "_load_latest_open_ar", return_value=""
        ), patch.object(run_persona, "_load_latest_orchestration_summary", return_value=""), patch.object(
            run_persona, "_load_goal_kpi_context", return_value=""
        ):
            prompt = run_persona._build_prompt(persona, "리스크만 말해줘", "cid-watchman")

        self.assertIn("리스크 -> 트리거 -> 완화/킬스위치", prompt)

    def test_vision_prompt_includes_product_style_rule(self):
        persona = get_persona("vision")
        with patch.object(run_persona, "_build_live_company_context", return_value=""), patch.object(
            run_persona, "_load_latest_open_ar", return_value=""
        ), patch.object(run_persona, "_load_latest_orchestration_summary", return_value=""), patch.object(
            run_persona, "_load_goal_kpi_context", return_value=""
        ):
            prompt = run_persona._build_prompt(persona, "패키징만 말해줘", "cid-vision")

        self.assertIn("패키지 -> 근거 -> 리스크 -> 다음 액션", prompt)

    def test_friday_prompt_includes_ops_style_rule(self):
        persona = get_persona("friday")
        with patch.object(run_persona, "_build_live_company_context", return_value=""), patch.object(
            run_persona, "_load_latest_open_ar", return_value=""
        ), patch.object(run_persona, "_load_latest_orchestration_summary", return_value=""), patch.object(
            run_persona, "_load_goal_kpi_context", return_value=""
        ):
            prompt = run_persona._build_prompt(persona, "운영만 말해줘", "cid-friday")

        self.assertIn("상태 -> 병목 -> 수정 -> 다음 액션", prompt)

    def test_call_persona_applies_handle_specific_length_limit(self):
        persona = get_persona("c3po")
        long_text = "가" * 700
        with patch.object(run_persona, "call_llm", return_value=(long_text, True)):
            text, ok = run_persona.call_persona(persona, "메시지 정리", "cid-c3po")

        self.assertTrue(ok)
        self.assertLessEqual(len(text), 420)

    def test_call_persona_applies_ledger_length_limit(self):
        persona = get_persona("ledger")
        long_text = "나" * 700
        with patch.object(run_persona, "call_llm", return_value=(long_text, True)):
            text, ok = run_persona.call_persona(persona, "재무 요약", "cid-ledger")

        self.assertTrue(ok)
        self.assertLessEqual(len(text), 360)

    def test_enforce_persona_shape_limits_ledger_to_three_lines(self):
        persona = get_persona("ledger")
        raw = (
            "## 요약\n"
            "1. 숫자: 이번 주 비용은 120만원이고 API 비용 비중은 48%입니다. 추가 설명이 아주 길게 붙어도 여기서 잘려야 합니다.\n"
            "2. 의미: paid 전환 0건이라 CAC 회수 근거가 아직 없습니다. 그래서 비용 집행 확대는 부적절합니다.\n"
            "3. 한도: 다음 주 상한은 80만원으로 두고 초과 집행은 보류하세요.\n"
            "4. 부록: 이 줄은 없어져야 합니다.\n"
        )

        shaped = run_persona._enforce_persona_shape(persona, raw)

        lines = shaped.splitlines()
        self.assertLessEqual(len(lines), 3)
        self.assertTrue(all(len(line) <= 120 for line in lines))
        self.assertNotIn("부록", shaped)

    def test_enforce_persona_shape_limits_kitt_to_three_lines(self):
        persona = get_persona("kitt")
        raw = (
            "**판단**\n"
            "- 보류: 표시광고법 검토 전 외부 발행은 위험합니다. 설명이 길어도 한 줄 안에서 정리돼야 합니다.\n"
            "- 근거: 표시광고법상 오인 가능성이 있으면 claim 수정이 필요합니다.\n"
            "- 게이트: legal_review_approve 후 publish 판단으로 넘기세요.\n"
            "- 사례 설명: 이 줄은 제거되어야 합니다.\n"
        )

        shaped = run_persona._enforce_persona_shape(persona, raw)

        lines = shaped.splitlines()
        self.assertLessEqual(len(lines), 3)
        self.assertTrue(all(len(line) <= 120 for line in lines))
        self.assertNotIn("사례 설명", shaped)

    def test_enforce_persona_shape_formats_jarvis_into_three_blocks(self):
        persona = get_persona("jarvis")
        raw = (
            "안녕하세요.\n"
            "이번 안건의 핵심은 paid 전환 실험은 유지하되 가격 변경은 지금 하면 안 된다는 점입니다. 배경 설명이 길게 붙어도 잘려야 합니다.\n"
            "근거는 free 유입은 늘지만 paid 전환 증거가 아직 부족하고 법무 검토도 끝나지 않았기 때문입니다.\n"
            "다음 액션은 가격 유지, copy 수정, legal_review_approve 확인 후 재판단입니다.\n"
            "추가 부연 설명은 제거되어야 합니다.\n"
        )

        shaped = run_persona._enforce_persona_shape(persona, raw)

        lines = shaped.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("핵심 판단:"))
        self.assertTrue(lines[1].startswith("근거:"))
        self.assertTrue(lines[2].startswith("다음 액션:"))
        self.assertTrue(all(len(line) <= 120 for line in lines))

    def test_call_persona_applies_jarvis_length_limit(self):
        persona = get_persona("jarvis")
        long_text = "핵심 판단입니다. " * 80
        with patch.object(run_persona, "call_llm", return_value=(long_text, True)):
            text, ok = run_persona.call_persona(persona, "CEO 카드 정리", "cid-jarvis")

        self.assertTrue(ok)
        self.assertLessEqual(len(text), 420)
        self.assertLessEqual(len(text.splitlines()), 3)

    def test_enforce_persona_shape_formats_vision_into_four_blocks(self):
        persona = get_persona("vision")
        raw = (
            "상품 패키지는 무료 본문 + paid deep note 1개로 단순화해야 합니다. 설명이 길어도 줄여야 합니다.\n"
            "근거는 현재 free 유입 대비 paid 전환 근거가 약하고, 옵션이 많으면 결제 저항이 커지기 때문입니다.\n"
            "리스크는 약속 범위를 넓히면 매주 제작 부담이 커진다는 점입니다.\n"
            "다음 액션은 이번 주 issue부터 CTA 1개만 남기고 teaser 문구를 다시 쓰는 것입니다.\n"
            "추가 설명은 제거됩니다.\n"
        )

        shaped = run_persona._enforce_persona_shape(persona, raw)

        lines = shaped.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("패키지:"))
        self.assertTrue(lines[1].startswith("근거:"))
        self.assertTrue(lines[2].startswith("리스크:"))
        self.assertTrue(lines[3].startswith("다음 액션:"))
        self.assertTrue(all(len(line) <= 120 for line in lines))

    def test_enforce_persona_shape_formats_friday_into_four_blocks(self):
        persona = get_persona("friday")
        raw = (
            "현재 상태는 free 유입은 늘지만 paid 전환은 아직 없는 구간입니다.\n"
            "병목은 CTA가 분산돼 있고 paid 가치 제안이 한 줄로 정리되지 않은 점입니다.\n"
            "수정은 CTA를 1개로 줄이고 teaser를 성과 약속 대신 문제 해결 문장으로 바꾸는 것입니다.\n"
            "다음 액션은 이번 issue 발송 전 CTA 카피를 교체하고 클릭률만 먼저 보자는 것입니다.\n"
            "배경 설명은 제거됩니다.\n"
        )

        shaped = run_persona._enforce_persona_shape(persona, raw)

        lines = shaped.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("상태:"))
        self.assertTrue(lines[1].startswith("병목:"))
        self.assertTrue(lines[2].startswith("수정:"))
        self.assertTrue(lines[3].startswith("다음 액션:"))
        self.assertTrue(all(len(line) <= 120 for line in lines))

    def test_compress_persona_output_removes_failure_noise(self):
        raw = (
            "My apologies, I am regenerating the whole content.\n"
            "update_topic(strategic_intent='x')\n"
            "안녕하세요!\n"
            "핵심 판단만 남깁니다.\n"
        )

        cleaned = run_persona._compress_persona_output(raw, max_chars=200)

        self.assertEqual(cleaned, "핵심 판단만 남깁니다.")

    def test_compress_persona_output_prefers_sentence_boundary(self):
        raw = "첫 문장입니다. 둘째 문장도 있습니다. 셋째 문장은 잘려야 합니다."

        cleaned = run_persona._compress_persona_output(raw, max_chars=28)

        self.assertEqual(cleaned, "첫 문장입니다. 둘째 문장도 있습니다.")


if __name__ == "__main__":
    unittest.main()
