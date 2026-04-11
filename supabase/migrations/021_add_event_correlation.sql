-- ============================================================
-- Migration 021: Add correlation_id to domain_events
-- Purpose: Enable high-performance tracing for Run Transcripts
-- ============================================================

-- 1. Add column
ALTER TABLE domain_events 
    ADD COLUMN IF NOT EXISTS correlation_id TEXT;

-- 2. Create composite index for performance
CREATE INDEX IF NOT EXISTS idx_domain_events_correlation 
    ON domain_events(org_id, correlation_id);

-- 3. Backfill from tasks table where possible (Optional but recommended)
-- This logic assumes aggregate_type='task' and aggregate_id matches tasks.id
UPDATE domain_events de
SET correlation_id = t.correlation_id
FROM tasks t
WHERE de.aggregate_type = 'task'
  AND de.aggregate_id = t.id::text
  AND de.correlation_id IS NULL;

-- 4. Comment on column for team visibility
COMMENT ON COLUMN domain_events.correlation_id IS 'External identifier for tracing across related services and events.';
