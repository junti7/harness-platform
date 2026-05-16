WITH customer_ref AS (
    SELECT id
    FROM customer_profiles
    WHERE external_ref = 'demo-parent-animation-001'
),
insert_report AS (
    INSERT INTO research_reports (
        title,
        report_type,
        audience,
        body,
        summary,
        sensitivity_level,
        requires_ceo_approval,
        status,
        source_signal_ids,
        cost_usd,
        published,
        notion_page_id,
        published_at,
        created_at,
        updated_at
    )
    VALUES (
        'Parent Decision Brief #001 - Animation High School to Hongik Roadmap',
        'decision_brief',
        'customer_specific',
        'See docs/issues/parent_customer_decision_brief_001_2026-05-13.md',
        '중3 학부모 고객의 애니고 진학 및 홍대 장기 목표를 위한 12개월 실행 로드맵 브리프.',
        'low',
        FALSE,
        'draft',
        '[]'::jsonb,
        0.0,
        FALSE,
        NULL,
        NULL,
        NOW(),
        NOW()
    )
    RETURNING id
)
INSERT INTO artifact_memory_usage (
    artifact_type,
    artifact_id,
    customer_id,
    audience_scope,
    audience_key,
    memory_event_ids,
    override_ids,
    watchlist_ids,
    question_ids,
    upgrade_event_ids,
    usage_summary,
    qa_checked,
    created_at
)
SELECT
    'research_report',
    insert_report.id,
    customer_ref.id,
    'individual',
    'demo-parent-animation-001',
    (
        SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
        FROM customer_memory_events
        WHERE customer_id = customer_ref.id
          AND event_key IN ('student_strength', 'too_much_jargon', 'mobile_first')
    ),
    (
        SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
        FROM customer_preference_overrides
        WHERE customer_id = customer_ref.id
          AND active = TRUE
    ),
    (
        SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
        FROM customer_watchlists
        WHERE customer_id = customer_ref.id
          AND active = TRUE
    ),
    (
        SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
        FROM customer_questions
        WHERE customer_id = customer_ref.id
          AND status = 'open'
    ),
    (
        SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
        FROM product_upgrade_events
        WHERE product_name = 'parent_decision_brief'
    ),
    '부모 고객의 모바일 우선 선호, 쉬운 표현 요구, 애니고 중심 focus shift를 반영해 3줄 결론/로드맵/watchlist 구조로 작성했다.',
    FALSE,
    NOW()
FROM customer_ref, insert_report;
