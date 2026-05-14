-- T-07: 마케팅 포스트 추적 테이블

CREATE TABLE IF NOT EXISTS marketing_posts (
    id                   SERIAL PRIMARY KEY,
    newsletter_issue_id  INTEGER REFERENCES newsletter_issues(id) ON DELETE SET NULL,
    platform             VARCHAR(50)  NOT NULL,  -- 'x', 'linkedin', 'substack_note'
    content              TEXT         NOT NULL,
    public_url           TEXT,
    posted_at            TIMESTAMP    DEFAULT NOW(),
    impressions          INTEGER      DEFAULT 0,
    clicks               INTEGER      DEFAULT 0,
    status               VARCHAR(30)  DEFAULT 'draft',  -- 'draft', 'posted', 'failed'
    error_message        TEXT
);

CREATE INDEX IF NOT EXISTS idx_marketing_posts_issue
    ON marketing_posts(newsletter_issue_id, platform);

CREATE INDEX IF NOT EXISTS idx_marketing_posts_platform
    ON marketing_posts(platform, posted_at DESC);
