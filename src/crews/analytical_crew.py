"""AnalyticalCrew — Agente analitico con CrewAI, herramientas SQL y EventStore.

Phase 4: Crew analitico que procesa consultas en lenguaje natural usando:
1. Intent Classification via LLM para clasificar la pregunta del usuario
2. Herramientas CrewAI (SQLAnalyticalTool, EventStoreTool) para ejecutar consultas
3. Synthesis via LLM para generar respuestas narrativas con insights

Pipeline: Question -> Intent Classifier (LLM) -> Tool Execution -> Synthesizer (LLM) -> Response

Seguridad:
- SQL dinamico prohibido: solo consultas del ALLOWED_ANALYTICAL_QUERIES
- Multi-tenancy: org_id inyectado automaticamente en las herramientas
- Fallback por keywords si el LLM falla
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from crewai import LLM

from .base_crew import BaseCrew
from .analytical_queries import ALLOWED_ANALYTICAL_QUERIES
from ..config import get_settings
from ..tools.analytical import SQLAnalyticalTool, EventStoreTool

logger = logging.getLogger(__name__)

# ── Intentos de clasificacion por keywords (fallback) ─────────────

_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "agent_success_rate": ["agente", "agent", "exito", "success", "mejor", "tasa", "eficiente", "eficiencia"],
    "tickets_by_status": ["ticket", "estado", "status", "distribucion"],
    "flow_token_consumption": ["token", "consumo", "gasto", "costo", "llm"],
    "recent_events_summary": ["evento", "event", "reciente", "recent", "24", "hoy"],
    "tasks_by_flow_type": ["tarea", "task", "flow", "tipo"],
}

_AVAILABLE_INTENTS = ", ".join(ALLOWED_ANALYTICAL_QUERIES.keys())


class AnalyticalCrew(BaseCrew):
    """Crew analitico con CrewAI Agent y herramientas SQL/EventStore.

    Implementa el pipeline: Intent Classifier -> Tool Execution -> Synthesizer
    """

    def __init__(self, org_id: str, user_id: Optional[str] = None) -> None:
        # FIX ID-005: Inicializamos la clase base con un role analitico generico.
        super().__init__(org_id, role="analytical_analyst")
        self.user_id = user_id
        # FIX ID-009: Inicializar _last_tokens_used para evitar AttributeError
        # en el path de fallback cuando _synthesize no llama al LLM.
        self._last_tokens_used = 0

    # ── Helpers LLM no bloqueantes ────────────────────────────────

    def _build_llm(self, temperature: float = 0.2, max_tokens: int = 500) -> LLM:
        """Crear un LLM configurado con los parametros adecuados.

        FIX ID-012: Crear LLM directamente en lugar de clonar via type(llm).
        """
        settings = get_settings()
        return LLM(
            model=settings.groq_model,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            api_key=settings.groq_api_key,
        )

    async def _llm_call_async(self, llm: LLM, messages: list[dict]) -> str:
        """Llamar al LLM de forma no bloqueante.

        FIX ID-010: llm.call() es sincrono y bloquea el event loop.
        Lo ejecutamos en un thread pool para no bloquear FastAPI.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: llm.call(messages=messages),
        )

    # ── Metodos publicos ───────────────────────────────────────────

    async def analyze(
        self,
        query_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ejecutar un analisis pre-definido (metodo legacy compatible)."""
        if query_type not in ALLOWED_ANALYTICAL_QUERIES:
            raise ValueError(
                f"Query type '{query_type}' not allowed. "
                f"Available: {list(ALLOWED_ANALYTICAL_QUERIES.keys())}"
            )

        tool = SQLAnalyticalTool(org_id=self.org_id)
        params_json = json.dumps(params or {})
        raw_result = tool._run(query_type=query_type, params=params_json)
        data = json.loads(raw_result)

        return {
            "query_type": query_type,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "org_id": self.org_id,
            "data": data.get("data", []),
            "metadata": {
                "row_count": data.get("row_count", 0),
                "query_template": ALLOWED_ANALYTICAL_QUERIES[query_type][:100] + "...",
            },
        }

    async def ask(self, question: str, query_type_hint: Optional[str] = None) -> Dict[str, Any]:
        """Procesar pregunta en lenguaje natural con el pipeline completo."""
        # Paso 1: Clasificar intencion (LLM o fallback)
        intent = query_type_hint or await self._classify_intent(question)

        # Validar que el intent es valido
        if intent not in ALLOWED_ANALYTICAL_QUERIES:
            return {
                "question": question,
                "query_type": "unknown",
                "data": [],
                "summary": (
                    f"No tengo acceso a datos para la pregunta: '{question}'.\n\n"
                    f"Puedo ayudarte con: {_AVAILABLE_INTENTS}."
                ),
                "metadata": {"tokens_used": 0, "row_count": 0},
            }

        # Paso 2: Ejecutar herramienta
        tool = SQLAnalyticalTool(org_id=self.org_id)
        raw_result = tool._run(query_type=intent, params="{}")
        query_data = json.loads(raw_result)

        data = query_data.get("data", [])
        row_count = query_data.get("row_count", 0)

        # Si no hay datos, retornar mensaje informativo sin llamar al LLM
        if not data:
            return {
                "question": question,
                "query_type": intent,
                "data": [],
                "summary": query_data.get(
                    "message",
                    f"No hay datos disponibles para {intent}.",
                ),
                "metadata": {"tokens_used": 0, "row_count": 0},
            }

        # Paso 3: Enriquecer con EventStore si es relevante
        event_context = ""
        if intent in ("agent_success_rate", "tasks_by_flow_type"):
            event_tool = EventStoreTool(org_id=self.org_id)
            event_raw = event_tool._run(limit=10)
            event_data = json.loads(event_raw)
            if event_data.get("count", 0) > 0:
                event_context = (
                    f"\nContexto de eventos recientes: "
                    f"{json.dumps(event_data.get('events', [])[:3], ensure_ascii=False)}"
                )

        # Paso 4: Sintetizar respuesta narrativa con LLM
        summary = await self._synthesize(question, intent, data, event_context)

        return {
            "question": question,
            "query_type": intent,
            "data": data,
            "summary": summary,
            "metadata": {
                "tokens_used": self._last_tokens_used,
                "row_count": row_count,
            },
        }

    # ── Intent Classifier ──────────────────────────────────────────

    async def _classify_intent(self, question: str) -> str:
        """Clasificar la intencion de la pregunta usando LLM con fallback por keywords."""
        try:
            return await self._classify_intent_llm(question)
        except Exception as exc:
            logger.warning("LLM intent classification failed, falling back to keywords: %s", exc)
            return self._classify_intent_keywords(question)

    async def _classify_intent_llm(self, question: str) -> str:
        """Usar LLM para clasificar la intencion de la pregunta."""
        llm = self._build_llm(temperature=0.0, max_tokens=30)

        system_prompt = (
            "Eres un clasificador de intenciones para un asistente analitico.\n"
            f"Debes clasificar la pregunta del usuario en UNO de estos intents: {_AVAILABLE_INTENTS}.\n"
            "Responde SOLO con el nombre del intent, sin explicaciones.\n"
            "Si la pregunta no encaja con ninguno, responde 'unknown'."
        )

        # FIX ID-010: Llamada async no bloqueante
        response = await self._llm_call_async(llm, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ])

        intent = response.strip().lower() if isinstance(response, str) else ""

        if intent in ALLOWED_ANALYTICAL_QUERIES:
            return intent

        return "unknown"

    def _classify_intent_keywords(self, question: str) -> str:
        """Fallback: clasificar por keywords simple."""
        q = question.lower()
        for intent, keywords in _INTENT_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                return intent
        return "unknown"

    # ── Synthesizer ────────────────────────────────────────────────

    async def _synthesize(
        self,
        question: str,
        intent: str,
        data: List[Dict[str, Any]],
        event_context: str = "",
    ) -> str:
        """Generar respuesta narrativa con LLM a partir de los datos."""
        llm = self._build_llm(temperature=0.2, max_tokens=500)

        data_json = json.dumps(data, ensure_ascii=False, indent=2)

        system_prompt = (
            "Eres un asistente analitico que responde preguntas con datos concretos.\n"
            "REGLAS ESTRICTAS:\n"
            "1. SOLO usa los datos proporcionados - NUNCA inventes numeros.\n"
            "2. Si los datos estan vacios, informa que no hay informacion disponible.\n"
            "3. Responde en espanol con formato Markdown.\n"
            "4. Destaca los numeros mas importantes en **negrita**.\n"
            "5. Se conciso pero informativo - maximo 3-4 oraciones.\n"
            "6. Menciona el agente/flow/item mas destacado si aplica."
        )

        user_content = (
            f"Pregunta: {question}\n"
            f"Intent: {intent}\n"
            f"Datos:\n```json\n{data_json}\n```"
        )
        if event_context:
            user_content += event_context

        try:
            # FIX ID-010: Llamada async no bloqueante
            response = await self._llm_call_async(llm, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ])
            summary = response.strip() if isinstance(response, str) else ""

            # FIX ID-004: Capturar tokens usados
            if summary:
                self._last_tokens_used = self._estimate_tokens(summary)
                return summary
        except Exception as exc:
            logger.warning("LLM synthesis failed, using fallback template: %s", exc)

        return self._synthesize_fallback(intent, data)

    @staticmethod
    def _estimate_tokens(summary: str) -> int:
        """Estimar tokens usados basado en la longitud del resumen.

        Regla practica: ~4 caracteres por token en promedio.
        """
        return max(1, len(summary) // 4)

    def _synthesize_fallback(
        self,
        intent: str,
        data: List[Dict[str, Any]],
    ) -> str:
        """Fallback narrativo sin LLM - templates hardcoded."""
        row_count = len(data)

        if intent == "agent_success_rate":
            if not data:
                return "No hay datos de agentes en los ultimos 7 dias."
            top = data[0]
            role = top.get("role") or "N/A"
            return (
                f"El agente con mayor tasa de exito es **{role}** "
                f"con **{top.get('success_rate', 0)}%** de exito "
                f"({top.get('completed_tasks', 0)}/{top.get('total_tasks', 0)} tareas)."
            )

        if intent == "tickets_by_status":
            if not data:
                return "No hay tickets registrados."
            total = sum(d.get("count", 0) for d in data)
            done = next((d["count"] for d in data if d.get("status") == "done"), 0)
            return (
                f"Hay **{total} tickets** en total. "
                f"**{done}** completados exitosamente."
            )

        if intent == "flow_token_consumption":
            if not data:
                return "No hay datos de consumo de tokens."
            total_tokens = sum(d.get("total_tokens", 0) for d in data)
            flow_name = data[0].get("flow_type") or "N/A"
            return (
                f"El consumo total de tokens es de **{total_tokens:,}**. "
                f"El flow con mayor consumo es **{flow_name}** "
                f"con {data[0].get('total_tokens', 0):,} tokens."
            )

        if intent == "recent_events_summary":
            if not data:
                return "No hay eventos en las ultimas 24 horas."
            total = sum(d.get("count", 0) for d in data)
            return (
                f"Se registraron **{total} eventos** en las ultimas 24 horas, "
                f"de **{row_count} tipos** diferentes."
            )

        if intent == "tasks_by_flow_type":
            if not data:
                return "No hay tareas registradas."
            total = sum(d.get("count", 0) for d in data)
            return (
                f"Hay **{total} tareas** registradas en "
                f"**{row_count} combinaciones** de flow/estado."
            )

        return f"Consulta ejecutada: {row_count} filas retornadas."
