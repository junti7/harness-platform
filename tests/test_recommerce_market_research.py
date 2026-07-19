import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.recommerce_market_research import CANDIDATES, load_market_research, run_market_research


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"total": 123, "items": [{"lprice": "10000", "mallName": "mall", "title": "<b>상품</b>"}]}


class _Client:
    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, *_args, **_kwargs):
        return _Response()


class RecommerceMarketResearchTests(unittest.TestCase):
    def test_refresh_writes_three_ranked_training_candidates(self):
        with tempfile.TemporaryDirectory() as tempdir, patch("core.recommerce_market_research.httpx.Client", _Client):
            path = Path(tempdir) / "research.json"
            result = run_market_research(path, client_id="id", client_secret="secret")
            self.assertEqual(len(result["candidates"]), 3)
            self.assertEqual(result["candidates"][0]["id"], CANDIDATES[0]["id"])
            self.assertEqual(load_market_research(path)["candidates"][0]["median_price"], 10000)

    def test_missing_snapshot_is_truthfully_not_run(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self.assertEqual(load_market_research(Path(tempdir) / "missing.json")["status"], "not_run")


if __name__ == "__main__":
    unittest.main()
