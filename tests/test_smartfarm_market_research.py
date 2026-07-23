import copy
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from adapters.content.tools import structured_web_search
from scripts.smartfarm_market_research import build_research_plan, load_catalog, validate_report
from scripts.openclaw_smartfarm_research_bridge import build_parser as build_read_only_parser


def _candidate(item, number, recommendation):
    return {
        "item_id": item["id"],
        "product_name": f"{item['name_ko']} {number}",
        "vendor": "vendor",
        "product_url": f"https://example.com/{item['id']}/{number}",
        "observed_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "price": 10000 + number,
        "currency": "KRW",
        "shipping_cost": 3000,
        "delivery_estimate": "2-3 days",
        "availability": "in_stock",
        "evidence_urls": [
            f"https://example.com/evidence/{item['id']}/{number}",
            f"https://manufacturer.example/spec/{item['id']}/{number}",
        ],
        "required_check_results": {
            check: {
                "status": "verified",
                "evidence_url": f"https://manufacturer.example/check/{item['id']}/{check}",
                "note": "manufacturer specification",
            }
            for check in item["required_checks"]
        },
        "risks": [],
        "recommendation": recommendation,
    }


class SmartfarmMarketResearchTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def _valid_report(self):
        candidates = []
        for item in self.catalog["items"]:
            candidates.extend(
                [
                    _candidate(item, 1, "recommended"),
                    _candidate(item, 2, "alternate"),
                    _candidate(item, 3, "reject"),
                ]
            )
        return {"candidates": candidates}

    def test_plan_contains_every_procurement_item_and_no_purchase_rule(self):
        plan = build_research_plan(self.catalog)
        self.assertEqual(len(plan["items"]), 6)
        self.assertEqual(plan["deliverables"]["decision"], "shortlist_only_no_purchase")
        self.assertIn("ESP32", plan["controller_architecture"]["edge_node"])
        self.assertIn("ADC1", plan["controller_architecture"]["rule"])
        self.assertTrue(
            any("Do not add to cart" in rule for rule in plan["candidate_contract"]["rules"])
        )

    def test_valid_report_passes(self):
        result = validate_report(self._valid_report(), self.catalog)
        self.assertTrue(result["ok"])
        self.assertEqual(result["findings"], [])

    def test_missing_candidates_and_safety_checks_fail(self):
        report = self._valid_report()
        item = self.catalog["items"][0]
        report["candidates"] = [
            candidate
            for candidate in report["candidates"]
            if candidate["item_id"] != item["id"] or candidate["recommendation"] == "recommended"
        ]
        report["candidates"][0] = copy.deepcopy(report["candidates"][0])
        report["candidates"][0]["required_check_results"] = {}
        result = validate_report(report, self.catalog)
        self.assertFalse(result["ok"])
        self.assertTrue(any("minimum is 3" in finding for finding in result["findings"]))
        self.assertTrue(any("missing required checks" in finding for finding in result["findings"]))

    def test_recommended_candidate_with_unknown_check_fails_closed(self):
        report = self._valid_report()
        recommended = report["candidates"][0]
        first_check = next(iter(recommended["required_check_results"]))
        recommended["required_check_results"][first_check]["status"] = "unknown"
        result = validate_report(report, self.catalog)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("shortlisted candidate has unresolved checks" in finding for finding in result["findings"])
        )

    def test_alternate_with_unknown_check_fails_closed(self):
        report = self._valid_report()
        alternate = report["candidates"][1]
        first_check = next(iter(alternate["required_check_results"]))
        alternate["required_check_results"][first_check]["status"] = "unknown"
        result = validate_report(report, self.catalog)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("shortlisted candidate has unresolved checks" in finding for finding in result["findings"])
        )

    def test_search_result_url_and_missing_check_evidence_fail(self):
        report = self._valid_report()
        recommended = report["candidates"][0]
        recommended["product_url"] = "https://www.google.com/search?q=grow+light"
        first_check = next(iter(recommended["required_check_results"]))
        recommended["required_check_results"][first_check]["evidence_url"] = ""
        result = validate_report(report, self.catalog)
        self.assertFalse(result["ok"])
        self.assertTrue(any("direct http(s) product URL" in f for f in result["findings"]))
        self.assertTrue(any("lacks direct check evidence" in f for f in result["findings"]))

    def test_dedicated_openclaw_parser_exposes_only_read_only_commands(self):
        parser = build_read_only_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"plan", "search", "open", "extract", "validate"})
        self.assertFalse({"fill", "cart", "order", "pay", "gpio", "pump"} & set(choices))

    @patch.dict(
        "os.environ",
        {"OPENCLAW_WEB_SEARCH_PROVIDER": "duckduckgo", "BRAVE_SEARCH_API_KEY": ""},
        clear=False,
    )
    @patch("adapters.content.tools.httpx.get")
    def test_structured_search_returns_direct_result_urls(self, mock_get):
        class Response:
            text = """
            <div class="result">
              <a class="result__a"
                 href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fproduct">
                 Grow light
              </a>
              <a class="result__snippet">30W white grow light</a>
            </div>
            """

            def raise_for_status(self):
                return None

        mock_get.return_value = Response()
        result = structured_web_search("white grow light", count=3)
        self.assertTrue(result["ok"])
        self.assertEqual(result["results"][0]["url"], "https://example.com/product")
        self.assertNotIn("duckduckgo.com/html", result["results"][0]["url"])


if __name__ == "__main__":
    unittest.main()
