import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def _load_backend_main():
    path = Path(__file__).resolve().parents[1] / "harness-os" / "backend" / "main.py"
    module_name = "harness_backend_main_recommerce_api_test"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class RecommerceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = _load_backend_main()
        cls.client = TestClient(cls.main.app)

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.tempdir.name) / "workspace.json"
        self.env_patch = patch.dict(os.environ, {"HARNESS_OS_SECRET_KEY": "test-recommerce-secret"})
        self.env_patch.start()
        self.base_headers = {"X-Harness-Secret": "test-recommerce-secret"}
        self.ceo_headers = {**self.base_headers, "X-Harness-Auth": self.main._issue_role_auth_token("ceo")}
        self.vp_headers = {**self.base_headers, "X-Harness-Auth": self.main._issue_role_auth_token("vp")}
        self.path_patch = patch.object(self.main, "RECOMMERCE_WORKSPACE_PATH", self.workspace_path)
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.env_patch.stop()
        self.tempdir.cleanup()

    def test_auth_and_role_boundaries(self):
        self.assertEqual(self.client.get("/api/recommerce/workspace").status_code, 401)
        self.assertEqual(self.client.get("/api/recommerce/workspace", headers=self.vp_headers).status_code, 200)
        denied = self.client.post(
            "/api/recommerce/workspace",
            headers=self.vp_headers,
            json={"expected_version": 0, "action": "set_weekly_hours", "payload": {"hours": 2}},
        )
        self.assertEqual(denied.status_code, 403)

    def test_feature_fails_closed_when_secret_is_not_configured(self):
        with patch.dict(os.environ, {"HARNESS_OS_SECRET_KEY": ""}):
            denied = self.client.get("/api/recommerce/workspace", headers=self.vp_headers)
        self.assertEqual(denied.status_code, 503)

    def test_ceo_write_and_stale_version_conflict(self):
        saved = self.client.post(
            "/api/recommerce/workspace",
            headers=self.ceo_headers,
            json={"expected_version": 0, "action": "set_weekly_hours", "payload": {"hours": 2}},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["workspace_version"], 1)
        conflict = self.client.post(
            "/api/recommerce/workspace",
            headers=self.ceo_headers,
            json={"expected_version": 0, "action": "set_weekly_hours", "payload": {"hours": 3}},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"]["workspace"]["metrics"]["weekly_hours"], 2)

    def test_market_research_is_readable_by_vp_but_refresh_is_ceo_only(self):
        with patch.object(self.main, "load_market_research", return_value={"status": "not_run", "candidates": []}):
            read = self.client.get("/api/recommerce/market-research", headers=self.vp_headers)
        self.assertEqual(read.status_code, 200)
        denied = self.client.post("/api/recommerce/market-research/refresh", headers=self.vp_headers)
        self.assertEqual(denied.status_code, 403)
        with patch.object(self.main, "run_market_research", return_value={"status": "training_shortlist_not_purchase_recommendation", "candidates": []}):
            refreshed = self.client.post("/api/recommerce/market-research/refresh", headers=self.ceo_headers)
        self.assertEqual(refreshed.status_code, 200)


if __name__ == "__main__":
    unittest.main()
