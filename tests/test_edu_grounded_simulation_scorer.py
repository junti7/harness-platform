import unittest

from scripts.score_edu_grounded_simulations import parse_simulation_markdown, score_cases


SAMPLE_MARKDOWN = """
# Sample

## Case 1. grounded case

- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | Math anxiety and AI | 수학 불안이 큰 학생일수록 AI 답안 의존이 커진다는 연구입니다. | https://example.com/1
  - [EvidenceAnchor] `연구` | App review caution | 학습앱이 틀린 답을 당당하게 제시할 수 있다는 부모 후기입니다. | urn:test:2

### 12-turn Simulation

1. **고객**: 아이가 수학 숙제할 때 AI 답부터 봐요.
2. **서비스**: 수학 불안이 큰 학생일수록 AI 답안 의존이 커진다는 연구가 있어서, 지금은 불안-회피 루프를 먼저 끊는 게 중요합니다.
3. **고객**: 그럼 어떻게 하죠?
4. **서비스**: 오늘은 학습앱 답을 그대로 믿지 말고, 10분 자력 시도 뒤에 첫 단서만 보게 하세요.

### What This Shows About P1

## Case 2. generic case

- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | Career anxiety | AI 불안이 자기효능감을 떨어뜨린다는 연구입니다. | https://example.com/3

### 12-turn Simulation

1. **고객**: 커리어가 불안해요.
2. **서비스**: 많이들 그러세요. 천천히 생각해 보시면 좋겠습니다.
3. **고객**: 뭘 해야 하죠?
4. **서비스**: 충분히 이해합니다. 차근차근 해보세요.

### What This Shows About P1
"""


class EduGroundedSimulationScorerTests(unittest.TestCase):
    def test_parser_extracts_cases_evidence_and_turns(self):
        cases = parse_simulation_markdown(SAMPLE_MARKDOWN)
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0].title, "Case 1. grounded case")
        self.assertEqual(len(cases[0].evidence_items), 2)
        self.assertEqual(len(cases[0].turns), 4)

    def test_grounded_case_scores_higher_than_generic_case(self):
        report = score_cases(parse_simulation_markdown(SAMPLE_MARKDOWN))
        first, second = report["results"]
        self.assertGreater(first["total_score"], second["total_score"])
        self.assertEqual(first["verdict"], "clear")
        self.assertEqual(second["verdict"], "weak")
        self.assertGreater(first["metrics"]["grounded_turn_ratio"], second["metrics"]["grounded_turn_ratio"])


if __name__ == "__main__":
    unittest.main()
