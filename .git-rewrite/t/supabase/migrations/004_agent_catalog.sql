-- ============================================================
-- Migration 004: Agent Catalog (Phase 3)
--   Defines specialized agent personalities and configurations.
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_catalog (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role          TEXT NOT NULL,          -- e.g. "analyst", "processor", "reviewer"
    is_active     BOOLEAN DEFAULT TRUE,
    soul_json     JSONB NOT NULL DEFAULT '{}', -- personality: role, goal, backstory
    allowed_tools TEXT[] DEFAULT '{}',    -- list of tool names from registry
    max_iter      INTEGER DEFAULT 5,      -- Rule R8 limit
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, role)
);

-- RLS: tenant isolation
ALTER TABLE agent_catalog ENABLE ROW LEVEL SECURITY;

CREATE POLICY "agent_catalog_tenant_isolation" ON agent_catalog
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

-- Index for fast lookup by role
CREATE INDEX IF NOT EXISTS idx_agent_catalog_org_role 
    ON agent_catalog(org_id, role) WHERE is_active = TRUE;
