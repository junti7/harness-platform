import io
import json
import unittest
from unittest.mock import patch

from scripts import openclaw_notion_archive


class OpenClawNotionArchiveTest(unittest.TestCase):
    def test_unknown_model_taxonomy_is_normalized_before_strict_write(self):
        payload = {
            "title": "Turtle 진단",
            "body": "본문",
            "artifactType": "operating_record",
            "teams": ["Jarvis"],
        }
        with (
            patch("sys.stdin", io.StringIO(json.dumps(payload))),
            patch("sys.stdout", new_callable=io.StringIO),
            patch.object(
                openclaw_notion_archive,
                "create_archive_page",
                return_value={"id": "page-1", "url": "https://notion.test/page-1"},
            ) as create,
        ):
            self.assertEqual(openclaw_notion_archive.main(), 0)

        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["artifact_type"], "ops_brief")
        self.assertEqual(kwargs["teams"], ["Chief of Staff"])
        self.assertTrue(kwargs["strict"])


if __name__ == "__main__":
    unittest.main()
