import unittest

from scripts.refresh_edu_evidence_bank import infer_segment, infer_source_kind, is_low_quality_evidence


class EduEvidenceQualityTests(unittest.TestCase):
    def test_infer_source_kind_marks_community_voice(self):
        kind = infer_source_kind(
            "네이버 맘카페 — '중학생 아이가 챗GPT로 숙제를 해요'",
            {"url": "https://cafe.naver.com/example"},
            "NaverCafe_parenting",
        )
        self.assertEqual(kind, "community_voice")

    def test_infer_source_kind_marks_research_policy(self):
        kind = infer_source_kind(
            "ERIC — AI Anxiety on AI-Assisted Problem-Solving",
            {"url": "https://eric.ed.gov/?id=EJ123"},
            "ERIC_AI",
        )
        self.assertEqual(kind, "research_policy")

    def test_infer_segment_marks_worker_clusters(self):
        segment = infer_segment({"topic_cluster": "job_seeker_ai"}, "GoogleNews_취준생AI")
        self.assertEqual(segment, "worker")

    def test_low_quality_blocks_entertainment_youtube_title(self):
        self.assertTrue(
            is_low_quality_evidence(
                "감정선이 깊어지는 명장면이었습니다.",
                "YouTube · Drama Fan Channel — 'Official Video OST Trailer'",
                {"title": "Official Video OST Trailer"},
                "YouTube_topic",
            )
        )

    def test_low_quality_keeps_relevant_parenting_youtube(self):
        self.assertFalse(
            is_low_quality_evidence(
                "아이와 AI를 같이 쓸 때는 답을 바로 얻는 습관보다 질문을 만드는 습관을 먼저 잡아줘야 해요.",
                "YouTube · Digital future Ai School — 'Episode 13 — AI in Family, Parenting & Children’s Education'",
                {"title": "Episode 13 — AI in Family, Parenting & Children’s Education"},
                "YouTube_topic",
            )
        )


if __name__ == "__main__":
    unittest.main()
