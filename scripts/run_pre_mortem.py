"""
T-10: Pre-Mortem CLI

사용법:
  python scripts/run_pre_mortem.py --type paid_offer --decision "9900원 유료 구독 런칭"
  python scripts/run_pre_mortem.py --type capital_action --decision "AWS 서버 월 50달러 계약"
  python scripts/run_pre_mortem.py --type paid_offer --decision "..." --context "현재 무료 구독자 50명"

결과: docs/governance/pre_mortem/{TYPE}-NA-{date}.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from core.logger import HarnessLogger
from adapters.content.pre_mortem import run_pre_mortem, HIGH_IMPACT_TYPES


def main():
    parser = argparse.ArgumentParser(description="Pre-Mortem 분석 생성")
    parser.add_argument("--type", required=True, choices=sorted(HIGH_IMPACT_TYPES),
                        help="의사결정 유형")
    parser.add_argument("--decision", required=True, help="결정 내용 설명")
    parser.add_argument("--context", default="", help="추가 맥락")
    parser.add_argument("--target-id", type=int, default=None, help="관련 DB id (선택)")
    args = parser.parse_args()

    logger = HarnessLogger(tier=4, correlation_id="pre-mortem")
    logger.info(f"=== Pre-Mortem 시작: {args.type} ===")

    result = run_pre_mortem(
        decision_target=args.decision,
        decision_type=args.type,
        context=args.context,
        target_id=args.target_id,
        logger=logger,
    )

    a = result["analysis"]
    print(f"\n{'=' * 60}")
    print(f"결정: {args.decision}")
    print(f"위험 수준: {a.get('overall_risk', 'N/A').upper()}")
    print(f"권고: {a.get('go_no_go_recommendation', 'N/A')}")
    if a.get("conditions_if_conditional"):
        print(f"조건: {a['conditions_if_conditional']}")
    print(f"\n결론: {a.get('executive_summary', '')[:200]}")
    print(f"\n시나리오 {len(a.get('scenarios', []))}개:")
    for s in a.get("scenarios", []):
        print(f"  [{s.get('probability', 0):.0%}] {s.get('scenario', '')} — {s.get('recoverability', '')}")
    print(f"\n메모: {result['memo_path']}")
    print(f"승인: {'✅ pre_mortem_approve' if result['approved'] else '❌ pre_mortem_block (critical risk)'}")


if __name__ == "__main__":
    main()
