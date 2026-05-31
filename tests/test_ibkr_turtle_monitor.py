import unittest
from unittest.mock import Mock, patch

from scripts import ibkr_turtle_monitor


class IbkrTurtleMonitorTests(unittest.TestCase):
    def test_yahoo_symbol_candidates_include_market_suffixes(self):
        contract = Mock()
        contract.symbol = "000660"
        contract.localSymbol = "000660.KS"
        contract.exchange = "KRX"
        contract.primaryExchange = "KRX"

        candidates = ibkr_turtle_monitor._yahoo_symbol_candidates(contract)

        self.assertEqual(candidates[0], "000660.KS")
        self.assertIn("000660", candidates)

    def test_compute_signal_from_bars_returns_metrics(self):
        bars = []
        base = 100.0
        for i in range(70):
            close = base + i
            high = close + 1
            if i == 69:
                close += 10
                high = close + 1
            bars.append({"high": close + 1, "low": close - 1, "close": close})

        signal = ibkr_turtle_monitor._compute_signal_from_bars("NVDA", bars, json_mode=False)

        self.assertIsNotNone(signal)
        self.assertEqual(signal["symbol"], "NVDA")
        self.assertEqual(signal["signal"], "breakout_long")
        self.assertIn(signal["active_signal"], {"S1", "S2"})
        self.assertIsNotNone(signal["atr"])
        self.assertIsNotNone(signal["s1_high"])
        self.assertIsNotNone(signal["s2_high"])

    @patch("scripts.ibkr_turtle_monitor._fetch_yahoo_daily_bars_for_contract")
    def test_calc_full_signal_falls_back_to_yahoo_when_ibkr_returns_no_bars(self, mock_yahoo):
        mock_ib = Mock()
        mock_ib.reqHistoricalData.return_value = []
        contract = Mock()
        contract.symbol = "NVDA"
        contract.currency = "USD"
        mock_yahoo.return_value = [
            [
                {
                    "high": (110 + i if i == 69 else 100 + i),
                    "low": 98 + i,
                    "close": (109 + i if i == 69 else 99 + i),
                }
                for i in range(70)
            ],
            "NVDA",
        ]

        signal = ibkr_turtle_monitor.calc_full_signal(mock_ib, contract, json_mode=False)

        self.assertIsNotNone(signal)
        self.assertEqual(signal["symbol"], "NVDA")
        self.assertEqual(signal["signal"], "breakout_long")
        mock_yahoo.assert_called_once_with(contract)


if __name__ == "__main__":
    unittest.main()
