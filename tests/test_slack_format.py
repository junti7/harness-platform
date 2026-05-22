import unittest

from adapters.content.slack_format import to_slack_mrkdwn


class SlackFormatTests(unittest.TestCase):
    def test_wide_markdown_table_renders_as_wrapped_code_table(self):
        source = """| # | 액션 | Owner | 조건 |
|---|---|---|---|
| A | 개인정보 처리방침 + 동의 절차 초안 작성 | KITT님 | **무료 구독 폼 런칭 전** 완료 필수. 폼 런칭 일정 확정 즉시 KITT님에게 공유 |
| B | 구독 약관·환불정책·카피 disclaimer 초안 작성 | KITT님 | A와 병렬 진행. Paid 전환 실험 진입 전 legal_review_approve 준비 |"""

        rendered = to_slack_mrkdwn(source)

        self.assertTrue(rendered.startswith("```\n| #"))
        self.assertIn("개인정보 처리방침 + 동의 절차", rendered)
        self.assertIn("무료 구독 폼 런칭 전 완료", rendered)
        self.assertNotIn("|---|", rendered)
        self.assertNotIn("• Owner:", rendered)


if __name__ == "__main__":
    unittest.main()
