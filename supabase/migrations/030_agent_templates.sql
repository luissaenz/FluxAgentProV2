-- =============================================================
-- Migration 030: agent_templates
-- Tabla global de templates de agentes para el builder visual.
-- Paso 03 del Ecosistema FluxAgentPro-v2
-- Correcciones vs plan:
--   - Tabla GLOBAL sin org_id (patron service_catalog mig 024)
--   - RLS: SELECT authenticated, ALL solo service_role
-- =============================================================

CREATE TABLE IF NOT EXISTS agent_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT NOT NULL,
    soul_json       JSONB NOT NULL DEFAULT '{}',
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter        INTEGER DEFAULT 5,
    is_system       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "agent_templates_read" ON agent_templates
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "agent_templates_write" ON agent_templates
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX idx_agent_templates_category ON agent_templates(category);
CREATE UNIQUE INDEX idx_agent_templates_system_name
    ON agent_templates(name) WHERE is_system = TRUE;
