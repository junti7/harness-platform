import argparse
import json
import sys

sys.path.insert(0, ".")

from adapters.content.decision_card import card_to_json
from adapters.content.mobile_dispatcher import build_slack_payload, send_decision_card


def main():
    parser = argparse.ArgumentParser(description="Send or preview a mobile decision card.")
    parser.add_argument("target_type", choices=["signal", "refined_output", "research_report"])
    parser.add_argument("target_id", type=int)
    parser.add_argument("--channel", choices=["slack", "text", "json", "slack-json"], default="text")
    args = parser.parse_args()

    if args.channel == "slack-json":
        result = send_decision_card(args.target_type, args.target_id, channel="json")
        print(json.dumps(build_slack_payload(result["card"]), ensure_ascii=False, indent=2, default=str))
        return

    result = send_decision_card(args.target_type, args.target_id, channel=args.channel)
    if args.channel == "text":
        print(result["text"])
    elif args.channel == "json":
        print(card_to_json(result["card"]))
    else:
        print(f"Sent decision card to {result['channel']}: {args.target_type}#{args.target_id}")


if __name__ == "__main__":
    main()
