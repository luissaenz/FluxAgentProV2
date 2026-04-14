-- Migration 026: Add requires_approval flag to tasks
-- Used for trazability of HITL tasks.

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN DEFAULT FALSE;

-- Index for filtering tasks requiring approval
CREATE INDEX IF NOT EXISTS idx_tasks_requires_approval ON tasks(requires_approval) WHERE requires_approval = TRUE;
