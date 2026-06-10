import unittest

from core.source_registry import (
    build_channel_coverage,
    merge_catalog_rows_with_defaults,
    source_status,
)


class SourceRegistryTests(unittest.TestCase):
    def test_merge_catalog_rows_with_defaults_preserves_new_config_sources(self):
        defaults = [
            {
                "name": "arXiv_robotics",
                "url": "https://rss.arxiv.org/rss/cs.RO",
                "source_type": "rss",
                "enabled": True,
                "channel": "arxiv",
                "collection_mode": "rss_pull",
            },
            {
                "name": "x_robotics_search",
                "url": "https://x.com/search?q=robotics",
                "source_type": "social",
                "enabled": False,
                "channel": "x",
                "collection_mode": "browser_search",
                "activation_policy": "restricted",
                "requires_login": True,
            },
        ]
        db_rows = [
            {
                "source_name": "arXiv_robotics",
                "base_url": "https://rss.arxiv.org/rss/cs.RO",
                "source_type": "rss",
                "enabled": True,
                "expected_signal_type": "research",
                "reliability_score": 0.9,
                "rate_limit_policy": {"channel": "arxiv", "collection_mode": "rss_pull"},
            }
        ]

        merged = merge_catalog_rows_with_defaults(db_rows, defaults)
        names = {item["source_name"] for item in merged}

        self.assertIn("arXiv_robotics", names)
        self.assertIn("x_robotics_search", names)

    def test_config_wins_over_db_for_kill_switch(self):
        """config(enabled:false)가 DB(enabled:true) self-register 행을 이겨야 한다.
        record_poll upsert가 enabled:true 행을 만들어도 config 비활성화가 kill switch로 작동(Red Team Codex)."""
        defaults = [
            {
                "name": "The_Robot_Report",
                "url": "https://www.therobotreport.com/feed/",
                "source_type": "rss",
                "enabled": False,  # 운영자가 config에서 끔
                "channel": "news",
                "collection_mode": "rss_pull",
                "reliability_score": 0.7,
            }
        ]
        db_rows = [
            {
                "source_name": "The_Robot_Report",
                "base_url": "https://www.therobotreport.com/feed/",
                "source_type": "rss",
                "enabled": True,  # record_poll이 폴링 시점에 self-register한 잔존값
                "reliability_score": 0.5,
                "rate_limit_policy": {},
                "last_poll_status": "ok",  # DB 전용 런타임 컬럼은 보존돼야
            }
        ]

        merged = merge_catalog_rows_with_defaults(db_rows, defaults)
        row = next(r for r in merged if r["source_name"] == "The_Robot_Report")
        self.assertFalse(row["enabled"], "config enabled:false가 DB enabled:true를 이겨야 함")
        self.assertEqual(row["reliability_score"], 0.7, "config reliability가 우선")
        self.assertEqual(row.get("last_poll_status"), "ok", "DB 전용 런타임 컬럼은 보존")

    def test_db_only_source_not_in_config_keeps_db_values(self):
        """config에 없는 런타임 시드 소스는 DB 값을 그대로 유지(else 분기)."""
        merged = merge_catalog_rows_with_defaults(
            [{"source_name": "공공데이터포털_데이터셋", "source_type": "open_api", "enabled": True}],
            [],
        )
        self.assertEqual(len(merged), 1)
        self.assertTrue(merged[0]["enabled"])

    def test_source_status_marks_login_required_sources_restricted(self):
        row = {
            "source_name": "x_robotics_search",
            "source_type": "social",
            "enabled": False,
            "rate_limit_policy": {
                "channel": "x",
                "collection_mode": "browser_search",
                "activation_policy": "restricted",
                "requires_login": True,
            },
        }

        self.assertEqual(source_status(row), "restricted")

    def test_build_channel_coverage_counts_active_and_restricted(self):
        rows = [
            {
                "source_name": "arXiv_robotics",
                "source_type": "rss",
                "enabled": True,
                "rate_limit_policy": {"channel": "arxiv", "collection_mode": "rss_pull"},
            },
            {
                "source_name": "x_robotics_search",
                "source_type": "social",
                "enabled": False,
                "rate_limit_policy": {
                    "channel": "x",
                    "collection_mode": "browser_search",
                    "activation_policy": "restricted",
                    "requires_login": True,
                },
            },
        ]

        coverage = build_channel_coverage(rows)
        by_channel = {item["channel"]: item for item in coverage}

        self.assertEqual(by_channel["arxiv"]["active_sources"], 1)
        self.assertEqual(by_channel["x"]["restricted_sources"], 1)

    def test_source_status_marks_enabled_substack_rss_search_active(self):
        row = {
            "source_name": "substack_publication_discovery",
            "source_type": "newsletter",
            "enabled": True,
            "rate_limit_policy": {
                "channel": "substack",
                "collection_mode": "rss_search",
                "activation_policy": "always_on",
            },
        }

        self.assertEqual(source_status(row), "active")


if __name__ == "__main__":
    unittest.main()
