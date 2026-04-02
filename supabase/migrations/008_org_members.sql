-- ============================================================
-- Migration 008: org_members + RLS + Realtime support
-- Phase 5: Dashboard multi-tenancy with role-based access
-- ============================================================

-- -----------------------------------------------------------
-- 1. org_members (user-org-role relationship)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS org_members (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  email      TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'org_operator'
             CHECK (role IN ('fap_admin', 'org_owner', 'org_operator')),
  is_active  BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, user_id)
);

ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------
-- 2. Helper function: break RLS recursion for admin check
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION is_fap_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM org_members
    WHERE user_id = auth.uid() AND role = 'fap_admin'
  );
$$ LANGUAGE sql SECURITY DEFINER;

-- -----------------------------------------------------------
-- 3. RLS policies for org_members
-- -----------------------------------------------------------

-- SELECT: user sees own membership + fap_admin sees all
CREATE POLICY "own_membership_select" ON org_members FOR SELECT
  USING (
    user_id = auth.uid()
    OR is_fap_admin()
  );

-- INSERT: only fap_admin or org_owner of the same org
CREATE POLICY "org_members_insert" ON org_members FOR INSERT
  WITH CHECK (
    is_fap_admin()
    OR EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid()
        AND m.org_id = org_id
        AND m.role = 'org_owner'
        AND m.is_active = TRUE
    )
  );

-- UPDATE: only fap_admin
CREATE POLICY "org_members_update" ON org_members FOR UPDATE
  USING (is_fap_admin());

-- DELETE: only fap_admin
CREATE POLICY "org_members_delete" ON org_members FOR DELETE
  USING (is_fap_admin());

-- -----------------------------------------------------------
-- 4. Enable REPLICA IDENTITY FULL for Realtime support
-- -----------------------------------------------------------
ALTER TABLE tasks REPLICA IDENTITY FULL;
ALTER TABLE pending_approvals REPLICA IDENTITY FULL;
ALTER TABLE domain_events REPLICA IDENTITY FULL;
