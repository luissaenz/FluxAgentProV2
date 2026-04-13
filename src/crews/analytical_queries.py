"""Consultas analiticas pre-validadas (allowlist de seguridad).

Este modulo existe separadamente para evitar imports circulares entre
analytical_crew.py y tools/analytical.py.
"""

from __future__ import annotations

from typing import Dict

ALLOWED_ANALYTICAL_QUERIES: Dict[str, str] = {
    "agent_success_rate": """
        SELECT
            ac.role,
            COUNT(t.id) as total_tasks,
            SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
            ROUND(
                100.0 * SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(t.id), 0),
                2
            ) as success_rate
        FROM tasks t
        JOIN agent_catalog ac ON t.assigned_agent_role = ac.role AND t.org_id = ac.org_id
        WHERE t.org_id = '{org_id}'
          AND t.created_at >= NOW() - INTERVAL '7 days'
        GROUP BY ac.role
        ORDER BY success_rate DESC
        LIMIT 10
    """,
    "tickets_by_status": """
        SELECT
            status,
            COUNT(*) as count
        FROM tickets
        WHERE org_id = '{org_id}'
        GROUP BY status
        ORDER BY count DESC
    """,
    "flow_token_consumption": """
        SELECT
            flow_type,
            COUNT(*) as total_runs,
            SUM(tokens_used) as total_tokens,
            ROUND(AVG(tokens_used), 2) as avg_tokens
        FROM tasks
        WHERE org_id = '{org_id}'
          AND tokens_used > 0
        GROUP BY flow_type
        ORDER BY total_tokens DESC
        LIMIT 10
    """,
    "recent_events_summary": """
        SELECT
            event_type,
            COUNT(*) as count
        FROM domain_events
        WHERE org_id = '{org_id}'
          AND created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY event_type
        ORDER BY count DESC
        LIMIT 20
    """,
    "tasks_by_flow_type": """
        SELECT
            flow_type,
            status,
            COUNT(*) as count
        FROM tasks
        WHERE org_id = '{org_id}'
        GROUP BY flow_type, status
        ORDER BY flow_type, count DESC
    """,
}
