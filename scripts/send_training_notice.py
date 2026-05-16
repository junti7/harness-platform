import argparse
import sys

sys.path.insert(0, ".")

from adapters.content.slack_router import send_slack_route


DAY_1_NOTICE = """오늘부터 부대표 OJT를 `Physical AI Weekly` 콘텐츠 검토 중심으로 시작합니다. 1일차 목표는 전문 B2B 영업이 아니라, 일반 한국어 독자가 읽을 수 있는 콘텐츠인지 판단하고 paid subscriber 전환을 막는 심리적 저항을 파악하는 것입니다.

오늘 할 일:
- issue sample 1개 읽기
- 이해 안 되는 부분 3개 표시
- 제목 후보 3개 중 가장 클릭하고 싶은 제목 선택
- 유료 구독이라면 추가로 받고 싶은 정보 1개 작성
- `capital_action_approve`만 실제 돈 집행 승인이라는 원칙

통과 기준:
- quiz 4/5 이상
- review note 제출
- jargon 또는 어려운 문장 3개 이상 표시
- 제목/lead 개선안 1개 이상 작성
- paid hesitation 가설 1개 이상 작성

HR Training Team은 결과를 기록하고, 주간 진행 요약을 대표에게 보고합니다."""


def build_payload() -> dict:
    return {
        "text": "Vice President OJT Day 1 - Content Review Gate",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Vice President OJT Day 1",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Module:* Content Review Gate\n*Owner:* HR Training Team\n*Report Line:* President",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": DAY_1_NOTICE,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Full plan: docs/VICE_PRESIDENT_OJT_PROGRAM.md",
                    }
                ],
            },
        ],
    }


def render_text() -> str:
    return "# Vice President OJT Day 1 - Content Review Gate\n\n" + DAY_1_NOTICE


def main() -> int:
    parser = argparse.ArgumentParser(description="Send or preview Vice President OJT Slack notice.")
    parser.add_argument("--channel", choices=["text", "slack"], default="text")
    args = parser.parse_args()

    if args.channel == "text":
        print(render_text())
        return 0

    send_slack_route("vp_content_review", build_payload())
    print("Sent Vice President OJT Day 1 notice to Slack")
    return 0


if __name__ == "__main__":
    sys.exit(main())
