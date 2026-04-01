-- Migration 006: Workflow Templates (Phase 4)
--   Almacena workflows generados por el Architect.
--   Un workflow_template puede ser instanciado múltiples veces.
-- ============================================================

CREATE TABLE workflow_templates (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                    UUID NOT NULL REFERENCES organizations(id)
                                                       ON DELETE CASCADE,

  -- Identificación
  name                      TEXT NOT NULL,
  description               TEXT,
  flow_type                 TEXT NOT NULL,  -- identificador único GLOBAL

  -- Definición estructurada (Schema en workflow_definition.py)
  definition                JSONB NOT NULL DEFAULT '{}',
  -- Estructura:
  -- {
  --   "name": str,
  --   "description": str,
  --   "steps": [ { "id", "name", "agent_role", "description", "depends_on", "requires_approval", "approval_threshold" } ],
  --   "agents": [ { "role", "goal", "backstory", "allowed_tools", "model", "max_iter" } ],
  --   "approval_rules": [ { "condition", "description" } ]
  -- }

  -- Versionado
  version                   INT DEFAULT 1,

  -- Auditoría
  created_by                TEXT,      -- "architect_flow", "user:uuid"
  conversation_id           UUID,      -- referencia a conversations
  is_validated              BOOLEAN DEFAULT FALSE,
  status                    TEXT DEFAULT 'draft'
                                              CHECK (status IN ('draft','active','archived')),

  -- Métricas
  execution_count           INT DEFAULT 0,
  last_executed            TIMESTAMPTZ,

  is_active                BOOLEAN DEFAULT TRUE,
  created_at              TIMESTAMPTZ DEFAULT now(),
  updated_at              TIMESTAMPTZ DEFAULT now()
);

-- flow_type es único GLOBAL (webhooks lo usan como path: /webhooks/{org_id}/{flow_type})
CREATE UNIQUE INDEX idx_workflow_templates_flow_type
  ON workflow_templates(flow_type);

CREATE INDEX idx_workflow_templates_org_active
  ON workflow_templates(org_id)
  WHERE is_active = TRUE;

ALTER TABLE workflow_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON workflow_templates
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
