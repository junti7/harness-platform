import unittest

from scripts.refresh_edu_evidence_bank import _cites_from_raw_data, extract_source_url, infer_segment, infer_source_kind, is_low_quality_evidence


class EduEvidenceQualityTests(unittest.TestCase):
    def test_extract_source_url_accepts_common_raw_data_url_fields(self):
        self.assertEqual(
            extract_source_url({"url": "https://cafe.naver.com/dochithink/2314987"}),
            "https://cafe.naver.com/dochithink/2314987",
        )
        self.assertEqual(
            extract_source_url({"canonical_url": "original https://blog.naver.com/dkp132/224065279124"}),
            "https://blog.naver.com/dkp132/224065279124",
        )
        self.assertEqual(
            extract_source_url({"doi": "10.1016/j.stueduc.2022.101231"}),
            "https://doi.org/10.1016/j.stueduc.2022.101231",
        )

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

    def test_low_quality_blocks_unrelated_multisub_anime_youtube_title(self):
        self.assertTrue(
            is_low_quality_evidence(
                "AI를 피하지 말고 친구처럼 활용하게 하세요.",
                "YouTube · Amazing Anime Man — '【新番】开局家徒四壁 | MULTI SUB'",
                {"title": "【新番】开局家徒四壁却白捡个神仙娇妻？ | MULTI SUB"},
                "YouTube_topic",
            )
        )

    def test_low_quality_blocks_non_korean_youtube_personal_title(self):
        self.assertTrue(
            is_low_quality_evidence(
                "AI 사용 규칙을 함께 정하고 지키라는 내용입니다.",
                "YouTube · TAKA — '悩んだらChatGPTに聞く人はAI依存症の人です'",
                {"title": "悩んだらChatGPTに聞く人はAI依存症の人です"},
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

    def test_raw_data_cites_use_source_owned_text_not_synthesis(self):
        raw_data = {
            "title": "AI와 친한 아이가 살아남습니다",
            "description": "대한 의존도가 높아진다면 아이의 생각은 없어지고 GPT 결과 판단력이 낮아질까봐 걱정된다는 내용입니다.",
            "synthesized_action": "AI가 대신 해주는 것이 아니라, AI를 활용해 더 깊이 생각하고 더 창의적인 결과물을 만들도록 지도해 주세요.",
        }

        cites = _cites_from_raw_data(raw_data)

        self.assertTrue(cites)
        self.assertIn("GPT 결과 판단력", cites[0])
        self.assertNotIn("더 창의적인 결과물", " ".join(cites))


if __name__ == "__main__":
    unittest.main()
