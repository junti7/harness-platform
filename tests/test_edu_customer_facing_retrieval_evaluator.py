import unittest
from unittest.mock import patch

from scripts.evaluate_edu_customer_facing_retrieval import evaluate_case, evaluate_cases
from scripts.score_edu_grounded_simulations import parse_simulation_markdown


SAMPLE_MARKDOWN = """
## Case 1. grounded case

- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | Math anxiety and AI | 수학 불안이 큰 학생일수록 AI 답안 의존이 커진다는 연구입니다. | https://example.com/1
  - [EvidenceAnchor] `연구` | App review caution | 학습앱이 틀린 답을 당당하게 제시할 수 있다는 부모 후기입니다. | urn:test:2

### 12-turn Simulation

1. **고객**: 아이가 수학 숙제할 때 AI 답부터 봐요.
2. **서비스**: 수학 불안과 답안 의존이 보입니다.
3. **고객**: 그럼 어떻게 하죠?
4. **서비스**: 학습앱 답을 그대로 믿지 않게 하세요.

### What This Shows About P1
"""


class _BackendStub:
    def __init__(self, bundle):
        self.bundle = bundle

    def _edu_db_customer_facing_bundle(self, query, segment, k=4):
        return self.bundle


class EduCustomerFacingRetrievalEvaluatorTests(unittest.TestCase):
    def test_evaluate_case_scores_matching_bundle_high(self):
        case = parse_simulation_markdown(SAMPLE_MARKDOWN)[0]
        backend = _BackendStub(
            {
                "items": [
                    {
                        "source": "ERIC Education Research",
                        "title": "Math anxiety and AI dependency",
                        "cite": "수학 불안이 큰 학생일수록 AI 답안 의존이 커진다는 연구입니다.",
                    },
                    {
                        "source": "EvidenceAnchor parent review",
                        "title": "App review caution",
                        "cite": "학습앱이 틀린 답을 당당하게 제시할 수 있다는 부모 후기입니다.",
                    },
                ]
            }
        )
        result = evaluate_case(case, backend, k=4, db_ready=True)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["score"], 70)
        self.assertEqual(result["verdict"], "clear")

    def test_evaluate_cases_reports_errors_when_bundle_unavailable(self):
        case = parse_simulation_markdown(SAMPLE_MARKDOWN)
        backend = _BackendStub(None)
        with patch("scripts.evaluate_edu_customer_facing_retrieval._load_backend_main", return_value=backend):
            report = evaluate_cases(case, k=4)
        self.assertEqual(report["summary"]["error_count"], 1)
        self.assertEqual(report["summary"]["ok_count"], 0)


if __name__ == "__main__":
    unittest.main()
