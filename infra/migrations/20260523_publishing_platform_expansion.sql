-- Migration: Publishing Platform Column Expansion
-- Date: 2026-05-23
-- Author: TARS (AR-20260522-003)
-- Purpose: Expand publishing_platform column to support multiple platform integrations

BEGIN;

-- 1. Expand publishing_platform column (VARCHAR(50) → VARCHAR(255))
ALTER TABLE newsletter_issues
    ALTER COLUMN publishing_platform SET DATA TYPE VARCHAR(255);

-- 2. Add index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_newsletter_issues_platform
    ON newsletter_issues(publishing_platform, status, issue_date DESC);

COMMIT;
