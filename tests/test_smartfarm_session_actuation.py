import importlib.util
import os
import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def _load_backend_main():
    path = Path(__file__).resolve().parents[1] / "harness-os" / "backend" / "main.py"
    module_name = "harness_backend_main_smartfarm_session_test"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _SafeRuntime:
    def control_guard(self, _zone_id):
        return nullcontext()

    def pump_safety(self, _zone_id, _duration_s, *, test_mode=False):
        return (test_mode, "clear" if test_mode else "actuation_disabled", "esp8266-zone2")

    def create_command(self, **kwargs):
        return {"command_id": "test-command", "status": "created", **kwargs}


class SmartfarmSessionActuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = _load_backend_main()
        cls.client = TestClient(cls.main.app)

    def setUp(self):
        self.env_patch = patch.dict(
            os.environ,
            {
                "HARNESS_OS_SECRET_KEY": "test-smartfarm-secret",
                "HARNESS_SMARTFARM_PUMP_TEST_ENABLED": "true",
            },
        )
        self.env_patch.start()
        base = {"X-Harness-Secret": "test-smartfarm-secret"}
        self.ceo_headers = {**base, "X-Harness-Auth": self.main._issue_role_auth_token("ceo")}
        self.vp_headers = {**base, "X-Harness-Auth": self.main._issue_role_auth_token("vp")}
        self.runtime_patch = patch.object(self.main, "get_smartfarm_runtime", return_value=_SafeRuntime())
        self.runtime_patch.start()

    def tearDown(self):
        self.runtime_patch.stop()
        self.env_patch.stop()

    def test_only_logged_in_ceo_can_issue_session_actuation_token(self):
        self.assertEqual(self.client.post("/api/smartfarm/actuation/session-token").status_code, 401)
        self.assertEqual(
            self.client.post("/api/smartfarm/actuation/session-token", headers=self.vp_headers).status_code,
            403,
        )
        issued = self.client.post("/api/smartfarm/actuation/session-token", headers=self.ceo_headers)
        self.assertEqual(issued.status_code, 200)
        self.assertTrue(issued.json()["actuation_nonce"])

    def test_pump_test_token_is_single_use_without_password_reentry(self):
        issued = self.client.post("/api/smartfarm/actuation/session-token", headers=self.ceo_headers)
        payload = {
            "action": "test",
            "duration_s": 3,
            "confirmation": "zone2",
            "actuation_nonce": issued.json()["actuation_nonce"],
        }
        first = self.client.post("/api/smartfarm/zones/zone2/pump", headers=self.ceo_headers, json=payload)
        replay = self.client.post("/api/smartfarm/zones/zone2/pump", headers=self.ceo_headers, json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(replay.status_code, 403)


if __name__ == "__main__":
    unittest.main()
