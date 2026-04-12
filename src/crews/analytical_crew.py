"""AnalyticalCrew — Agente especializado con acceso a herramientas SQL y EventStore.

Phase 4: Crew analítico que procesa consultas complejas sobre datos históricos
de la organización. Permite responder preguntas como:
- "¿Cuál es el agente con mayor tasa de éxito en la última semana?"
- "¿Cuántos tickets se completaron exitosamente este mes?"
- "¿Qué flow tiene el mayor consumo de tokens?"

El agente tiene acceso a:
1. Consultas SQL seguras (pre-validadas contra un allowlist)
2. EventStore para análisis de eventos de dominio
3. LLM para interpretar preguntas en lenguaje natural y generar respuestas
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .base_crew import BaseCrew
from ..db.session import get_tenant_client
from ..events.store import EventStore

logger = logging.getLogger(__name__)

# ── Consultas SQL pre-validadas (allowlist de seguridad) ─────────

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


class AnalyticalCrew(BaseCrew):
    """Crew analítico especializado con acceso a SQL y EventStore.

    Este crew no sigue el patrón estándar de BaseCrew porque:
    1. No ejecuta tareas genéricas de CrewAI
    2. Tiene acceso directo a consultas SQL pre-validadas
    3. Puede consultar el EventStore para análisis temporal

    Uso::

        crew = AnalyticalCrew(org_id="org-uuid")
        result = await crew.analyze(
            query_type="agent_success_rate",
            params={"timeframe": "7d"}
        )
    """

    def __init__(self, org_id: str, user_id: Optional[str] = None) -> None:
        self.org_id = org_id
        self.user_id = user_id
        self._event_store: Optional[EventStore] = None

    @property
    def event_store(self) -> EventStore:
        """Lazy-init del EventStore."""
        if self._event_store is None:
            self._event_store = EventStore(self.org_id, self.user_id)
        return self._event_store

    async def analyze(
        self,
        query_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ejecutar un análisis pre-definido.

        Args:
            query_type: Nombre de la consulta allowlisted
            params: Parámetros adicionales (timeframe, filters, etc.)

        Returns:
            Dict con resultados del análisis y metadata

        Raises:
            ValueError: Si query_type no está en el allowlist
        """
        if query_type not in ALLOWED_ANALYTICAL_QUERIES:
            raise ValueError(
                f"Query type '{query_type}' not allowed. "
                f"Available: {list(ALLOWED_ANALYTICAL_QUERIES.keys())}"
            )

        # Ejecutar consulta SQL segura
        sql_result = await self._execute_safe_query(query_type, params or {})

        # Enriquecer con metadata
        return {
            "query_type": query_type,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "org_id": self.org_id,
            "data": sql_result,
            "metadata": {
                "row_count": len(sql_result) if isinstance(sql_result, list) else 0,
                "query_template": ALLOWED_ANALYTICAL_QUERIES[query_type][:100] + "...",
            },
        }

    async def _execute_safe_query(
        self,
        query_type: str,
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Ejecutar una consulta SQL pre-validada de forma segura.

        SUPUESTO: Supabase client no soporta ejecución de SQL raw directamente.
        Se usa un enfoque de consultas parametrizadas con el tenant client.
        Para queries complejas, se usa RPC o vistas materializadas.

        En MVP, simulamos la ejecución con consultas seguras via tenant client.
        """
        # SUPUESTO: Para MVP, usamos el tenant client con consultas directas
        # a las tablas, ya que Supabase no permite SQL raw sin RPC.
        # En producción real, se crearían RPC functions para cada query.

        with get_tenant_client(self.org_id, self.user_id) as db:
            if query_type == "agent_success_rate":
                return await self._query_agent_success_rate(db)
            elif query_type == "tickets_by_status":
                return await self._query_tickets_by_status(db)
            elif query_type == "flow_token_consumption":
                return await self._query_flow_tokens(db)
            elif query_type == "recent_events_summary":
                return await self._query_recent_events(db)
            elif query_type == "tasks_by_flow_type":
                return await self._query_tasks_by_flow(db)
            else:
                return []

    async def _query_agent_success_rate(self, db) -> List[Dict[str, Any]]:
        """Agente con mayor tasa de éxito."""
        # SUPUESTO: Como Supabase no permite SQL raw, usamos consultas
        # directas a las tablas y hacemos el agregado en Python.
        # Esto es aceptable para MVP con volúmenes bajos.
        from datetime import timedelta

        seven_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=7)
        ).isoformat()

        result = (
            db.table("tasks")
            .select("id, flow_type, status, assigned_agent_role, tokens_used")
            .gte("created_at", seven_days_ago)
            .execute()
        )

        tasks = result.data or []
        stats: Dict[str, Dict[str, int]] = {}

        for task in tasks:
            role = task.get("assigned_agent_role", "unknown")
            if role not in stats:
                stats[role] = {"total": 0, "completed": 0}
            stats[role]["total"] += 1
            if task.get("status") == "completed":
                stats[role]["completed"] += 1

        # Calcular tasas y ordenar
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

    async def _query_tickets_by_status(self, db) -> List[Dict[str, Any]]:
        """Tickets agrupados por estado."""
        result = (
            db.table("tickets")
            .select("id, status")
            .execute()
        )

        tickets = result.data or []
        stats: Dict[str, int] = {}

        for ticket in tickets:
            status = ticket.get("status", "unknown")
            stats[status] = stats.get(status, 0) + 1

        return [
            {"status": status, "count": count}
            for status, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)
        ]

    async def _query_flow_tokens(self, db) -> List[Dict[str, Any]]:
        """Consumo de tokens por flow type."""
        result = (
            db.table("tasks")
            .select("id, flow_type, tokens_used")
            .not_.is_("tokens_used", "null")
            .execute()
        )

        tasks = result.data or []
        stats: Dict[str, Dict[str, Any]] = {}

        for task in tasks:
            flow = task.get("flow_type", "unknown")
            tokens = task.get("tokens_used") or 0
            if tokens == 0:
                continue

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

    async def _query_recent_events(self, db) -> List[Dict[str, Any]]:
        """Resumen de eventos recientes (últimas 24h)."""
        from datetime import timedelta

        twenty_four_hours_ago = (
            datetime.now(timezone.utc) - timedelta(hours=24)
        ).isoformat()

        result = (
            db.table("domain_events")
            .select("id, event_type, created_at")
            .gte("created_at", twenty_four_hours_ago)
            .execute()
        )

        events = result.data or []
        stats: Dict[str, int] = {}

        for event in events:
            event_type = event.get("event_type", "unknown")
            stats[event_type] = stats.get(event_type, 0) + 1

        return [
            {"event_type": event_type, "count": count}
            for event_type, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)
        ][:20]

    async def _query_tasks_by_flow(self, db) -> List[Dict[str, Any]]:
        """Tareas agrupadas por flow type y estado."""
        result = (
            db.table("tasks")
            .select("id, flow_type, status")
            .execute()
        )

        tasks = result.data or []
        stats: Dict[str, Dict[str, int]] = {}

        for task in tasks:
            flow = task.get("flow_type", "unknown")
            status = task.get("status", "unknown")

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

    async def query_events(
        self,
        event_type: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Consulta directa al EventStore para análisis ad-hoc.

        Args:
            event_type: Filtrar por tipo de evento
            aggregate_type: Filtrar por tipo de agregado
            limit: Máximo de eventos a retornar

        Returns:
            Lista de eventos con metadata
        """
        events = []
        try:
            # Intentar obtener eventos del store en memoria primero
            if self._event_store and hasattr(self._event_store, '_pending'):
                events = list(getattr(self._event_store, '_pending', []))
        except Exception:
            pass

        # Complementar con eventos de la base de datos
        with get_tenant_client(self.org_id, self.user_id) as db:
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

            events.extend(result.data or [])

        return events[:limit]
