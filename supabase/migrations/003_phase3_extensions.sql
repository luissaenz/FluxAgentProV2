-- ============================================================
-- Migration 003: Phase 3 extensions
--   1. Add embedding_version column to memory_vectors
--   2. Create org_mcp_servers table
-- ============================================================

-- -----------------------------------------------------------
-- 1. Add embedding_version to memory_vectors
--    Tracks which model produced each embedding (enables future migration)
-- -----------------------------------------------------------
ALTER TABLE memory_vectors
  ADD COLUMN IF NOT EXISTS embedding_version TEXT DEFAULT 'text-embedding-3-small';

CREATE INDEX IF NOT EXISTS idx_memory_version
  ON memory_vectors(org_id, embedding_version);

-- -----------------------------------------------------------
-- 2. MCP server configuration per organisation
--    One MCP server can be shared by multiple agents in an org.
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS org_mcp_servers (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  command     TEXT NOT NULL,          -- e.g. "node", "python", "npx"
  args        JSONB DEFAULT '[]',     -- command arguments
  secret_name TEXT,                   -- name of secret in secrets table (optional)
  is_active   BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, name)
);

ALTER TABLE org_mcp_servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON org_mcp_servers
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
