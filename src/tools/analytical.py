"""Herramientas analiticas para el AnalyticalCrew.

SQLAnalyticalTool: Ejecuta consultas pre-validadas del ALLOWED_ANALYTICAL_QUERIES
inyectando org_id para aislamiento multi-tenant.

Las consultas se ejecutan via Supabase Python client (filtrado por tabla)
ya que el SDK no soporta SQL raw sin RPC functions. Los resultados son
estructuralmente identicos a las plantillas SQL del allowlist.

EventStoreTool: Consulta el EventStore para analisis de eventos de dominio.
"""

from __future__ import annotations

import json
import logging
from typing import Type, Optional

from pydantic import BaseModel, Field

from .base_tool import OrgBaseTool
from .registry import register_tool
from ..crews.analytical_queries import ALLOWED_ANALYTICAL_QUERIES
from ..db.session import get_tenant_client

logger = logging.getLogger(__name__)


# ── Input Schemas ──────────────────────────────────────────────────

class SQLAnalyticalInput(BaseModel):
    """Schema de input para SQLAnalyticalTool."""
    query_type: str = Field(
        ...,
        description=(
            "Tipo de consulta a ejecutar. Opciones validas: "
            "agent_success_rate, tickets_by_status, flow_token_consumption, "
            "recent_events_summary, tasks_by_flow_type"
        ),
    )
    params: Optional[str] = Field(
        default="{}",
        description="Parametros adicionales en formato JSON",
    )


class EventStoreInput(BaseModel):
    """Schema de input para EventStoreTool."""
    event_type: Optional[str] = Field(
        default=None,
        description="Filtrar por tipo de evento especifico",
    )
    aggregate_type: Optional[str] = Field(
        default=None,
        description="Filtrar por tipo de agregado",
    )
    limit: int = Field(
        default=50,
        description="Maximo de eventos a retornar (default: 50, max: 200)",
    )


# ── SQLAnalyticalTool ──────────────────────────────────────────────

