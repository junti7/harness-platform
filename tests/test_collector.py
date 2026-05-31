import unittest
from unittest.mock import patch

from adapters.content import collector


class CollectorTests(unittest.TestCase):
    def test_expand_substack_source_uses_publication_feed(self):
        source = {
            "name": "substack_publication_discovery",
            "url": "https://substack.com",
            "source_type": "newsletter",
            "channel": "substack",
            "collection_mode": "rss_search",
            "expected_signal_type": "newsletter_post",
        }

        with patch.dict("os.environ", {"SUBSTACK_PUBLICATION_URL": "https://junti7.substack.com"}, clear=False):
            expanded = collector._expand_special_sources(source)

        self.assertEqual(len(expanded), 1)
        self.assertEqual(expanded[0]["collection_mode"], "rss_pull")
        self.assertEqual(expanded[0]["url"], "https://junti7.substack.com/feed")


if __name__ == "__main__":
    unittest.main()
