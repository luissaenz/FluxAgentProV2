-- supabase/migrations/018_flow_metrics_view.sql
-- Indices de soporte + vista de metricas agregadas por flow_type

-- Indices de soporte
CREATE INDEX IF NOT EXISTS idx_tasks_flow_type ON tasks(org_id, flow_type);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(org_id, created_at DESC);

-- Vista: metricas agregadas por flow_type (solo datos del sistema agentino)
CREATE OR REPLACE VIEW v_flow_metrics AS
SELECT
    org_id,
    flow_type,
    COUNT(*)                                               AS total_runs,
    COUNT(*) FILTER (WHERE status = 'completed')           AS completed,
    COUNT(*) FILTER (WHERE status = 'failed')              AS failed,
    COUNT(*) FILTER (WHERE status = 'running')             AS running,
    COUNT(*) FILTER (WHERE status = 'awaiting_approval')   AS awaiting_approval,
    COUNT(*) FILTER (WHERE status = 'pending')             AS pending,
    COALESCE(SUM(tokens_used), 0)                          AS total_tokens,
    COALESCE(AVG(tokens_used) FILTER (WHERE tokens_used > 0), 0)::INTEGER AS avg_tokens,
    MAX(updated_at)                                        AS last_run_at
FROM tasks
GROUP BY org_id, flow_type;

-- La vista hereda RLS de tasks (SECURITY INVOKER por defecto en PostgreSQL)
