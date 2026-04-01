-- ============================================================
-- Migration 002: Gobernanza — HITL, Vault, columnas adicionales
-- Ejecutar DESPUÉS de 001_set_config_rpc.sql
-- ============================================================

-- -----------------------------------------------------------
-- 1. Extender organizations con columnas de Fase 2
-- -----------------------------------------------------------
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS config       JSONB DEFAULT '{"limits":{}}',
    ADD COLUMN IF NOT EXISTS billing_plan TEXT DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS quota        JSONB DEFAULT '{"max_tasks_per_month":500,"max_tokens_per_month":5000000}',
    ADD COLUMN IF NOT EXISTS is_active    BOOLEAN DEFAULT TRUE;


-- -----------------------------------------------------------
-- 2. Extender tasks con columnas de Fase 2
-- -----------------------------------------------------------
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS flow_id              TEXT,
    ADD COLUMN IF NOT EXISTS assigned_agent_role   TEXT,
    ADD COLUMN IF NOT EXISTS approval_required     BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS approval_status       TEXT DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS approval_payload     JSONB,
    ADD COLUMN IF NOT EXISTS idempotency_key      TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS retries              INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_retries          INTEGER DEFAULT 3,
    ADD COLUMN IF NOT EXISTS tokens_used          INTEGER DEFAULT 0;

-- Backfill flow_id desde id para datos existentes
UPDATE tasks SET flow_id = id::text WHERE flow_id IS NULL;
ALTER TABLE tasks ALTER COLUMN flow_id SET NOT NULL;


-- -----------------------------------------------------------
-- 3. Extender snapshots con columnas de Fase 2 (aggregate)
-- -----------------------------------------------------------
ALTER TABLE snapshots
    ADD COLUMN IF NOT EXISTS aggregate_type TEXT DEFAULT 'flow',
    ADD COLUMN IF NOT EXISTS aggregate_id   TEXT,
    ADD COLUMN IF NOT EXISTS version        BIGINT DEFAULT 0;

-- Backfill aggregate_id desde task_id para datos existentes
UPDATE snapshots SET aggregate_id = task_id::text WHERE aggregate_id IS NULL;


-- -----------------------------------------------------------
-- 4. Tabla: pending_approvals (aprobaciones HITL)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pending_approvals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id),
    task_id     UUID NOT NULL REFERENCES tasks(id),
    flow_type   TEXT NOT NULL,
    description TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}',
    status      TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    decided_by  TEXT,
    decided_at  TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_approvals_org_pending
    ON pending_approvals(org_id, status);
CREATE INDEX IF NOT EXISTS idx_approvals_task
    ON pending_approvals(task_id);

ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;

-- RLS: tenant isolation
CREATE POLICY "tenant_isolation_pending_approvals" ON pending_approvals
    FOR ALL USING (org_id::text = current_org_id());


-- -----------------------------------------------------------
-- 5. Tabla: secrets (credenciales cifradas)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS secrets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id),
    name         TEXT NOT NULL,
    secret_value TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, name)
);

ALTER TABLE secrets ENABLE ROW LEVEL SECURITY;

-- Solo service_role puede SELECT. Agents nunca acceden directamente.
CREATE POLICY "service_role_only_secrets" ON secrets
    FOR SELECT USING (auth.role() = 'service_role');


-- -----------------------------------------------------------
-- 6. Corrección: RLS en domain_events para evitar cross-tenant INSERT
-- -----------------------------------------------------------
DROP POLICY IF EXISTS "append_only_insert" ON domain_events;
DROP POLICY IF EXISTS "domain_events_org_access" ON domain_events;

ALTER TABLE domain_events ENABLE ROW LEVEL SECURITY;

-- INSERT: debe usar el org_id del setting, no permitir任意
CREATE POLICY "tenant_insert_domain_events" ON domain_events
    FOR INSERT WITH CHECK (org_id::text = current_org_id());

-- SELECT: tenant isolation
CREATE POLICY "tenant_select_domain_events" ON domain_events
    FOR SELECT USING (org_id::text = current_org_id());


-- -----------------------------------------------------------
-- 7. Corrección: next_event_sequence con bloqueo de fila
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION next_event_sequence(
    p_aggregate_type TEXT,
    p_aggregate_id   TEXT
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    next_seq BIGINT;
BEGIN
    SELECT COALESCE(MAX(sequence), 0) + 1 INTO next_seq
      FROM domain_events
     WHERE aggregate_type = p_aggregate_type
       AND aggregate_id   = p_aggregate_id
    FOR UPDATE;  -- Bloquea la fila para evitar race condition
    RETURN next_seq;
END;
$$;
