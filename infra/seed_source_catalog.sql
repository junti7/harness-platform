INSERT INTO source_catalog (
    source_name,
    source_type,
    base_url,
    reliability_score,
    expected_signal_type,
    collection_cost,
    rate_limit_policy,
    enabled
)
VALUES
    ('arXiv_robotics', 'rss', 'https://rss.arxiv.org/rss/cs.RO', 0.90, 'research', 'free', '{"stale_minutes": 10080}'::jsonb, TRUE),
    ('arXiv_AI', 'rss', 'https://rss.arxiv.org/rss/cs.AI', 0.85, 'research', 'free', '{"stale_minutes": 10080}'::jsonb, TRUE),
    ('arXiv_ML', 'rss', 'https://rss.arxiv.org/rss/cs.LG', 0.85, 'research', 'free', '{"stale_minutes": 10080}'::jsonb, TRUE),
    ('IEEE_Spectrum', 'rss', 'https://spectrum.ieee.org/feeds/feed.rss', 0.80, 'industry_news', 'free', '{"stale_minutes": 4320}'::jsonb, TRUE),
    ('MIT_Tech_Review', 'rss', 'https://www.technologyreview.com/feed/', 0.80, 'industry_news', 'free', '{"stale_minutes": 2880}'::jsonb, TRUE),
    ('TechCrunch_robotics', 'rss', 'https://techcrunch.com/tag/robotics/feed/', 0.65, 'startup_news', 'free', '{"stale_minutes": 4320}'::jsonb, TRUE),
    ('Boston_Dynamics', 'rss', 'https://feeds.feedburner.com/BostonDynamics', 0.75, 'company_blog', 'free', '{"stale_minutes": 43200}'::jsonb, TRUE)
ON CONFLICT (source_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    base_url = EXCLUDED.base_url,
    reliability_score = EXCLUDED.reliability_score,
    expected_signal_type = EXCLUDED.expected_signal_type,
    collection_cost = EXCLUDED.collection_cost,
    rate_limit_policy = EXCLUDED.rate_limit_policy,
    enabled = EXCLUDED.enabled,
    updated_at = NOW();
