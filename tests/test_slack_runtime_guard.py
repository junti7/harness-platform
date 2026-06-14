import os
import unittest
from unittest.mock import patch

from adapters.content.slack_runtime_guard import get_slack_runtime_guard_error


class SlackRuntimeGuardTests(unittest.TestCase):
    def test_blocks_macbook_class_host_by_default(self):
        with patch.dict(os.environ, {}, clear=False), patch(
            "adapters.content.slack_runtime_guard.collect_hostnames",
            return_value={"bagjuntaeui-macbookpro-2.local", "bagjuntaeui-macbookpro-2"},
        ):
            error = get_slack_runtime_guard_error()

        self.assertIsNotNone(error)
        self.assertIn("Mac Mini", error)

    def test_allows_explicit_mac_mini_allowlist_host(self):
        with patch.dict(
            os.environ,
            {"HARNESS_SLACK_ALLOWED_HOSTNAMES": "harness-mac-mini,harness-mac-mini.local"},
            clear=False,
        ), patch(
            "adapters.content.slack_runtime_guard.collect_hostnames",
            return_value={"harness-mac-mini.local", "harness-mac-mini"},
        ):
            error = get_slack_runtime_guard_error()

        self.assertIsNone(error)

    def test_blocks_when_allowlist_is_set_but_host_mismatches(self):
        with patch.dict(
            os.environ,
            {"HARNESS_SLACK_ALLOWED_HOSTNAMES": "harness-mac-mini"},
            clear=False,
        ), patch(
            "adapters.content.slack_runtime_guard.collect_hostnames",
            return_value={"bagjuntaeui-macbookpro-2.local", "bagjuntaeui-macbookpro-2"},
        ):
            error = get_slack_runtime_guard_error()

        self.assertIsNotNone(error)
        self.assertIn("HARNESS_SLACK_ALLOWED_HOSTNAMES", error)


if __name__ == "__main__":
    unittest.main()
