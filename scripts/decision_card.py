import argparse
import sys

sys.path.insert(0, ".")

from adapters.content.decision_card import build_decision_card, card_to_json, render_mobile_text


def main():
    parser = argparse.ArgumentParser(description="Render a mobile decision card payload.")
    parser.add_argument("target_type", choices=["signal", "refined_output", "research_report"])
    parser.add_argument("target_id", type=int)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    card = build_decision_card(args.target_type, args.target_id)
    if args.format == "json":
        print(card_to_json(card))
    else:
        print(render_mobile_text(card))


if __name__ == "__main__":
    main()
