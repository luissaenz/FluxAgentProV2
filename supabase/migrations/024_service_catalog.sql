-- =============================================================
-- Migration 024: Service Catalog TIPO C
-- 3 tablas: service_catalog, org_service_integrations, service_tools
-- Paso 5.2.5 del Ecosistema Agéntico MCP
-- =============================================================

-- Tabla 1: service_catalog (global, SIN RLS)
CREATE TABLE IF NOT EXISTS service_catalog (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  auth_type TEXT NOT NULL,
  auth_scopes JSONB DEFAULT '[]'::JSONB,
  base_url TEXT NOT NULL,
  api_version TEXT,
  health_check_url TEXT,
  docs_url TEXT,
  logo_url TEXT,
  required_secrets TEXT[] NOT NULL DEFAULT '{}',
  config_schema JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_catalog_category
  ON service_catalog(category);

-- Tabla 2: org_service_integrations (per-org, CON RLS)
CREATE TABLE IF NOT EXISTS org_service_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  service_id TEXT NOT NULL REFERENCES service_catalog(id),
  status TEXT NOT NULL DEFAULT 'pending_setup',
  secret_names JSONB NOT NULL DEFAULT '[]'::JSONB,
  config JSONB DEFAULT '{}'::JSONB,
  last_health_check TIMESTAMPTZ,
  last_health_status TEXT,
  error_message TEXT,
  enabled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, service_id)
);

ALTER TABLE org_service_integrations ENABLE ROW LEVEL SECURITY;

-- CORREGIDO: Patrón de mig. 010 con service_role bypass + current_org_id() text cast
CREATE POLICY org_integration_access ON org_service_integrations
  FOR ALL USING (
    auth.role() = 'service_role'
    OR org_id::text = current_org_id()
  );

CREATE INDEX IF NOT EXISTS idx_org_integrations_org
  ON org_service_integrations(org_id);
CREATE INDEX IF NOT EXISTS idx_org_integrations_status
  ON org_service_integrations(org_id, status);

-- Tabla 3: service_tools (global, SIN RLS)
CREATE TABLE IF NOT EXISTS service_tools (
  id TEXT PRIMARY KEY,
  service_id TEXT NOT NULL REFERENCES service_catalog(id),
  name TEXT NOT NULL,
  version TEXT NOT NULL DEFAULT '1.0.0',
  input_schema JSONB NOT NULL,
  output_schema JSONB NOT NULL,
  execution JSONB NOT NULL,
  tool_profile JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_tools_service
  ON service_tools(service_id);
