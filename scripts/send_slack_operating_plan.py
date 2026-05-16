import argparse
import sys

sys.path.insert(0, ".")

from adapters.content.slack_router import send_slack_route


ANNOUNCEMENT = """Slack을 Phase 1 creator subscription 운영 구조에 맞게 재편합니다. 앞으로 Slack은 `Physical AI Weekly` 발행 승인, 부대표 콘텐츠 검토, 운영 incident를 관리하는 최소 command surface로 사용합니다.

Phase 1 active 채널:
- 대표 의사결정: `#exec-president-decisions`
- 부대표 콘텐츠 검토: `#vp-content-review`
- 실패/권한/비용 incident: `#ops-incidents`

나머지 채널은 routing target으로 유지하지만, 첫 외부 매출 전에는 daily operation을 3개 채널 중심으로 제한합니다.

운영 원칙:
- 대표 채널에는 중간 로그를 보내지 않습니다.
- 부대표 채널에는 긴 원문을 기본 노출하지 않고 issue draft review만 보냅니다.
- HR Training은 교육, 평가, 대표 보고를 분리합니다.
- Codex, GitHub Copilot CLI, Claude, Gemini, GPT reasoning, local models, OpenClaw는 역할별 채널에서 작업 상태와 검토 결과를 남깁니다.
- 실제 비용/투자/자본 집행 후보도 Phase 1에서는 `#exec-president-decisions`에서만 다룹니다.
- API key, webhook, secret 값은 Slack에 쓰지 않습니다.

현재는 Slack Bot Token mode에서 실제 채널 라우팅이 가능합니다. 단, 사업 우선순위는 채널 확장이 아니라 weekly issue 발행, 무료 구독자 50명, paid subscriber 1명입니다."""


def build_payload() -> dict:
    return {
        "text": "Harness Slack Operating System Reset",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Harness Slack Operating System Reset",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ANNOUNCEMENT,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Full spec: docs/SLACK_OPERATING_SYSTEM.md",
                    }
                ],
            },
        ],
    }


def render_text() -> str:
    return "# Harness Slack Operating System Reset\n\n" + ANNOUNCEMENT


def main() -> int:
    parser = argparse.ArgumentParser(description="Send or preview the Harness Slack operating plan.")
    parser.add_argument("--channel", choices=["text", "slack"], default="text")
    args = parser.parse_args()

    if args.channel == "text":
        print(render_text())
        return 0

    send_slack_route("exec_president_decisions", build_payload())
    print("Sent Slack operating plan announcement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
