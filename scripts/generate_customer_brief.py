import argparse
from datetime import datetime
from pathlib import Path

from core.database import execute_query


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def fetch_one(query: str, params: tuple) -> dict:
    rows = execute_query(query, params, fetch=True)
    if not rows:
        raise RuntimeError("required row not found")
    return rows[0]


def fetch_all(query: str, params: tuple) -> list[dict]:
    return execute_query(query, params, fetch=True) or []


def load_customer_bundle(external_ref: str) -> dict:
    profile = fetch_one(
        """
        SELECT *
        FROM customer_profiles
        WHERE external_ref = %s
        """,
        (external_ref,),
    )
    customer_id = profile["id"]
    now = datetime.now()

    interests = fetch_all(
        """
        SELECT tag, weight, source
        FROM customer_interest_tags
        WHERE customer_id = %s
        ORDER BY weight DESC, tag
        """,
        (customer_id,),
    )
    watchlists = fetch_all(
        """
        SELECT id, entity_type, entity_key, priority, reason
        FROM customer_watchlists
        WHERE customer_id = %s AND active = TRUE
        ORDER BY priority DESC, entity_type, entity_key
        """,
        (customer_id,),
    )
    questions = fetch_all(
        """
        SELECT DISTINCT ON (question)
            id, question, priority, status, due_at
        FROM customer_questions
        WHERE customer_id = %s AND status IN ('open', 'in_progress')
        ORDER BY
            question,
            CASE priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                ELSE 4
            END,
            CASE status
                WHEN 'open' THEN 1
                WHEN 'in_progress' THEN 2
                ELSE 3
            END,
            updated_at DESC,
            id DESC
        """,
        (customer_id,),
    )
    questions.sort(
        key=lambda row: (
            -_priority_rank(row.get("priority")),
            row.get("due_at") or datetime.max,
            row.get("id") or 0,
        )
    )
    memory = fetch_all(
        """
        SELECT DISTINCT ON (event_key)
            id, event_type, event_key, event_value, confidence
        FROM customer_memory_events
        WHERE customer_id = %s
        ORDER BY event_key, created_at DESC, id DESC
        LIMIT 5
        """,
        (customer_id,),
    )
    overrides = fetch_all(
        """
        SELECT DISTINCT ON (preference_key)
            id, preference_key, preference_value, scope, priority, expires_at
        FROM customer_preference_overrides
        WHERE customer_id = %s
          AND active = TRUE
          AND (expires_at IS NULL OR expires_at >= %s)
        ORDER BY
            preference_key,
            CASE priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                ELSE 4
            END,
            created_at DESC,
            id DESC
        """,
        (customer_id, now),
    )
    questions = _dedupe_rows(questions, ["question"])
    memory = _dedupe_rows(memory, ["event_key"])
    overrides = _dedupe_rows(overrides, ["preference_key"])
    upgrades = fetch_all(
        """
        SELECT id, product_name, upgrade_type, description
        FROM product_upgrade_events
        ORDER BY created_at DESC, id DESC
        LIMIT 20
        """,
        (),
    )
    persona = (profile.get("persona_type") or "general").lower()
    filtered_upgrades = []
    for row in upgrades:
        product_name = (row.get("product_name") or "").lower()
        if persona == "parent" and ("parent" in product_name or "weekly" in product_name or "generic" in product_name):
            filtered_upgrades.append(row)
        elif persona == "operator" and ("operator" in product_name or "inventory" in product_name or "generic" in product_name):
            filtered_upgrades.append(row)
        elif persona not in {"parent", "operator"}:
            filtered_upgrades.append(row)
    upgrades = filtered_upgrades[:5]
    return {
        "profile": profile,
        "interests": interests,
        "watchlists": watchlists,
        "questions": questions,
        "memory": memory,
        "overrides": overrides,
        "upgrades": upgrades,
    }


def _json_text(value) -> str:
    if isinstance(value, dict):
        if "summary" in value:
            return str(value["summary"])
        parts = [f"{k}={v}" for k, v in value.items()]
        return ", ".join(parts)
    return str(value)


