WITH upsert_customer AS (
    INSERT INTO customer_profiles (
        external_ref,
        email_hash,
        tier,
        persona_type,
        country,
        timezone,
        preferred_language,
        knowledge_level,
        preferred_depth,
        consent_marketing,
        consent_personalization
    )
    VALUES (
        'demo-parent-animation-001',
        md5('demo-parent-animation-001@example.com'),
        'paid',
        'parent',
        'KR',
        'Asia/Seoul',
        'ko',
        'beginner',
        'plain',
        TRUE,
        TRUE
    )
    ON CONFLICT (external_ref) DO UPDATE
    SET
        tier = EXCLUDED.tier,
        persona_type = EXCLUDED.persona_type,
        preferred_language = EXCLUDED.preferred_language,
        knowledge_level = EXCLUDED.knowledge_level,
        preferred_depth = EXCLUDED.preferred_depth,
        consent_marketing = EXCLUDED.consent_marketing,
        consent_personalization = EXCLUDED.consent_personalization,
        updated_at = NOW()
    RETURNING id
),
customer_ref AS (
    SELECT id FROM upsert_customer
    UNION ALL
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-parent-animation-001'
    LIMIT 1
)
INSERT INTO customer_interest_tags (customer_id, tag, weight, source, updated_at)
SELECT id, tag, weight, source, NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        ('animation_school', 1.0, 'demo_seed'),
        ('portfolio', 0.9, 'demo_seed'),
        ('hongik_university', 0.8, 'demo_seed'),
        ('middle_school_roadmap', 0.8, 'demo_seed')
) AS v(tag, weight, source)
ON CONFLICT (customer_id, tag) DO UPDATE
SET
    weight = EXCLUDED.weight,
    source = EXCLUDED.source,
    updated_at = NOW();

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-parent-animation-001'
)
INSERT INTO customer_watchlists (
    customer_id,
    entity_type,
    entity_key,
    priority,
    reason,
    active,
    created_at,
    updated_at
)
SELECT id, entity_type, entity_key, priority, reason, TRUE, NOW(), NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        ('school', 'korea_animation_high_school', 'high', '애니고 전형/포트폴리오 기준 추적'),
        ('university', 'hongik_university_fine_arts', 'high', '최종 진학 목표'),
        ('skill', 'drawing_portfolio', 'high', '실기/포트폴리오 경쟁력 핵심'),
        ('channel', 'portfolio_academy_options', 'medium', '외부 교육 옵션 비교')
) AS v(entity_type, entity_key, priority, reason)
ON CONFLICT (customer_id, entity_type, entity_key) DO UPDATE
SET
    priority = EXCLUDED.priority,
    reason = EXCLUDED.reason,
    active = TRUE,
    updated_at = NOW();

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-parent-animation-001'
)
INSERT INTO customer_questions (
    customer_id,
    question,
    status,
    priority,
    topic_tags,
    sensitivity_level,
    due_at,
    created_at,
    updated_at
)
SELECT
    id,
    question,
    'open',
    priority,
    topic_tags::jsonb,
    'low',
    due_at::timestamp,
    NOW(),
    NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        (
            '중3 기준으로 한국애니메이션고등학교 진학 가능성을 높이기 위한 12개월 로드맵은 무엇인가?',
            'urgent',
            '["animation_school","roadmap","middle_school"]',
            '2026-05-20 18:00:00'
        ),
        (
            '홍익대학교 진학까지 고려했을 때 지금부터 포트폴리오 준비를 어떻게 역산해야 하는가?',
            'high',
            '["hongik_university","portfolio","long_term_strategy"]',
            '2026-05-25 18:00:00'
        )
) AS v(question, priority, topic_tags, due_at)
WHERE NOT EXISTS (
    SELECT 1
    FROM customer_questions q
    WHERE q.customer_id = id
      AND q.question = v.question
);

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-parent-animation-001'
)
INSERT INTO customer_memory_events (
    customer_id,
    event_type,
    event_key,
    event_value,
    source_channel,
    confidence,
    sensitivity_level,
    expires_at,
    created_at
)
SELECT
    id,
    event_type,
    event_key,
    event_value::jsonb,
    source_channel,
    confidence,
    sensitivity_level,
    expires_at::timestamp,
    NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        (
            'consulting_note',
            'student_strength',
            '{"summary":"그림 실력이 상대적으로 강점이며 장기 목표는 홍익대학교다."}',
            'demo_seed',
            0.9,
            'low',
            NULL
        ),
        (
            'hesitation',
            'too_much_jargon',
            '{"summary":"기술적 표현보다 단계별 실행 일정과 학교별 비교를 원한다."}',
            'demo_seed',
            0.9,
            'low',
            '2026-06-13 00:00:00'
        ),
        (
            'feedback',
            'mobile_first',
            '{"summary":"모바일에서 바로 이해되는 요약을 먼저 보여줘야 한다."}',
            'demo_seed',
            0.8,
            'low',
            '2026-06-13 00:00:00'
        )
) AS v(event_type, event_key, event_value, source_channel, confidence, sensitivity_level, expires_at);
WHERE NOT EXISTS (
    SELECT 1
    FROM customer_memory_events e
    WHERE e.customer_id = id
      AND e.event_type = v.event_type
      AND e.event_key = v.event_key
);

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-parent-animation-001'
)
INSERT INTO customer_preference_overrides (
    customer_id,
    preference_key,
    preference_value,
    scope,
    source,
    confidence,
    priority,
    effective_from,
    expires_at,
    active,
    created_at,
    updated_at
)
SELECT
    id,
    preference_key,
    preference_value::jsonb,
    scope,
    source,
    confidence,
    priority,
    NOW(),
    expires_at::timestamp,
    TRUE,
    NOW(),
    NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        (
            'opening_format',
            '{"type":"three_line_summary"}',
            'brief',
            'demo_seed',
            0.9,
            'high',
            '2026-05-20 18:00:00'
        ),
        (
            'tone',
            '{"style":"plain_parent_friendly"}',
            'campaign',
            'demo_seed',
            0.9,
            'high',
            '2026-06-13 18:00:00'
        ),
        (
            'focus_shift',
            '{"current_focus":"animation_high_school_admission_over_university_theory"}',
            'brief',
            'demo_seed',
            0.8,
            'high',
            '2026-05-20 18:00:00'
        )
) AS v(preference_key, preference_value, scope, source, confidence, priority, expires_at);
WHERE NOT EXISTS (
    SELECT 1
    FROM customer_preference_overrides o
    WHERE o.customer_id = id
      AND o.preference_key = v.preference_key
      AND o.preference_value = v.preference_value::jsonb
      AND o.active = TRUE
);

WITH source_customer AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-parent-animation-001'
)
INSERT INTO product_upgrade_events (
    product_name,
    artifact_type,
    artifact_id,
    source_event_ids,
    source_feedback_ids,
    upgrade_type,
    description,
    applied_to_products,
    created_by,
    created_at
)
SELECT
    'parent_decision_brief',
    'research_report',
    NULL,
    (
        SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
        FROM customer_memory_events
        WHERE customer_id = source_customer.id
          AND event_key IN ('too_much_jargon', 'mobile_first')
    ),
    '[]'::jsonb,
    'format_change',
    '부모 고객용 브리프는 3줄 결론, 일정표, watchlist를 우선 노출하고 전문용어를 줄인다.',
    '["parent_decision_brief","weekly_parent_update"]'::jsonb,
    'Product Planning Agent',
    NOW()
FROM source_customer
WHERE NOT EXISTS (
    SELECT 1
    FROM product_upgrade_events
    WHERE product_name = 'parent_decision_brief'
      AND upgrade_type = 'format_change'
      AND description = '부모 고객용 브리프는 3줄 결론, 일정표, watchlist를 우선 노출하고 전문용어를 줄인다.'
);
