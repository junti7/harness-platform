import unittest
from unittest.mock import patch

from adapters.content import refiner
from core import cost_alerts


class CostResilienceTests(unittest.TestCase):
    @patch("adapters.content.refiner.execute_query", side_effect=RuntimeError("db down"))
    def test_log_api_cost_does_not_raise_when_db_unavailable(self, _mock_execute):
        refiner.log_api_cost("claude-haiku-4-5", 10, 5)

    @patch("core.cost_alerts.execute_query", side_effect=RuntimeError("db down"))
    def test_check_and_alert_does_not_raise_when_db_unavailable(self, _mock_execute):
        result = cost_alerts.check_and_alert(1.0, 2.0)

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
