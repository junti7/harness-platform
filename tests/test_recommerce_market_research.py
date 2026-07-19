import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.recommerce_market_research import load_market_research, run_market_research


class _Response:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "total": 123,
            "items": [
                {
                    "lprice": str(20_000 + index * 1_000),
                    "mallName": f"mall-{index}",
                    "title": "모듈 서랍 정리 트레이 6개 세트",
                    "productId": str(index + 1),
                    "link": f"https://example.com/{index}",
                    "image": f"https://example.com/{index}.jpg",
                    "category1": "생활/건강",
                    "category3": "수납/정리용품",
                    "category4": "정리함",
                }
                for index in range(6)
            ],
        }


class _Client:
    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, *_args, **_kwargs):
        return _Response()


def _select_first(candidates):
    return ({
        "status": "selected",
        "selected": [{
            "id": candidates[0]["id"],
            "score": 90,
            "reason": "경쟁가격 표본과 판매처 분산이 하드게이트를 충족",
            "risks": ["배송비 별도 검증 필요"],
            "training_goal": "동일상품 총 결제가격과 공급가를 검증",
        }],
        "rejected": [],
    }, {"provider": "ollama", "model": "test-model", "required": True})


class RecommerceMarketResearchTests(unittest.TestCase):
    def test_refresh_requires_llm_and_writes_evidence_selected_target(self):
        with tempfile.TemporaryDirectory() as tempdir, patch("core.recommerce_market_research.httpx.Client", _Client):
            path = Path(tempdir) / "research.json"
            result = run_market_research(path, client_id="id", client_secret="secret", llm_selector=_select_first)
            self.assertEqual(result["status"], "llm_selected_ojt_targets_not_purchase_recommendation")
            self.assertEqual(len(result["candidates"]), 1)
            self.assertEqual(result["candidates"][0]["llm_score"], 90)
            self.assertGreaterEqual(result["candidates"][0]["sample_size"], 5)
            self.assertEqual(result["candidates"][0]["commercial_readiness"], "blocked_until_supplier_and_shipping_evidence")
            self.assertFalse(result["selection_policy"]["human_manual_selection_allowed"])
            self.assertEqual(load_market_research(path)["llm"]["provider"], "ollama")

    def test_llm_failure_fails_closed_without_candidates(self):
        def fail(_candidates):
            raise RuntimeError("local model offline")

        with tempfile.TemporaryDirectory() as tempdir, patch("core.recommerce_market_research.httpx.Client", _Client):
            result = run_market_research(
                Path(tempdir) / "research.json",
                client_id="id",
                client_secret="secret",
                llm_selector=fail,
            )
            self.assertEqual(result["status"], "selection_blocked_llm_unavailable")
            self.assertEqual(result["candidates"], [])
            self.assertEqual(result["llm"]["error"], "RuntimeError")

    def test_low_llm_score_is_blocked_even_when_market_evidence_exists(self):
        def weak_selector(candidates):
            return ({
                "status": "selected",
                "selected": [{
                    "id": candidates[0]["id"], "score": 69, "reason": "점수가 부족함",
                    "risks": ["근거 부족"], "training_goal": "선정 보류를 이해",
                }],
                "rejected": [],
            }, {"provider": "ollama", "model": "test-model", "required": True})

        with tempfile.TemporaryDirectory() as tempdir, patch("core.recommerce_market_research.httpx.Client", _Client):
            result = run_market_research(
                Path(tempdir) / "research.json", client_id="id", client_secret="secret", llm_selector=weak_selector,
            )
            self.assertEqual(result["status"], "selection_blocked_no_evidence_qualified_product")
            self.assertEqual(result["candidates"], [])
            self.assertIn("LLM 보수점수 70점 미만", result["rejected"][0]["reason"])

    def test_adaptive_profile_selects_only_after_strict_profile_has_zero_candidates(self):
        adaptive_candidate = {
            "id": "adaptive-target", "product_id": "123", "name": "동일 규격 정리함 세트",
            "query": "정리함", "category": "정리함", "category1": "생활/건강", "image_url": "https://example.com/a.jpg",
            "market_low_price": 18_400, "market_link": "https://example.com/a", "mall_name": "mall-a",
            "sample_size": 31, "sample_mall_count": 25, "price_p25": 18_400, "price_p75": 34_920,
            "median_price": 21_860, "result_count": 31, "competitor_samples": [],
        }

        def select_adaptive(_candidates):
            return ({
                "status": "selected",
                "selected": [{
                    "id": "adaptive-target", "score": 90, "reason": "표본은 충분하나 가격분산을 주의",
                    "risks": ["배송비 별도 검증"], "training_goal": "공급가 상한을 확인",
                }],
                "rejected": [],
            }, {"provider": "ollama", "model": "test-model", "required": True})

        with tempfile.TemporaryDirectory() as tempdir, \
                patch("core.recommerce_market_research.httpx.Client", _Client), \
                patch("core.recommerce_market_research._candidate_pool", return_value=([adaptive_candidate], [], [])):
            result = run_market_research(
                Path(tempdir) / "research.json", client_id="id", client_secret="secret", llm_selector=select_adaptive,
            )
            self.assertEqual(len(result["candidates"]), 1)
            self.assertEqual(result["candidates"][0]["selection_profile"], "adaptive_1")
            self.assertTrue(result["selection_result"]["adaptive"])
            self.assertEqual(result["selection_result"]["strict_candidate_count"], 0)

    def test_near_duplicate_llm_choices_are_not_shown_as_two_ojt_products(self):
        base = {
            "product_id": "123", "query": "정리함", "category": "정리함", "category1": "생활/건강",
            "image_url": "https://example.com/a.jpg", "market_low_price": 20_000, "market_link": "https://example.com/a",
            "mall_name": "mall-a", "sample_size": 10, "sample_mall_count": 4, "price_p25": 20_000,
            "price_p75": 24_000, "median_price": 22_000, "result_count": 10, "competitor_samples": [],
        }
        candidates = [
            {**base, "id": "one", "name": "양면 34칸 소형 부품 정리함 탈착식 칸막이"},
            {**base, "id": "two", "product_id": "456", "name": "양면 34칸 소형 부품 정리함 탈착식 칸막이 세트"},
        ]

        def select_both(_candidates):
            return ({"status": "selected", "selected": [
                {"id": "one", "score": 90, "reason": "첫 후보", "risks": [], "training_goal": "조사"},
                {"id": "two", "score": 90, "reason": "중복 후보", "risks": [], "training_goal": "조사"},
            ], "rejected": []}, {"provider": "ollama", "model": "test-model", "required": True})

        with tempfile.TemporaryDirectory() as tempdir, \
                patch("core.recommerce_market_research.httpx.Client", _Client), \
                patch("core.recommerce_market_research._candidate_pool", return_value=(candidates, [], [])):
            result = run_market_research(Path(tempdir) / "research.json", client_id="id", client_secret="secret", llm_selector=select_both)
            self.assertEqual(len(result["candidates"]), 1)
            self.assertEqual(result["candidates"][0]["id"], "one")

    def test_source_failure_replaces_snapshot_with_selection_hold(self):
        class BrokenClient(_Client):
            def get(self, *_args, **_kwargs):
                raise RuntimeError("source offline")

        with tempfile.TemporaryDirectory() as tempdir, patch("core.recommerce_market_research.httpx.Client", BrokenClient):
            result = run_market_research(Path(tempdir) / "research.json", client_id="id", client_secret="secret")
            self.assertEqual(result["status"], "selection_blocked_source_unavailable")
            self.assertEqual(result["candidates"], [])
            self.assertEqual(result["llm"]["error_detail"], "not_called_source_unavailable")

    def test_missing_snapshot_is_truthfully_not_run(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self.assertEqual(load_market_research(Path(tempdir) / "missing.json")["status"], "not_run")


if __name__ == "__main__":
    unittest.main()
