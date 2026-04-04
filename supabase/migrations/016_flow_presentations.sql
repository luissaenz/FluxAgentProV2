-- ============================================================
-- Migration 016: flow_presentations table
-- Declarative presentation config per flow_type per org
-- ============================================================

CREATE TABLE IF NOT EXISTS flow_presentations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    flow_type           TEXT NOT NULL,
    presentation_config JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, flow_type)
);

ALTER TABLE flow_presentations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "flow_presentations_access" ON flow_presentations
    FOR ALL USING (
        auth.role() = 'service_role'
        OR org_id::text = current_setting('app.org_id', TRUE)
    );

CREATE INDEX idx_flow_presentations_org_flow
    ON flow_presentations(org_id, flow_type);
