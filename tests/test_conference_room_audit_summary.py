import json
import subprocess
import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from scripts.summarize_conference_room_audit import build_summary, _build_slack_summary


class ConferenceRoomAuditSummaryTests(unittest.TestCase):
    def test_build_summary_includes_length_and_noise_sections(self):
        records = [
            {
                "posted_at": "2026-05-24T10:00:00",
                "text_markdown": "*TARS(엔지니어링팀)*:\nupdate_topic(foo)\n핵심 구현만 남깁니다.",
            },
            {
                "posted_at": "2026-05-31T10:05:00",
                "text_markdown": "*Vision(상품기획팀)*:\n유료 전환 포인트는 마지막 단락 하나로 압축해야 합니다.",
            },
        ]

        summary = build_summary(records, generated_for="2026-05-31")

        self.assertIn("persona_messages_reviewed: 2", summary)
        self.assertIn("TARS(엔지니어링팀): n=1", summary)
        self.assertIn("Noise Patterns", summary)
        self.assertIn("update_topic(", summary)
        self.assertIn("trailing_7d_avg_chars:", summary)
        self.assertIn("previous_7d_avg_chars:", summary)
        self.assertIn("trailing_7d_delta_chars:", summary)
        self.assertIn("Top Persona WoW", summary)

    def test_main_writes_output_file(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit_path = root / "conference_room_stream.jsonl"
            audit_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "posted_at": "2026-05-30T10:00:00",
                                "text_markdown": "*Coach(인사팀)*:\n안녕하세요. 현재 단계만 짧게 말씀드리겠습니다.",
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "posted_at": "2026-05-30T10:10:00",
                                "text_markdown": "*C3PO(마케팅팀)*:\n타깃은 학부모, 메시지는 부담 없는 첫 클릭, 채널은 기존 issue 하단 CTA입니다.",
                            },
                            ensure_ascii=False,
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            output_dir = root / "out"

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/summarize_conference_room_audit.py",
                    "--audit-path",
                    str(audit_path),
                    "--output-dir",
                    str(output_dir),
                    "--date",
                    "2026-05-31",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            output_path = output_dir / "conference_room_audit_2026-05-31.md"
            self.assertTrue(output_path.exists())
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("Conference Room Audit Summary", text)
            self.assertIn("Coach(인사팀)", text)

    def test_build_slack_summary_includes_noise_and_longest_personas(self):
        records = [
            {
                "posted_at": "2026-05-24T10:00:00",
                "text_markdown": "*TARS(엔지니어링팀)*:\nupdate_topic(foo)\n핵심 구현만 남깁니다.",
            },
            {
                "posted_at": "2026-05-31T10:05:00",
                "text_markdown": "*Vision(상품기획팀)*:\n안녕하세요.\n유료 전환 포인트는 마지막 단락 하나로 압축해야 합니다.",
            },
            {
                "posted_at": "2026-05-31T10:10:00",
                "text_markdown": "*Vision(상품기획팀)*:\n조금 더 긴 설명을 붙입니다. " + ("가" * 200),
            },
        ]

        text = _build_slack_summary(records)

        self.assertIn("Conference room audit", text)
        self.assertIn("persona_messages: 3", text)
        self.assertIn("avg chars WoW:", text)
        self.assertIn("top3 WoW:", text)
        self.assertIn("top_noise:", text)
        self.assertIn("Vision(상품기획팀)", text)

    def test_build_summary_includes_top_persona_weekly_delta(self):
        records = [
            {
                "posted_at": "2026-05-24T10:00:00",
                "text_markdown": "*Ledger(재무팀)*:\n" + ("가" * 200),
            },
            {
                "posted_at": "2026-05-31T10:00:00",
                "text_markdown": "*Ledger(재무팀)*:\n" + ("나" * 120),
            },
            {
                "posted_at": "2026-05-24T10:10:00",
                "text_markdown": "*KITT(법무팀)*:\n" + ("가" * 180),
            },
            {
                "posted_at": "2026-05-31T10:10:00",
                "text_markdown": "*KITT(법무팀)*:\n" + ("나" * 140),
            },
        ]

        summary = build_summary(records, generated_for="2026-05-31")

        self.assertIn("## Top Persona WoW", summary)
        self.assertIn("Ledger(재무팀): trailing_7d=", summary)
        self.assertIn("previous_7d=", summary)


if __name__ == "__main__":
    unittest.main()
