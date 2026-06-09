import unittest
from unittest.mock import patch

from core import trading_universe


class TradingUniverseTests(unittest.TestCase):
    @patch("core.trading_universe._load_seed_registry")
    @patch("core.trading_universe.execute_query")
    def test_build_trading_universe_scores_matching_symbols(self, mock_execute, mock_registry):
        mock_registry.return_value = [
            {"region": "US", "symbol": "NVDA", "exchange": "SMART", "currency": "USD", "name": "NVIDIA", "sector": "AI Chip"},
            {"region": "US", "symbol": "AVGO", "exchange": "SMART", "currency": "USD", "name": "Broadcom", "sector": "AI Chip"},
        ]

        def side_effect(query, params=None, fetch=False):
            if "ALTER TABLE" in query or "CREATE INDEX" in query:
                return None
            if "FROM filtered_signals fs" in query:
                return [
                    {
                        "title": "NVIDIA launches new GR00T robotics model",
                        "summary": "NVIDIA and Boston Dynamics deepen robotics stack",
                        "full_content": "NVIDIA GR00T and Cosmos are central to physical AI.",
                        "score": 0.8,
                        "source": "Boston_Dynamics",
                        "created_at": "2026-06-02",
                    },
                    {
                        "title": "Broadcom custom AI ASIC demand rises",
                        "summary": "Broadcom wins more custom AI accelerator business",
                        "full_content": "Broadcom custom ai asic business expands.",
                        "score": 0.7,
                        "source": "TechCrunch_robotics",
                        "created_at": "2026-06-02",
                    },
                ]
            return []

        mock_execute.side_effect = side_effect
        universe = trading_universe.build_trading_universe()

        symbols = [row["symbol"] for row in universe]
        self.assertIn("NVDA", symbols)
        self.assertIn("AVGO", symbols)

    @patch("core.trading_universe._load_seed_registry")
    @patch("core.trading_universe.execute_query")
    def test_build_trading_universe_uses_theme_bridge_when_company_not_named(self, mock_execute, mock_registry):
        mock_registry.return_value = [
            {"region": "US", "symbol": "ANET", "exchange": "SMART", "currency": "USD", "name": "Arista Networks", "sector": "AI Network"},
        ]

        def side_effect(query, params=None, fetch=False):
            if "ALTER TABLE" in query or "CREATE INDEX" in query:
                return None
            if "FROM filtered_signals fs" in query:
                return [
                    {
                        "title": "Silicon photonics becomes critical for AI scale-out",
                        "summary": "Co-packaged optics and photonic interconnects are moving into production.",
                        "full_content": "The report focuses on silicon photonics for AI clusters and co-packaged optics adoption.",
                        "score": 0.9,
                        "source": "google_news_ai_networking",
                        "created_at": "2026-06-09",
                    },
                ]
            return []

        mock_execute.side_effect = side_effect
        universe = trading_universe.build_trading_universe()

        self.assertEqual(len(universe), 1)
        self.assertEqual(universe[0]["symbol"], "ANET")
        self.assertEqual(universe[0]["theme_bridge_hits"], 1)

    @patch("core.trading_universe._load_seed_registry")
    @patch("core.trading_universe.execute_query")
    def test_explain_trading_symbol_marks_theme_matches(self, mock_execute, mock_registry):
        mock_registry.return_value = [
            {"region": "US", "symbol": "GEV", "exchange": "NYSE", "currency": "USD", "name": "GE Vernova", "sector": "Power Equip"},
        ]

        def side_effect(query, params=None, fetch=False):
            if "ALTER TABLE" in query or "CREATE INDEX" in query:
                return None
            if "FROM filtered_signals fs" in query:
                return [
                    {
                        "title": "Substation bottleneck slows data center buildout",
                        "summary": "Grid infrastructure remains a gating factor.",
                        "full_content": "Substation and power distribution bottlenecks are now shaping AI cluster deployment.",
                        "score": 0.8,
                        "source": "google_news_power_cooling",
                        "created_at": "2026-06-09",
                    },
                ]
            return []

        mock_execute.side_effect = side_effect
        rows = trading_universe.explain_trading_symbol("GEV")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_kind"], "theme")
        self.assertIn("substation", rows[0]["matched_theme"])

    @patch("core.trading_universe.UNIVERSE_PATH")
    def test_load_trading_universe_filters_alpaca_to_us(self, mock_path):
        mock_path.exists.return_value = False
        fallback = [
            {"symbol": "NVDA", "region": "US"},
            {"symbol": "005930", "region": "KR"},
        ]
        rows, source = trading_universe.load_trading_universe(broker="alpaca", fallback=fallback)
        self.assertEqual(source, "fallback")
        self.assertEqual([row["symbol"] for row in rows], ["NVDA"])


if __name__ == "__main__":
    unittest.main()
