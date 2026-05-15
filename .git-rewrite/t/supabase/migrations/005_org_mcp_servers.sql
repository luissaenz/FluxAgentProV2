-- ============================================================
-- Migration 005: MCP Servers per Organization
-- Required for Phase 3 Multi-Agent orchestration with MCP.
-- ============================================================

-- Configuración de servidores MCP por organización.
-- Un MCP server puede ser compartido por múltiples agentes de una org.

CREATE TABLE IF NOT EXISTS org_mcp_servers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    command     TEXT NOT NULL,          -- ej: "node", "python", "npx"
    args        JSONB DEFAULT '[]',     -- argumentos del comando
    secret_name TEXT,                   -- nombre del secreto en tabla secrets (opcional)
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, name)
);

-- Habilitar RLS
ALTER TABLE org_mcp_servers ENABLE ROW LEVEL SECURITY;

-- Política de aislamiento de tenant usando el helper current_org_id()
CREATE POLICY "tenant_isolation_org_mcp_servers" ON org_mcp_servers
    FOR ALL USING (org_id::text = current_org_id());

-- Índice para búsquedas por org
CREATE INDEX IF NOT EXISTS idx_mcp_servers_org ON org_mcp_servers(org_id);
