-- ============================================================
-- Migration 001: set_config RPC + current_org_id() + RLS
-- Execute this FIRST — all RLS policies depend on it.
-- ============================================================

-- -----------------------------------------------------------
-- 1. RPC to set session-level tenant config
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION set_config(
    p_key   TEXT,
    p_value TEXT,
    p_is_local BOOLEAN DEFAULT TRUE
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Allow only approved keys
    IF p_key NOT IN ('app.org_id', 'app.user_id', 'app.role') THEN
        RAISE EXCEPTION 'Invalid config key: %', p_key;
    END IF;

    -- org_id and user_id must not be NULL
    IF p_key IN ('app.org_id', 'app.user_id') AND p_value IS NULL THEN
        RAISE EXCEPTION 'Value cannot be null for key: %', p_key;
    END IF;

    PERFORM pg_catalog.set_config(p_key, p_value, p_is_local);
END;
$$;


-- -----------------------------------------------------------
-- 2. Helper to read the current org from session
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION current_org_id()
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN current_setting('app.org_id', TRUE);
END;
$$;


-- -----------------------------------------------------------
-- 3. Core tables
-- -----------------------------------------------------------

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    flow_type       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    payload         JSONB DEFAULT '{}',
    result          JSONB,
    error           TEXT,
    correlation_id  TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Snapshots (state persistence)
CREATE TABLE IF NOT EXISTS snapshots (
    task_id     UUID PRIMARY KEY REFERENCES tasks(id),
    org_id      UUID NOT NULL REFERENCES organizations(id),
    flow_type   TEXT NOT NULL,
    status      TEXT NOT NULL,
    state_json  JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Domain events (event sourcing)
CREATE TABLE IF NOT EXISTS domain_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    aggregate_type  TEXT NOT NULL,
    aggregate_id    TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    payload         JSONB DEFAULT '{}',
    actor           TEXT,
    sequence        INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);


-- -----------------------------------------------------------
-- 4. Row Level Security
-- -----------------------------------------------------------

-- tasks
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY tasks_org_access ON tasks
    FOR ALL
    USING (org_id::text = current_org_id());

-- snapshots
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY snapshots_org_access ON snapshots
    FOR ALL
    USING (org_id::text = current_org_id());

-- domain_events
ALTER TABLE domain_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY domain_events_org_access ON domain_events
    FOR ALL
    USING (org_id::text = current_org_id());

-- organizations (org members can see their own org)
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
CREATE POLICY organizations_self_access ON organizations
    FOR ALL
    USING (id::text = current_org_id());


-- -----------------------------------------------------------
-- 5. Indexes
-- -----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_tasks_org_id ON tasks(org_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_correlation ON tasks(correlation_id);
CREATE INDEX IF NOT EXISTS idx_domain_events_aggregate ON domain_events(aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_domain_events_org ON domain_events(org_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_org ON snapshots(org_id);
