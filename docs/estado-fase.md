# 🗺️ ESTADO DE FASE: FASE 4 - CAPA DE INTELIGENCIA VISUAL Y ANALÍTICA 🏗️

## 1. Resumen de Fase
- **Objetivo:** Dotar al sistema de herramientas avanzadas de supervisión, modelado de procesos de negocio y diagnóstico basado en IA, permitiendo entender no solo *qué* está pasando, sino *cómo* se conectan los procesos y qué dicen los datos históricos.
- **Fase Anterior:** Fase 3 - Real-time Run Transcripts [FINALIZADA ✅]
- **Pasos de la Fase 4:**
    1. **4.1 [Framework]:** Metadata de Escalamiento en el `registry.py`. [COMPLETADO ✅]
    2. **4.2 [Frontend]:** Implementar `FlowHierarchyView.tsx`. [COMPLETADO ✅]
    3. **4.3 [Backend]:** Implementar `AnalyticalCrew`. [COMPLETADO ✅]
    4. **4.4 [Frontend]:** Implementar `AnalyticalAssistantChat.tsx`. [PENDIENTE 🏗️]
    5. **4.5 [Validación]:** Test de Precisión Analítica. [PENDIENTE 🏗️]

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **IA Analítica y Consultas Naturales (Step 4.3):** Implementación del `AnalyticalCrew` operativo. Soporta clasificación de intenciones vía LLM con fallback por keywords, ejecución de consultas analíticas pre-validadas y síntesis narrativa de resultados con insights en Markdown.
    - **Herramientas de Análisis:** Disponibilidad de `SQLAnalyticalTool` (para métricas de negocio) y `EventStoreTool` (para trazabilidad de eventos) con aislamiento multi-tenant estricto vía `org_id`.
    - **API de Chat Analítico:** Endpoint `POST /analytical/ask` habilitado con soporte para rate limiting por organización (10 req/min) y trazabilidad de consumo de tokens.
    - **Visualización de Jerarquía (Step 4.2):** Componente `FlowHierarchyView` desplegado. Agrupa flows por categorías, visualiza dependencias y resalta errores de grafo.
    - **Registro Enriquecido (Step 4.1):** Soporte para metadatos de jerarquía y dependencias con validación automática (DFS Cycle Detection) en el arranque del servidor.
    - **Fase 3 Completa:** Streaming de eventos en tiempo real (Transcripts) funcional con latencia < 500ms y visualización animada en el timeline.

- **Parcialmente Implementado:**
    - **Categorización de Flows de Sistema:** Auditoría inicial completada, pero se requiere mantenimiento continuo a medida que se agreguen nuevos procesos dinámicos.

## 3. Contratos Técnicos Vigentes
- **API Analítica (`POST /analytical/ask`):**
    - Request: `{ "question": str, "query_type": Optional[str] }`
    - Response: `{ "question": str, "query_type": str, "data": List, "summary": str, "metadata": { "tokens_used": int, "row_count": int } }`
- **Allowlist Analítico (`analytical_queries.py`):** Plantillas SQL pre-aprobadas para: `agent_success_rate`, `tickets_by_status`, `flow_token_consumption`, `recent_events_summary`, y `tasks_by_flow_type`.
- **Metadata de Registro (`registry.py`):** Campos `category` y `depends_on` para modelado de jerarquía.
- **API Hierarchy (`GET /flows/hierarchy`):** Entrega el mapa de procesos con estatus de validación integrado.

## 4. Decisiones de Arquitectura Tomadas
- **Asincronía en CrewAI (Paso 4.3):** Las llamadas al LLM se ejecutan mediante `run_in_executor` para evitar el bloqueo del event loop de FastAPI durante la inferencia, garantizando la responsividad del resto de la API.
- **Robustez Multi-fallback (Paso 4.3):** Implementación de pipelines de reserva basados en heurísticas locales (keywords) para garantizar una respuesta (aunque sea simplificada) ante fallos de conectividad con el proveedor de LLM.
- **Aislamiento por Herramienta (Paso 4.3):** El `org_id` se inyecta directamente en las instancias de las herramientas analíticas (heredando de `OrgBaseTool`), garantizando que el LLM solo procese datos del tenant solicitante.
- **Code-as-Schema (Paso 4.1):** Definición de dependencias en decoradores para evitar desincronización con la base de datos.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 4.3  | ✅ | `analytical_crew.py`, `analytical.py`, `analytical_chat.py` | Asincronía LLM / Multi-fallback | Backend analítico certificado y libre de crashes térmicos. |
| 4.2  | ✅ | `FlowHierarchyView.tsx`, `page.tsx`, `types.ts` | Error Auto-expand / Framer Motion | Visualización diagnóstica aprobada con 100% de cumplimiento. |
| 4.1  | ✅ | `registry.py`, `main.py`, `flows.py`, `architect_flow.py` | Code-as-Schema / DFS Cycle Detection | Jerarquía de procesos validada. Fix crítico de registro aplicado. |
| 3.5  | ✅ | `test_3_5_latency.py`, `get_server_time.sql` | Certificación de Latencia P95 | Validado tras resolver issues de Cold Start en Supabase. |

## 6. Criterios Generales de Aceptación MVP (Fase 4)
- [✅] El sistema debe ser capaz de representar visualmente las dependencias entre flows.
- [✅] El backend analítico responde preguntas sobre el Event Store y métricas de negocio usando lenguaje natural (Step 4.3).
- [ ] El chat analítico lateral es accesible y funcional desde el dashboard del frontend (Step 4.4).
- [ ] Los errores en el grafo de procesos no deben impedir el funcionamiento del resto del sistema.

---
*Documento actualizado por el protocolo CONTEXTO tras la finalización del Paso 4.3 (Implementación del AnalyticalCrew).*

