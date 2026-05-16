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
        'demo-operator-inventory-001',
        md5('demo-operator-inventory-001@example.com'),
        'paid',
        'operator',
        'KR',
        'Asia/Seoul',
        'ko',
        'intermediate',
        'structured',
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
)
INSERT INTO customer_interest_tags (customer_id, tag, weight, source, updated_at)
SELECT id, tag, weight, 'demo_seed', NOW()
FROM upsert_customer
CROSS JOIN (
    VALUES
        ('inventory_clearance', 1.0),
        ('pricing_strategy', 0.9),
        ('channel_mix', 0.85),
        ('cash_recovery', 0.8)
) AS v(tag, weight)
ON CONFLICT (customer_id, tag) DO UPDATE
SET weight = EXCLUDED.weight, source = EXCLUDED.source, updated_at = NOW();

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-operator-inventory-001'
)
INSERT INTO customer_watchlists (
    customer_id, entity_type, entity_key, priority, reason, active, created_at, updated_at
)
SELECT id, entity_type, entity_key, priority, reason, TRUE, NOW(), NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        ('sku_group', 'slow_moving_top_20', 'high', '회수율이 낮은 부진 SKU 묶음'),
        ('channel', 'live_commerce', 'high', '30일 내 소진용 빠른 판매 채널'),
        ('channel', 'closed_b2b_dump', 'high', '브랜드 노출 최소화 현금화 채널'),
        ('metric', 'gross_margin_floor', 'high', '손실 허용 한계선')
) AS v(entity_type, entity_key, priority, reason)
ON CONFLICT (customer_id, entity_type, entity_key) DO UPDATE
SET priority = EXCLUDED.priority, reason = EXCLUDED.reason, active = TRUE, updated_at = NOW();

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-operator-inventory-001'
)
INSERT INTO customer_questions (
    customer_id, question, status, priority, topic_tags, sensitivity_level, due_at, created_at, updated_at
)
SELECT id, question, 'open', priority, topic_tags::jsonb, 'low', due_at::timestamp, NOW(), NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        (
            '부진 재고 5억을 30일 안에 현금화하려면 어떤 채널 조합과 가격 가드레일이 필요한가?',
            'urgent',
            '["inventory_clearance","channel_mix","pricing_strategy"]',
            '2026-05-16 18:00:00'
        ),
        (
            '브랜드 훼손을 최소화하면서도 회수율을 높일 수 있는 비공개 판매 옵션은 무엇인가?',
            'high',
            '["cash_recovery","closed_b2b","brand_risk"]',
            '2026-05-18 18:00:00'
        )
) AS v(question, priority, topic_tags, due_at)
WHERE NOT EXISTS (
    SELECT 1 FROM customer_questions q
    WHERE q.customer_id = id AND q.question = v.question
);

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-operator-inventory-001'
)
INSERT INTO customer_memory_events (
    customer_id, event_type, event_key, event_value, source_channel, confidence, sensitivity_level, expires_at, created_at
)
SELECT id, event_type, event_key, event_value::jsonb, 'demo_seed', confidence, 'low', expires_at::timestamp, NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        ('consulting_note', 'primary_goal', '{"summary":"최우선 목표는 30일 내 현금 회수이며, 단기 손익보다 재고 부담 제거를 더 중시한다."}', 0.9, NULL),
        ('hesitation', 'brand_damage_risk', '{"summary":"노골적인 할인 노출은 브랜드 가치 훼손 우려가 커서 비공개 채널 선호가 높다."}', 0.9, '2026-06-13 00:00:00'),
        ('feedback', 'table_first', '{"summary":"긴 설명보다 채널별 회수율/브랜드리스크/실행속도 비교표를 먼저 원한다."}', 0.85, '2026-06-13 00:00:00')
    ) AS v(event_type, event_key, event_value, confidence, expires_at)
WHERE NOT EXISTS (
    SELECT 1 FROM customer_memory_events e
    WHERE e.customer_id = id
      AND e.event_type = v.event_type
      AND e.event_key = v.event_key
);

WITH customer_ref AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-operator-inventory-001'
)
INSERT INTO customer_preference_overrides (
    customer_id, preference_key, preference_value, scope, source, confidence, priority, effective_from, expires_at, active, created_at, updated_at
)
SELECT id, preference_key, preference_value::jsonb, scope, 'demo_seed', confidence, priority, NOW(), expires_at::timestamp, TRUE, NOW(), NOW()
FROM customer_ref
CROSS JOIN (
    VALUES
        ('opening_format', '{"type":"comparison_table_first"}', 'brief', 0.9, 'high', '2026-05-20 18:00:00'),
        ('tone', '{"style":"operator_plain"}', 'campaign', 0.9, 'high', '2026-06-13 18:00:00'),
        ('focus_shift', '{"current_focus":"inventory_liquidation_over_long_term_brand_story"}', 'brief', 0.85, 'high', '2026-05-20 18:00:00')
    ) AS v(preference_key, preference_value, scope, confidence, priority, expires_at)
WHERE NOT EXISTS (
    SELECT 1 FROM customer_preference_overrides o
    WHERE o.customer_id = id
      AND o.preference_key = v.preference_key
      AND o.preference_value = v.preference_value::jsonb
      AND o.active = TRUE
);

WITH source_customer AS (
    SELECT id FROM customer_profiles WHERE external_ref = 'demo-operator-inventory-001'
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
    'inventory_operator_brief',
    'research_report',
    NULL,
    (
        SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb)
        FROM customer_memory_events
        WHERE customer_id = source_customer.id
          AND event_key IN ('brand_damage_risk', 'table_first')
    ),
    '[]'::jsonb,
    'format_change',
    '운영자 고객용 브리프는 채널 비교표, 브랜드 리스크, 현금 회수 우선순위를 먼저 보여준다.',
    '["inventory_operator_brief","inventory_weekly_update"]'::jsonb,
    'Product Planning Agent',
    NOW()
FROM source_customer
WHERE NOT EXISTS (
    SELECT 1
    FROM product_upgrade_events
    WHERE product_name = 'inventory_operator_brief'
      AND upgrade_type = 'format_change'
      AND description = '운영자 고객용 브리프는 채널 비교표, 브랜드 리스크, 현금 회수 우선순위를 먼저 보여준다.'
);
