import unittest

from scripts import analyze_google_cloud_spend as mod


class GoogleCloudSpendAnalysisTests(unittest.TestCase):
    def test_build_report_highlights_youtube_when_units_present(self):
        runs = [
            mod.RunStats(timestamp="2026-06-01 00:50:30", channel_calls=8, query_calls=20, quota_exceeded=False, api_new_items=361),
            mod.RunStats(timestamp="2026-06-01 12:53:50", channel_calls=0, query_calls=0, quota_exceeded=True, api_new_items=0),
        ]
        report = mod.build_report(
            "2026-06-01",
            runs,
            {"available": "yes", "calls": 58, "input_tokens": 51834, "output_tokens": 18250},
        )

        self.assertIn("YouTube Data API v3", report)
        self.assertIn("estimated_units=2808", report)
        self.assertIn("Gemini 사용은 보조 요인 수준", report)

    def test_parse_runs_counts_channel_and_query_calls(self):
        content = "\n".join(
            [
                "2026-06-01 00:50:30,719 | tier=1 | cid=x | INFO | === 교육 DEEP RESEARCH 수집 시작",
                "2026-06-01 00:50:31,100 | tier=1 | cid=x | INFO | YouTube API: Test (@test)",
                "2026-06-01 00:50:32,200 | tier=1 | cid=x | INFO | YouTube API 검색: abc",
                "2026-06-01 00:52:11,000 | tier=1 | cid=x | INFO |   YouTube 수집 병합 완료 (yt-dlp 신규: 0개, API 신규: 12개)",
            ]
        )
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tmp:
            tmp.write(content)
            tmp.flush()
            runs = mod.parse_runs(mod.Path(tmp.name), "2026-06-01")

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].channel_calls, 1)
        self.assertEqual(runs[0].query_calls, 1)
        self.assertEqual(runs[0].api_new_items, 12)


if __name__ == "__main__":
    unittest.main()
