import unittest

from agents.registry import find_mentioned_personas, get_persona


class RegistryTests(unittest.TestCase):
    def test_ledger_persona_is_registered_and_active(self):
        persona = get_persona("ledger")

        self.assertEqual(persona.team_ko, "재무팀 (CFO)")
        self.assertEqual(persona.channel_env, "SLACK_CHANNEL_TEAM_LEDGER")
        self.assertTrue(persona.active)

    def test_find_mentioned_personas_matches_ledger_by_name_and_team(self):
        by_name = find_mentioned_personas("Ledger님, 이번 달 burn rate 봐주세요.")
        by_team = find_mentioned_personas("재무팀 의견도 같이 듣고 싶어요.")

        self.assertTrue(any(p.handle == "ledger" for p in by_name))
        self.assertTrue(any(p.handle == "ledger" for p in by_team))


if __name__ == "__main__":
    unittest.main()
