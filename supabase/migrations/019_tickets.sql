-- ============================================================
-- Migration 019: Tickets — solicitudes de trabajo con ciclo de vida
-- Ejecutar DESPUES de 018_flow_metrics_view.sql
-- ============================================================

-- Tabla de tickets (solicitudes de trabajo)
CREATE TABLE IF NOT EXISTS tickets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    title           TEXT NOT NULL,
    description     TEXT,
    flow_type       TEXT,
    priority        TEXT NOT NULL DEFAULT 'medium',
    status          TEXT NOT NULL DEFAULT 'backlog',
    input_data      JSONB,
    task_id         UUID,
    created_by      TEXT,
    assigned_to     TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_tickets_org ON tickets(org_id);
CREATE INDEX IF NOT EXISTS idx_tickets_org_status ON tickets(org_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_task ON tickets(task_id);

-- RLS — MISMO PATRON que tasks (service_role bypass + tenant isolation)
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tickets_org_access ON tickets;
CREATE POLICY tickets_org_access ON tickets
    FOR ALL
    USING (
        auth.role() = 'service_role'
        OR org_id::text = current_org_id()
    );

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_tickets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_tickets_updated_at ON tickets;
CREATE TRIGGER trg_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_tickets_updated_at();
