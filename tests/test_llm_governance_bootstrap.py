import unittest

import scripts.dispatch_llm_task_packet as dispatch_packet
import scripts.run_persona as run_persona


class LlmGovernanceBootstrapTests(unittest.TestCase):
    def test_dispatch_packet_prompt_includes_binding_governance(self):
        prompt = dispatch_packet._task_prompt(
            {
                "title": "test",
                "task_kind": "red_team",
                "objective": "review",
            },
            "gemini",
        )

        self.assertIn("HARNESS GOVERNANCE BOOTSTRAP", prompt)
        self.assertIn("CLAUDE.md", prompt)
        self.assertIn("docs/governance/LLM_GROUND_RULES.md", prompt)
        self.assertIn("scripts/agent_completion_guard.py", prompt)

    def test_persona_prompt_preamble_includes_binding_governance(self):
        self.assertIn("HARNESS GOVERNANCE BOOTSTRAP", run_persona.GOVERNANCE_BOOTSTRAP_PROMPT)
        self.assertIn("CLAUDE.md", run_persona.GOVERNANCE_BOOTSTRAP_PROMPT)
        self.assertIn("docs/governance/LLM_GROUND_RULES.md", run_persona.GOVERNANCE_BOOTSTRAP_PROMPT)
        self.assertIn("scripts/agent_completion_guard.py", run_persona.GOVERNANCE_BOOTSTRAP_PROMPT)


if __name__ == "__main__":
    unittest.main()
