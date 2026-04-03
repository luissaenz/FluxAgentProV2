-- ============================================================
-- Migration 010: Allow service_role to bypass RLS policies
-- For backend operations that need to work with service_key
-- ============================================================

-- Drop existing policies and recreate with service_role bypass
DROP POLICY IF EXISTS "own_membership_select" ON org_members;
DROP POLICY IF EXISTS "org_members_insert" ON org_members;
DROP POLICY IF EXISTS "org_members_update" ON org_members;
DROP POLICY IF EXISTS "org_members_delete" ON org_members;

-- SELECT: user sees own membership + fap_admin sees all + service_role sees all
CREATE POLICY "own_membership_select" ON org_members FOR SELECT
  USING (
    auth.role() = 'service_role'
    OR user_id = auth.uid()
    OR is_fap_admin()
  );

-- INSERT: only fap_admin or org_owner of the same org + service_role
CREATE POLICY "org_members_insert" ON org_members FOR INSERT
  WITH CHECK (
    auth.role() = 'service_role'
    OR is_fap_admin()
    OR EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid()
        AND m.org_id = org_id
        AND m.role = 'org_owner'
        AND m.is_active = TRUE
    )
  );

-- UPDATE: only fap_admin + service_role
CREATE POLICY "org_members_update" ON org_members FOR UPDATE
  USING (auth.role() = 'service_role' OR is_fap_admin());

-- DELETE: only fap_admin + service_role
CREATE POLICY "org_members_delete" ON org_members FOR DELETE
  USING (auth.role() = 'service_role' OR is_fap_admin());

-- Allow service_role to bypass RLS on pending_approvals
DROP POLICY IF EXISTS "tenant_isolation_pending_approvals" ON pending_approvals;
CREATE POLICY "tenant_isolation_pending_approvals" ON pending_approvals
    FOR ALL USING (
      auth.role() = 'service_role'
      OR org_id::text = current_org_id()
    );

-- Allow service_role to bypass RLS on domain_events (for INSERT)
DROP POLICY IF EXISTS "tenant_insert_domain_events" ON domain_events;
DROP POLICY IF EXISTS "tenant_select_domain_events" ON domain_events;

CREATE POLICY "tenant_insert_domain_events" ON domain_events
    FOR INSERT WITH CHECK (
      auth.role() = 'service_role'
      OR org_id::text = current_org_id()
    );

CREATE POLICY "tenant_select_domain_events" ON domain_events
    FOR SELECT USING (
      auth.role() = 'service_role'
      OR org_id::text = current_org_id()
    );

-- Allow service_role to bypass RLS on other core tables
DROP POLICY IF EXISTS "tasks_org_access" ON tasks;
CREATE POLICY "tasks_org_access" ON tasks
    FOR ALL
    USING (
      auth.role() = 'service_role'
      OR org_id::text = current_org_id()
    );

DROP POLICY IF EXISTS "snapshots_org_access" ON snapshots;
CREATE POLICY "snapshots_org_access" ON snapshots
    FOR ALL
    USING (
      auth.role() = 'service_role'
      OR org_id::text = current_org_id()
    );
