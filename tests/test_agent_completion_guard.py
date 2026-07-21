import json
import tempfile
import unittest
from pathlib import Path

from scripts.agent_completion_guard import validate


class AgentCompletionGuardTests(unittest.TestCase):
    def _bootstrap(self):
        return [
            {
                "path": "CLAUDE.md",
                "read_at": "2026-06-28T14:30:00+09:00",
                "summary": "Read Harness operating directive and real verification completion rule.",
            },
            {
                "path": "docs/governance/LLM_GROUND_RULES.md",
                "read_at": "2026-06-28T14:30:00+09:00",
                "summary": "Read common LLM ground rules and completion guard requirements.",
            },
        ]

    def test_blocks_mock_only_complete_closeout(self):
        data = {
            "task": "edu coach answer fix",
            "status": "complete",
            "governance_bootstrap": self._bootstrap(),
            "verification": [
                {
                    "name": "mock pilot",
                    "target": "unit",
                    "command": "patch.object(...); pytest",
                    "result": "passed",
                    "mock": True,
                }
            ],
        }

        errors = validate(data, base_dir=Path.cwd(), require_deploy=False, require_red_team=False)

        self.assertTrue(any("real user-facing/runtime entrypoint" in error for error in errors))
        self.assertTrue(any("mock-only" in error for error in errors))
        self.assertTrue(any("status=complete" in error for error in errors))

    def test_requires_governance_bootstrap_before_completion(self):
        data = {
            "task": "edu coach answer fix",
            "status": "complete",
            "verification": [
                {
                    "name": "macmini service health",
                    "target": "macmini api",
                    "command": "curl http://127.0.0.1:8000/api/health",
                    "result": "ok",
                }
            ],
        }

        errors = validate(data, base_dir=Path.cwd(), require_deploy=False, require_red_team=False)

        self.assertTrue(any("governance_bootstrap" in error for error in errors))
        self.assertTrue(any("CLAUDE.md" in error for error in errors))
        self.assertTrue(any("LLM_GROUND_RULES.md" in error for error in errors))

    def test_requires_claude_and_independent_second_model_when_red_team_requested(self):
        data = {
            "task": "policy change",
            "status": "complete",
            "governance_bootstrap": self._bootstrap(),
            "verification": [
                {
                    "name": "macmini service health",
                    "target": "macmini api",
                    "command": "curl http://127.0.0.1:8000/api/health",
                    "result": "ok",
                }
            ],
            "red_team": {
                "models": ["Claude"],
                "artifacts": [],
                "verdict": "red_team_clear",
            },
        }

        errors = validate(data, base_dir=Path.cwd(), require_deploy=False, require_red_team=True)

        self.assertTrue(any("Claude plus" in error for error in errors))
        self.assertTrue(any("artifacts" in error for error in errors))

    def test_accepts_real_entrypoint_deploy_and_two_model_red_team_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "claude.md").write_text("clear", encoding="utf-8")
            (base / "copilot.md").write_text("clear", encoding="utf-8")
            data = {
                "task": "edu coach answer fix",
                "status": "complete",
                "governance_bootstrap": self._bootstrap(),
                "verification": [
                    {
                        "name": "macmini production answer check",
                        "target": "macmini api",
                        "command": "curl http://127.0.0.1:8000/api/health",
                        "result": "answer includes source link and no markdown leak",
                    }
                ],
                "deploy": {
                    "method": "scripts/deploy_to_macmini.sh harness-os/backend/main.py",
                    "result": "deployed and service restarted",
                },
                "red_team": {
                    "models": ["Claude", "Copilot"],
                    "artifacts": [{"artifact": "claude.md"}, {"artifact": "copilot.md"}],
                    "verdict": "red_team_clear",
                },
            }

            errors = validate(data, base_dir=base, require_deploy=True, require_red_team=True)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
