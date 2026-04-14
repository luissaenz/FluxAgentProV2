-- ============================================================
-- Migration 025: Update agent_catalog RLS to modern pattern
--   Adds service_role bypass (consistent with mig010+)
--   Required for MCP server tools (list_agents, get_agent_detail)
-- ============================================================

-- Drop old policy (mig004 pattern: current_setting without service_role bypass)
DROP POLICY IF EXISTS "agent_catalog_tenant_isolation" ON agent_catalog;

-- Recreate with modern pattern (mig010+)
CREATE POLICY "agent_catalog_tenant_isolation" ON agent_catalog
    FOR ALL USING (
        auth.role() = 'service_role'
        OR org_id::text = current_org_id()
    );