@register_tool(
    name="sql_analytical",
    description=(
        "Ejecuta consultas analiticas pre-validadas sobre datos historicos. "
        "Solo acepta query_types del allowlist. "
        "NUNCA genera SQL dinamico."
    ),
    tags=["analytical", "sql", "read-only"],
    timeout_seconds=30,
    retry_count=2,
)
class SQLAnalyticalTool(OrgBaseTool):
    """Ejecutor de consultas analiticas pre-validadas con aislamiento multi-tenant.

    Ejecuta consultas del ALLOWED_ANALYTICAL_QUERIES inyectando org_id.
    Las consultas se realizan via Supabase Python client con filtrado
    y agregacion en Python (equivalente a las templates SQL del allowlist).
    """

    name: str = "sql_analytical"
    description: str = (
        "Ejecuta consultas analiticas pre-validadas sobre datos historicos."
    )
    args_schema: Type[BaseModel] = SQLAnalyticalInput

    def _run(self, query_type: str, params: str = "{}") -> str:
        """Ejecutar consulta analitica y retornar resultados como JSON string."""
        if query_type not in ALLOWED_ANALYTICAL_QUERIES:
            return json.dumps({
                "error": f"Query type '{query_type}' no permitido.",
                "allowed": list(ALLOWED_ANALYTICAL_QUERIES.keys()),
            })

        try:
            parsed_params = json.loads(params) if params else {}
        except json.JSONDecodeError:
            parsed_params = {}

        try:
            with get_tenant_client(self.org_id, user_id=None) as db:
                results = self._execute_query(db, query_type, parsed_params)

            if not results:
                return json.dumps({
                    "query_type": query_type,
                    "data": [],
                    "message": "No hay datos disponibles para esta consulta.",
                    "row_count": 0,
                })

            return json.dumps({
                "query_type": query_type,
                "data": results,
                "row_count": len(results),
            })

        except Exception as exc:
            logger.error("Error ejecutando consulta analitica %s: %s", query_type, exc)
            return json.dumps({
                "error": "Fallo temporal en la recuperacion de metricas.",
                "query_type": query_type,
                "detail": str(exc),
            })

    def _execute_query(self, db, query_type: str, params: dict) -> list:
        """Ejecutar la consulta especifica contra Supabase."""
        dispatcher = {
            "agent_success_rate": self._query_agent_success_rate,
            "tickets_by_status": self._query_tickets_by_status,
            "flow_token_consumption": self._query_flow_tokens,
            "recent_events_summary": self._query_recent_events,
            "tasks_by_flow_type": self._query_tasks_by_flow,
        }
        handler = dispatcher.get(query_type)
        return handler(db, params) if handler else []

    def _query_agent_success_rate(self, db, params: dict = None) -> list:
        """Equivalente a la template SQL 'agent_success_rate' del allowlist.

        SELECT ac.role, COUNT(*) as total_tasks,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed_tasks,
               ROUND(100.0 * completed / NULLIF(total, 0), 2) as success_rate
        FROM tasks JOIN agent_catalog ...
        WHERE org_id = X AND created_at >= NOW() - 7 days
        GROUP BY ac.role ORDER BY success_rate DESC LIMIT 10
        """
        from datetime import timedelta, datetime, timezone

        params = params or {}
        days = int(params.get("days", 7))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        result = (
            db.table("tasks")
            .select("id, status, assigned_agent_role")
            .gte("created_at", cutoff)
            .execute()
        )

        tasks = result.data or []
        stats: dict[str, dict[str, int]] = {}

        for task in tasks:
            # FIX ID-003: .get() con default "unknown" no funciona si el valor es null explicito
            role = task.get("assigned_agent_role") or "unknown"
            if role not in stats:
                stats[role] = {"total": 0, "completed": 0}
            stats[role]["total"] += 1
            if task.get("status") == "completed":
                stats[role]["completed"] += 1

        result_list = []
        for role, data in stats.items():
            rate = round(100.0 * data["completed"] / data["total"], 2) if data["total"] > 0 else 0
            result_list.append({
                "role": role,
                "total_tasks": data["total"],
                "completed_tasks": data["completed"],
                "success_rate": rate,
            })

        result_list.sort(key=lambda x: x["success_rate"], reverse=True)
        return result_list[:10]

    def _query_tickets_by_status(self, db, params: dict = None) -> list:
        """Equivalente a la template SQL 'tickets_by_status' del allowlist.

        SELECT status, COUNT(*) as count FROM tickets WHERE org_id = X GROUP BY status ORDER BY count DESC
        """
        params = params  # reserved for future filters (e.g., status filter)
        result = (
            db.table("tickets")
            .select("id, status")
            .execute()
        )

        tickets = result.data or []
        stats: dict[str, int] = {}

        for ticket in tickets:
            status = ticket.get("status") or "unknown"
            stats[status] = stats.get(status, 0) + 1

        return [
            {"status": status, "count": count}
            for status, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)
        ]

    def _query_flow_tokens(self, db, params: dict = None) -> list:
        """Equivalente a la template SQL 'flow_token_consumption' del allowlist.

        SELECT flow_type, COUNT(*) as total_runs, SUM(tokens_used) as total_tokens,
               ROUND(AVG(tokens_used), 2) as avg_tokens
        FROM tasks WHERE org_id = X AND tokens_used > 0 GROUP BY flow_type ORDER BY total_tokens DESC
        """
        params = params  # reserved for future filters
        result = (
            db.table("tasks")
            .select("id, flow_type, tokens_used")
            .execute()
        )

        tasks = result.data or []
        stats: dict[str, dict[str, int]] = {}

        for task in tasks:
            tokens = task.get("tokens_used") or 0
            if tokens == 0:
                continue
            flow = task.get("flow_type") or "unknown"
            if flow not in stats:
                stats[flow] = {"total_tokens": 0, "runs": 0}
            stats[flow]["total_tokens"] += tokens
            stats[flow]["runs"] += 1

        result_list = []
        for flow, data in stats.items():
            result_list.append({
                "flow_type": flow,
                "total_runs": data["runs"],
                "total_tokens": data["total_tokens"],
                "avg_tokens": round(data["total_tokens"] / data["runs"], 2) if data["runs"] > 0 else 0,
            })

        result_list.sort(key=lambda x: x["total_tokens"], reverse=True)
        return result_list[:10]

    def _query_recent_events(self, db, params: dict = None) -> list:
        """Equivalente a la template SQL 'recent_events_summary' del allowlist.

        SELECT event_type, COUNT(*) as count FROM domain_events
        WHERE org_id = X AND created_at >= NOW() - 24h GROUP BY event_type ORDER BY count DESC
        """
        from datetime import timedelta, datetime, timezone

        params = params or {}
        hours = int(params.get("hours", 24))
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        result = (
            db.table("domain_events")
            .select("id, event_type, created_at")
            .gte("created_at", cutoff)
            .execute()
        )

        events = result.data or []
        stats: dict[str, int] = {}

        for event in events:
            event_type = event.get("event_type") or "unknown"
            stats[event_type] = stats.get(event_type, 0) + 1

        return [
            {"event_type": event_type, "count": count}
            for event_type, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)
        ][:20]

    def _query_tasks_by_flow(self, db, params: dict = None) -> list:
        """Equivalente a la template SQL 'tasks_by_flow_type' del allowlist.

        SELECT flow_type, status, COUNT(*) as count FROM tasks
        WHERE org_id = X GROUP BY flow_type, status ORDER BY flow_type, count DESC
        """
        params = params  # reserved for future filters
        result = (
            db.table("tasks")
            .select("id, flow_type, status")
            .execute()
        )

        tasks = result.data or []
        stats: dict[str, dict[str, int]] = {}

        for task in tasks:
            flow = task.get("flow_type") or "unknown"
            status = task.get("status") or "unknown"
            if flow not in stats:
                stats[flow] = {}
            if status not in stats[flow]:
                stats[flow][status] = 0
            stats[flow][status] += 1

        result_list = []
        for flow, status_counts in stats.items():
            for status, count in status_counts.items():
                result_list.append({
                    "flow_type": flow,
                    "status": status,
                    "count": count,
                })

        result_list.sort(key=lambda x: (x["flow_type"], -x["count"]))
        return result_list


