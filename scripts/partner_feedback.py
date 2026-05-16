import argparse
import sys
from typing import Optional

sys.path.insert(0, ".")

from core.database import execute_query


VALID_MARKET_READS = {"hot", "unclear", "weak", "relationship_opportunity"}
VALID_ACTIONS = {"none", "more_research", "customer_framing", "outreach_material", "ceo_review"}


def record_partner_feedback(
    target_type: str,
    target_id: int,
    market_read: str,
    trust_temperature: Optional[str],
    relationship_leverage: Optional[str],
    timing_read: Optional[str],
    emotional_resonance: Optional[str],
    buyer_hesitation: Optional[str],
    analog_notes: Optional[str],
    requested_action: str,
    human_review_required: bool,
):
    if market_read not in VALID_MARKET_READS:
        raise ValueError(f"market_read must be one of: {', '.join(sorted(VALID_MARKET_READS))}")
    if requested_action not in VALID_ACTIONS:
        raise ValueError(f"requested_action must be one of: {', '.join(sorted(VALID_ACTIONS))}")

    execute_query(
        """
        INSERT INTO partner_feedback (
            partner_name,
            target_type,
            target_id,
            market_read,
            trust_temperature,
            relationship_leverage,
            timing_read,
            emotional_resonance,
            buyer_hesitation,
            analog_notes,
            requested_action,
            human_review_required
        )
        VALUES ('Vice President', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            target_type,
            target_id,
            market_read,
            trust_temperature,
            relationship_leverage,
            timing_read,
            emotional_resonance,
            buyer_hesitation,
            analog_notes,
            requested_action,
            human_review_required,
        ),
    )


def main():
    parser = argparse.ArgumentParser(description="Record Vice President market-sense feedback.")
    parser.add_argument(
        "target_type",
        choices=["signal", "refined_output", "research_report", "newsletter_issue", "content_review"],
    )
    parser.add_argument("target_id", type=int)
    parser.add_argument("market_read", choices=sorted(VALID_MARKET_READS))
    parser.add_argument("--trust-temperature", default=None)
    parser.add_argument("--relationship-leverage", default=None)
    parser.add_argument("--timing-read", default=None)
    parser.add_argument("--emotional-resonance", default=None)
    parser.add_argument("--buyer-hesitation", default=None)
    parser.add_argument("--analog-notes", default=None)
    parser.add_argument("--requested-action", choices=sorted(VALID_ACTIONS), default="none")
    parser.add_argument("--human-review-required", action="store_true")
    args = parser.parse_args()

    record_partner_feedback(
        args.target_type,
        args.target_id,
        args.market_read,
        args.trust_temperature,
        args.relationship_leverage,
        args.timing_read,
        args.emotional_resonance,
        args.buyer_hesitation,
        args.analog_notes,
        args.requested_action,
        args.human_review_required,
    )
    print(f"Recorded Vice President feedback: {args.target_type}#{args.target_id} -> {args.market_read}")


if __name__ == "__main__":
    main()
