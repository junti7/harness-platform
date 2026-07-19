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
                    "id": candidates[0]["id"], "score": 74, "reason": "점수가 부족함",
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
            self.assertIn("LLM 보수점수 75점 미만", result["rejected"][0]["reason"])

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