# ── EventStoreTool ─────────────────────────────────────────────────

@register_tool(
    name="event_store",
    description=(
        "Consulta el EventStore para analisis de eventos de dominio historicos. "
        "Permite filtrar por event_type y aggregate_type."
    ),
    tags=["analytical", "events", "read-only"],
    timeout_seconds=30,
    retry_count=2,
)
class EventStoreTool(OrgBaseTool):
    """Consultor del EventStore para analisis de eventos de dominio."""

    name: str = "event_store"
    description: str = "Consulta eventos de dominio historicos."
    args_schema: Type[BaseModel] = EventStoreInput

    def _run(self, event_type: Optional[str] = None, aggregate_type: Optional[str] = None, limit: int = 50) -> str:
        """Consultar eventos del EventStore."""
        limit = min(limit, 200)

        try:
            events = self._query_events(event_type, aggregate_type, limit)

            if not events:
                return json.dumps({
                    "event_type": event_type,
                    "aggregate_type": aggregate_type,
                    "events": [],
                    "message": "No se encontraron eventos con los filtros solicitados.",
                    "count": 0,
                })

            simplified = []
            for evt in events:
                simplified.append({
                    "event_type": evt.get("event_type"),
                    "aggregate_type": evt.get("aggregate_type"),
                    "aggregate_id": evt.get("aggregate_id"),
                    "sequence": evt.get("sequence"),
                    "created_at": evt.get("created_at"),
                })

            return json.dumps({
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "events": simplified,
                "count": len(simplified),
            })

        except Exception as exc:
            logger.error("Error consultando EventStore: %s", exc)
            return json.dumps({
                "error": "Fallo temporal en la recuperacion de eventos.",
                "detail": str(exc),
            })

    def _query_events(self, event_type: Optional[str], aggregate_type: Optional[str], limit: int) -> list:
        """Consultar eventos desde Supabase."""
        with get_tenant_client(self.org_id, user_id=None) as db:
            query = db.table("domain_events").select(
                "id, event_type, aggregate_type, aggregate_id, payload, sequence, created_at"
            )

            if event_type:
                query = query.eq("event_type", event_type)
            if aggregate_type:
                query = query.eq("aggregate_type", aggregate_type)

            result = (
                query.order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return result.data or []
