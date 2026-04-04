-- ============================================================
-- Verification script for flow_presentations RLS
-- Run in Supabase SQL Editor with service_role
-- ============================================================

-- 1. Service role can insert into any org
INSERT INTO flow_presentations (org_id, flow_type, presentation_config)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'TestFlow',
  '{"card": {"title": {"from": "$.test"}}}'::jsonb
);

-- 2. With org context: sees only its own rows
SELECT set_config('app.org_id', '00000000-0000-0000-0000-000000000001', true);
SELECT count(*) as org_a_count FROM flow_presentations
WHERE flow_type = 'TestFlow';
-- Expected: 1

-- 3. With different org context: sees nothing
SELECT set_config('app.org_id', '00000000-0000-0000-0000-000000000002', true);
SELECT count(*) as org_b_count FROM flow_presentations
WHERE flow_type = 'TestFlow';
-- Expected: 0

-- 4. Cleanup
DELETE FROM flow_presentations WHERE flow_type = 'TestFlow';
