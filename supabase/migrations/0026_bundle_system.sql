-- ============================================================
-- Migration 026: Bundle System (Standard v2)
-- ============================================================

-- 1. Modificar workflow_templates: de Unique Global a Unique per Org
-- Esto permite que diferentes organizaciones tengan flujos con el mismo nombre.
DROP INDEX IF EXISTS idx_workflow_templates_flow_type;
CREATE UNIQUE INDEX idx_workflow_templates_org_flow_type 
    ON workflow_templates(org_id, flow_type);


-- 2. Tabla: bundle_imports (Auditoría de importaciones)
CREATE TABLE IF NOT EXISTS bundle_imports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    bundle_name TEXT NOT NULL,
    bundle_hash TEXT NOT NULL,
    status      TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'validating', 'importing', 'committed', 'failed')),
    error_detail TEXT,
    imported_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_bundle_imports_org ON bundle_imports(org_id);


-- 3. Tabla: skill_catalog (Catálogo dinámico de habilidades)
CREATE TABLE IF NOT EXISTS skill_catalog (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    bundle_id   UUID REFERENCES bundle_imports(id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    code_source TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, name)
);

CREATE INDEX idx_skill_catalog_org ON skill_catalog(org_id);


-- 4. Extender agent_catalog con referencia a bundle
ALTER TABLE agent_catalog ADD COLUMN IF NOT EXISTS bundle_id UUID REFERENCES bundle_imports(id) ON DELETE SET NULL;


-- 5. RLS: Tenant isolation para nuevas tablas
ALTER TABLE bundle_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_catalog ENABLE ROW LEVEL SECURITY;

CREATE POLICY "bundle_imports_tenant_isolation" ON bundle_imports
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

CREATE POLICY "skill_catalog_tenant_isolation" ON skill_catalog
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
