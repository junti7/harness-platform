import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import topic_registry


class TopicRegistryTests(unittest.TestCase):
    def test_heuristic_candidates_exclude_existing_seed_topics(self):
        current_topics = ["robotics", "physical ai", "humanoid"]
        recent_titles = [
            "Tesla Optimus bots fall behind production target",
            "Why Runway is eyeing the robotics industry for future revenue growth",
            "Warehouse automation startup raises capital for humanoid deployment",
            "Optimus supply chain bottleneck slows factory rollout",
        ]

        candidates = topic_registry._heuristic_topic_candidates(current_topics, recent_titles, limit=10)

        topics = {item["topic"] for item in candidates}
        self.assertNotIn("robotics", topics)
        self.assertIn("optimus", topics)

    def test_compose_query_sources_uses_active_topics_only(self):
        sources = topic_registry._compose_query_sources(
            "physical_ai",
            [
                {"topic": "optimus", "active": True},
                {"topic": "warehouse automation", "active": False},
            ],
        )

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["topic"], "optimus")
        self.assertIn("news.google.com", sources[0]["url"])

    def test_ensure_fresh_topic_registry_returns_cached_when_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "physical_ai_topic_registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "domain": "physical_ai",
                        "generated_at": "2099-01-01T00:00:00+00:00",
                        "auto_topics": [{"topic": "optimus", "active": True}],
                        "query_sources": [],
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(topic_registry, "RUNTIME_DIR", Path(tmp)):
                payload = topic_registry.ensure_fresh_topic_registry("physical_ai", [])

            self.assertEqual(payload["auto_topics"][0]["topic"], "optimus")


if __name__ == "__main__":
    unittest.main()
