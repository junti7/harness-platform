import argparse
import json
import re
import sys
from typing import Any

sys.path.insert(0, ".")

from adapters.content.slack_router import send_slack_route
from scripts.openclaw_codex_bridge import _gmail_search_runtime


EXCLUDE_PATTERNS = {
    "promotion": [
        r"sale",
        r"discount",
        r"offer",
        r"deal",
        r"promo",
        r"promotion",
        r"newsletter",
        r"unsubscribe",
        r"광고",
        r"프로모션",
        r"세일",
        r"할인",
    ],
    "social": [
        r"linkedin",
        r"x\.com",
        r"twitter",
        r"facebook",
        r"instagram",
        r"social",
        r"팔로우",
        r"좋아요",
        r"멘션",
    ],
    "forum": [
        r"forum",
        r"community",
        r"reddit",
        r"discuss",
        r"thread",
        r"토론",
        r"포럼",
        r"커뮤니티",
    ],
    "system_update": [
        r"password",
        r"sign-in",
        r"signin",
        r"security alert",
        r"verification",
        r"receipt",
        r"invoice",
        r"billing alert",
        r"noreply",
        r"no-reply",
        r"do-not-reply",
        r"system update",
        r"notification",
        r"인증",
        r"보안",
        r"영수증",
        r"알림",
        r"업데이트",
    ],
}


def _matches_any(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def _classify(item: dict[str, Any]) -> str | None:
    haystack = " ".join(
        [
            str(item.get("from") or ""),
            str(item.get("subject") or ""),
            " ".join(item.get("labels") or []),
        ]
    )
    for category, patterns in EXCLUDE_PATTERNS.items():
        if _matches_any(haystack, patterns):
            return category
    return None


def _render_summary(query: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return (
            "최근 수신된 메일 중 회사 경영에 관련된 메일은 없습니다.\n"
            f"- 검색 조건: `{query}`"
        )

    lines = [
        "대표 Gmail 경영 관련 메일 요약",
        f"- 검색 조건: `{query}`",
        f"- 포함 건수: {len(items)}",
        "",
    ]
    for item in items:
        lines.append(f"- {item.get('date') or '-'} | {item.get('from') or '-'} | {item.get('subject') or '(제목 없음)'}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Gmail for recent management-relevant mail and post a concise Slack summary.")
    parser.add_argument("--query", default="newer_than:1d")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--route", default="exec_president_decisions")
    args = parser.parse_args()

    payload = _gmail_search_runtime(args.query, args.limit)
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        category = _classify(item)
        if category is None:
            kept.append(item)
        else:
            item = dict(item)
            item["excluded_as"] = category
            excluded.append(item)

    summary = _render_summary(args.query, kept[:5])
    send_slack_route(args.route, {"text": summary})
    result = {
        "ok": True,
        "query": args.query,
        "route": args.route,
        "reported": len(kept[:5]),
        "kept_total": len(kept),
        "excluded_total": len(excluded),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
