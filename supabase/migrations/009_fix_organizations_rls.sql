-- ============================================================
-- Migration 009: Fix organizations RLS for dashboard queries
-- Allow users to see orgs they are members of, not just current_org_id()
-- ============================================================

-- Drop the overly restrictive policy
DROP POLICY IF EXISTS organizations_self_access ON organizations;

-- Create a new policy: users can see orgs they are members of
CREATE POLICY organizations_member_access ON organizations FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM org_members
      WHERE org_members.org_id = organizations.id
        AND org_members.user_id = auth.uid()
        AND org_members.is_active = TRUE
    )
  );

-- Allow service role to access all organizations (for backend operations)
CREATE POLICY organizations_service_role ON organizations FOR ALL
  USING (auth.role() = 'service_role');