def _dedupe_rows(rows: list[dict], key_fields: list[str]) -> list[dict]:
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for row in rows:
        key = tuple(str(row.get(field) or "").strip() for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _priority_rank(value: str | None) -> int:
    return {"urgent": 4, "high": 3, "medium": 2, "low": 1}.get((value or "").lower(), 1)


def _operator_scorecard(bundle: dict) -> list[str]:
    watchlists = bundle["watchlists"]
    memory = bundle["memory"]
    questions = bundle["questions"]
    comparison_pref = any(
        row.get("preference_key") == "opening_format"
        and "comparison_table_first" in _json_text(row.get("preference_value"))
        for row in bundle["overrides"]
    )
    brand_risk = any(row.get("event_key") == "brand_damage_risk" for row in memory)
    cash_goal = any(row.get("event_key") == "primary_goal" for row in memory)
    high_channels = sum(1 for row in watchlists if row.get("entity_type") == "channel")
    urgent_questions = sum(1 for row in questions if (row.get("priority") or "").lower() == "urgent")

    rows = [
        "| Dimension | Current signal | Read |",
        "| --- | --- | --- |",
        f"| Channel readiness | {high_channels} high-priority channels tracked | {'Strong' if high_channels >= 2 else 'Needs build'} |",
        f"| Cash recovery urgency | {'explicit 30-day recovery goal' if cash_goal else 'not clearly stated'} | {'Strong' if cash_goal else 'Needs clarification'} |",
        f"| Brand-risk sensitivity | {'brand damage concern captured' if brand_risk else 'no explicit caution found'} | {'High caution' if brand_risk else 'Normal'} |",
        f"| Decision speed | {urgent_questions} urgent question(s) open | {'Fast-cycle needed' if urgent_questions else 'Normal cadence'} |",
        f"| Delivery format fit | {'comparison-table-first override active' if comparison_pref else 'no comparison-table override'} | {'Matched' if comparison_pref else 'Gap'} |",
    ]
    return rows


def _parent_scorecard(bundle: dict) -> list[str]:
    watchlists = bundle["watchlists"]
    memory = bundle["memory"]
    overrides = bundle["overrides"]
    roadmap_focus = any("three_line_summary" in _json_text(row.get("preference_value")) for row in overrides)
    portfolio_focus = any(row.get("entity_key") == "drawing_portfolio" for row in watchlists)
    jargon_hesitation = any(row.get("event_key") == "too_much_jargon" for row in memory)

    rows = [
        "| Dimension | Current signal | Read |",
        "| --- | --- | --- |",
        f"| Short-term target clarity | {'애니고 watchlist active' if any(row.get('entity_key') == 'korea_animation_high_school' for row in watchlists) else 'short-term target unclear'} | {'Strong' if any(row.get('entity_key') == 'korea_animation_high_school' for row in watchlists) else 'Needs build'} |",
        f"| Portfolio emphasis | {'portfolio watch active' if portfolio_focus else 'portfolio focus weak'} | {'Strong' if portfolio_focus else 'Needs build'} |",
        f"| Parent readability need | {'jargon hesitation captured' if jargon_hesitation else 'no readability friction recorded'} | {'High importance' if jargon_hesitation else 'Normal'} |",
        f"| Mobile-first summary fit | {'three-line summary override active' if roadmap_focus else 'no mobile summary override'} | {'Matched' if roadmap_focus else 'Gap'} |",
    ]
    return rows


def _generic_scorecard(bundle: dict) -> list[str]:
    return [
        "| Dimension | Current signal | Read |",
        "| --- | --- | --- |",
        f"| Open questions | {len(bundle['questions'])} active | {'High' if bundle['questions'] else 'Low'} |",
        f"| Watchlist coverage | {len(bundle['watchlists'])} active targets | {'Good' if bundle['watchlists'] else 'Thin'} |",
        f"| Override intensity | {len(bundle['overrides'])} active overrides | {'Adaptive' if bundle['overrides'] else 'Default-only'} |",
    ]


def _scorecard_lines(bundle: dict) -> list[str]:
    persona = (bundle["profile"].get("persona_type") or "general").lower()
    if persona == "operator":
        return _operator_scorecard(bundle)
    if persona == "parent":
        return _parent_scorecard(bundle)
    return _generic_scorecard(bundle)


def _question_table_lines(questions: list[dict]) -> list[str]:
    lines = [
        "| Priority | Status | Question | Due |",
        "| --- | --- | --- | --- |",
    ]
    for row in questions:
        due = row["due_at"].strftime("%Y-%m-%d") if row.get("due_at") else "-"
        lines.append(f"| {row['priority']} | {row['status']} | {row['question']} | {due} |")
    return lines if len(lines) > 2 else ["- 열린 질문 없음"]


def _watchlist_table_lines(watchlists: list[dict]) -> list[str]:
    lines = [
        "| Entity Type | Entity Key | Priority | Why it matters |",
        "| --- | --- | --- | --- |",
    ]
    for row in watchlists:
        lines.append(f"| {row['entity_type']} | {row['entity_key']} | {row['priority']} | {row['reason']} |")
    return lines if len(lines) > 2 else ["- active watchlist 없음"]


def build_markdown(bundle: dict, title: str) -> str:
    profile = bundle["profile"]
    questions = bundle["questions"]
    watchlists = bundle["watchlists"]
    overrides = bundle["overrides"]
    memory = bundle["memory"]
    interests = bundle["interests"]
    upgrades = bundle["upgrades"]

    top_question = questions[0]["question"] if questions else "현재 고객의 최우선 질문 확인 필요"
    top_interest = interests[0]["tag"] if interests else "general"
    persona = profile.get("persona_type") or "general"

    summary = [
        f"1. 현재 최우선 과제는 `{top_question}`에 대한 실행 가능한 다음 단계 정리다.",
        f"2. 이 고객은 `{persona}` persona이며 현재 관심 축은 `{top_interest}` 중심으로 읽힌다.",
        f"3. 이번 브리프는 기본 profile보다 최신 override와 open question을 우선 반영해 조립됐다.",
    ]

    override_lines = [
        f"- `{row['preference_key']}`: {_json_text(row['preference_value'])} "
        f"(scope={row['scope']}, priority={row['priority']})"
        for row in overrides
    ] or ["- active override 없음"]
    question_lines = [
        f"- [{row['priority']}/{row['status']}] {row['question']}"
        + (f" (due: {row['due_at']:%Y-%m-%d})" if row.get("due_at") else "")
        for row in questions
    ] or ["- 열린 질문 없음"]
    watchlist_lines = [
        f"- `{row['entity_type']}` / `{row['entity_key']}`: {row['reason']}"
        for row in watchlists
    ] or ["- active watchlist 없음"]
    memory_lines = [
        f"- `{row['event_type']}` / `{row['event_key']}`: {_json_text(row['event_value'])}"
        for row in memory
    ] or ["- 누적 memory 없음"]
    interest_lines = [
        f"- `{row['tag']}` (weight={row['weight']})"
        for row in interests
    ] or ["- interest tag 없음"]
    upgrade_lines = [
        f"- `{row['product_name']}` / `{row['upgrade_type']}`: {row['description']}"
        for row in upgrades
    ] or ["- product upgrade event 없음"]

    next_actions = [
        "- 고객의 최우선 질문 기준으로 다음 리서치 태스크를 분해",
        "- watchlist 상위 3개 대상의 최신 자료를 확보",
        "- 다음 브리프에서 열린 질문 중 최소 1개를 answered 상태로 전환",
    ]
    scorecard_lines = _scorecard_lines(bundle)
    question_table_lines = _question_table_lines(questions)
    watchlist_table_lines = _watchlist_table_lines(watchlists)

    return "\n".join(
        [
            f"# {title}",
            "",
            "## 3-Line Summary",
            "",
            *summary,
            "",
            "## Customer Fit",
            "",
            f"- External ref: `{profile['external_ref']}`",
            f"- Persona: `{profile.get('persona_type')}`",
            f"- Tier: `{profile.get('tier')}`",
            f"- Preferred language: `{profile.get('preferred_language')}`",
            f"- Knowledge level: `{profile.get('knowledge_level')}`",
            f"- Preferred depth: `{profile.get('preferred_depth')}`",
            "",
            "## Active Overrides",
            "",
            *override_lines,
            "",
            "## Priority Questions",
            "",
            *question_table_lines,
            "",
            *question_lines,
            "",
            "## Watchlist",
            "",
            *watchlist_table_lines,
            "",
            *watchlist_lines,
            "",
            "## Customer Scorecard",
            "",
            *scorecard_lines,
            "",
            "## Interest Tags",
            "",
            *interest_lines,
            "",
            "## Memory Signals",
            "",
            *memory_lines,
            "",
            "## Reusable Product Upgrades",
            "",
            *upgrade_lines,
            "",
            "## Next Actions",
            "",
            *next_actions,
            "",
            "## Draft Note",
            "",
            "이 문서는 외부 자료 리서치 이전에 customer memory와 override를 기반으로 자동 조립된 초안이다.",
        ]
    )


def register_artifact(bundle: dict, title: str, output_path: Path) -> int:
    profile = bundle["profile"]
    report = execute_query(
        """
        INSERT INTO research_reports (
            title, report_type, audience, body, summary,
            sensitivity_level, requires_ceo_approval, status,
            source_signal_ids, cost_usd, published, created_at, updated_at
        )
        VALUES (%s, 'decision_brief', 'customer_specific', %s, %s,
                'low', FALSE, 'draft', '[]'::jsonb, 0.0, FALSE, NOW(), NOW())
        RETURNING id
        """,
        (
            title,
            f"See {output_path.relative_to(PROJECT_ROOT)}",
            f"{profile['external_ref']} personalized brief draft",
        ),
        fetch=True,
    )[0]
    report_id = report["id"]

    execute_query(
        """
        INSERT INTO artifact_memory_usage (
            artifact_type, artifact_id, customer_id, audience_scope, audience_key,
            memory_event_ids, override_ids, watchlist_ids, question_ids, upgrade_event_ids,
            usage_summary, qa_checked, created_at
        )
        VALUES (
            'research_report', %s, %s, 'individual', %s,
            (
                SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
                FROM customer_memory_events
                WHERE customer_id = %s
            ),
            (
                SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
                FROM customer_preference_overrides
                WHERE customer_id = %s AND active = TRUE
                  AND (expires_at IS NULL OR expires_at >= NOW())
            ),
            (
                SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
                FROM customer_watchlists
                WHERE customer_id = %s AND active = TRUE
            ),
            (
                SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
                FROM customer_questions
                WHERE customer_id = %s AND status IN ('open', 'in_progress')
            ),
            (
                SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
                FROM product_upgrade_events
            ),
            %s,
            FALSE,
            NOW()
        )
        """,
        (
            report_id,
            profile["id"],
            profile["external_ref"],
            profile["id"],
            profile["id"],
            profile["id"],
            profile["id"],
            f"Generated from profile/watchlist/questions/overrides for {profile['external_ref']}.",
        ),
    )

    execute_query(
        """
        UPDATE customer_questions
        SET last_answered_artifact_type = 'research_report',
            last_answered_artifact_id = %s,
            status = 'in_progress',
            updated_at = NOW()
        WHERE customer_id = %s
          AND status = 'open'
        """,
        (report_id, profile["id"]),
    )
    return report_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a customer-specific brief draft from customer memory tables.")
    parser.add_argument("external_ref")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default=None)
    parser.add_argument("--register-report", action="store_true")
    args = parser.parse_args()

    bundle = load_customer_bundle(args.external_ref)
    title = args.title or f"Customer Decision Brief - {args.external_ref}"
    markdown = build_markdown(bundle, title)
    output_path = args.output.resolve()
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote draft: {output_path}")

    if args.register_report:
        report_id = register_artifact(bundle, title, output_path)
        print(f"Registered research_report: {report_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
