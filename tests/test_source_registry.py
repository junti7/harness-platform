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
