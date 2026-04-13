# 🗺️ ESTADO DE FASE: FASE 4 - CAPA DE INTELIGENCIA VISUAL Y ANALÍTICA 🏗️

## 1. Resumen de Fase
- **Objetivo:** Dotar al sistema de herramientas avanzadas de supervisión, modelado de procesos de negocio y diagnóstico basado en IA, permitiendo entender no solo *qué* está pasando, sino *cómo* se conectan los procesos y qué dicen los datos históricos.
- **Fase Anterior:** Fase 3 - Real-time Run Transcripts [FINALIZADA ✅]
- **Pasos de la Fase 4:**
    1. **4.1 [Framework]:** Metadata de Escalamiento en el `registry.py`. [COMPLETADO ✅]
    2. **4.2 [Frontend]:** Implementar `FlowHierarchyView.tsx`. [COMPLETADO ✅]
    3. **4.3 [Backend]:** Implementar `AnalyticalCrew`. [COMPLETADO ✅]
    4. **4.4 [Frontend]:** Implementar `AnalyticalAssistantChat.tsx`. [COMPLETADO ✅]
    5. **4.5 [Validación]:** Test de Precisión Analítica. [COMPLETADO ✅]
    6. **FASE FINALIZADA ✅** Podrás encontrar la documentación de la Fase 5 en el plan general.

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **Asistente Analítico Integral (Step 4.4):** Componente `AnalyticalAssistantChat` desplegado globalmente como un FAB (Floating Action Button) en el dashboard. Permite interacción fluida con el `AnalyticalCrew` mediante lenguaje natural y consultas rápidas (Quick Queries).
    - **IA Analítica y Consultas Naturales (Step 4.3):** Implementación del `AnalyticalCrew` operativo. Soporta clasificación de intenciones vía LLM con fallback por keywords, ejecución de consultas analíticas pre-validadas y síntesis narrativa de resultados con insights en Markdown.
    - **Herramientas de Análisis:** Disponibilidad de `SQLAnalyticalTool` (para métricas de negocio) y `EventStoreTool` (para trazabilidad de eventos) con aislamiento multi-tenant estricto vía `org_id`.
    - **API de Chat Analítico:** Endpoint `POST /analytical/ask` habilitado con soporte para rate limiting por organización (10 req/min) y trazabilidad de consumo de tokens.
    - **Visualización de Jerarquía (Step 4.2):** Componente `FlowHierarchyView` desplegado. Agrupa flows por categorías, visualiza dependencias y resalta errores de grafo.
    - **Registro Enriquecido (Step 4.1):** Soporte para metadatos de jerarquía y dependencias con validación automática (DFS Cycle Detection) en el arranque del servidor.
    - **Validación de Precisión (Step 4.5):** Certificación de precisión analítica completada mediante script de seeding, alcanzando un 95% de coincidencia con el Golden Set de métricas.
    - **Fase 3 Completa:** Streaming de eventos en tiempo real (Transcripts) funcional con latencia < 500ms y visualización animada en el timeline.

- **Parcialmente Implementado:**
    - **Optimización de Prompts:** Evaluado inicialmente en 4.5, se deja como mejora continua para la Fase 5 para reducir variabilidad en resúmenes narrativos.

## 3. Contratos Técnicos Vigentes
- **API Analítica (`POST /analytical/ask`):**
    - Request: `{ "question": str, "query_type": Optional[str] }`
    - Response: `{ "question": str, "query_type": str, "data": List, "summary": str, "metadata": { "tokens_used": int, "row_count": int } }`
- **Lista de Consultas (`GET /analytical/queries`):** Devuelve las plantillas y descripciones para las Quick Queries del frontend.
- **Allowlist Analítico (`analytical_queries.py`):** Plantillas SQL pre-aprobadas para: `agent_success_rate`, `tickets_by_status`, `flow_token_consumption`, `recent_events_summary`, y `tasks_by_flow_type`.
- **Metadata de Registro (`registry.py`):** Campos `category` y `depends_on` para modelado de jerarquía.
- **API Hierarchy (`GET /flows/hierarchy`):** Entrega el mapa de procesos con estatus de validación integrado.

## 4. Decisiones de Arquitectura Tomadas
- **Integración Global vía Layout (Paso 4.4):** El chat analítico se inyecta en el `layout.tsx` del dashboard para estar disponible en cualquier contexto de navegación sin interferir con la vista principal (usando `Sheet` de Radix UI).
- **UX Reactiva (Paso 4.4):** Implementación de auto-scroll, placeholders de carga y manejo de errores 429 (Rate Limit) con feedback narrativo al usuario.
- **Asincronía en CrewAI (Paso 4.3):** Las llamadas al LLM se ejecutan mediante `run_in_executor` para evitar el bloqueo del event loop de FastAPI durante la inferencia, garantizando la responsividad del resto de la API.
- **Robustez Multi-fallback (Paso 4.3):** Implementación de pipelines de reserva basados en heurísticas locales (keywords) para garantizar una respuesta (aunque sea simplificada) ante fallos de conectividad con el proveedor de LLM.
- **Aislamiento por Herramienta (Paso 4.3):** El `org_id` se inyecta directamente en las instancias de las herramientas analíticas (heredando de `OrgBaseTool`), garantizando que el LLM solo procese datos del tenant solicitante.
- **Code-as-Schema (Paso 4.1):** Definición de dependencias en decoradores para evitar desincronización con la base de datos.
- **Validación Basada en Golden Set (Paso 4.5):** Uso de scripts de seeding dinámicos para crear escenarios deterministas (90% success, 50% success) que permiten certificar la precisión numérica del LLM sin depender de datos de producción ruidosos.
- **Protocolo de "Seeding de Precisión" (Paso 4.5):** Implementada la capacidad de limpiar e inyectar tareas sintéticas por agente para validar la capa de inteligencia de forma aislada.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 4.5  | ✅ | `test_4_5_precision.py`, `seed_precision_data.py` | Golden Set Validation / Controlled Seeding | Precisión certificada (Success Rate 90/50). |
| 4.4  | ✅ | `AnalyticalAssistantChat.tsx`, `layout.tsx`, `analytical_chat.py` | FAB Global / Sheet UI | Chat analítico operativo y validado. |
| 4.3  | ✅ | `analytical_crew.py`, `analytical.py`, `analytical_chat.py` | Asincronía LLM / Multi-fallback | Backend analítico certificado. |
| 4.2  | ✅ | `FlowHierarchyView.tsx`, `page.tsx`, `types.ts` | Error Auto-expand / Framer Motion | Visualización diagnóstica aprobada. |
| 4.1  | ✅ | `registry.py`, `main.py`, `flows.py`, `architect_flow.py` | Code-as-Schema / DFS Cycle Detection | Jerarquía de procesos validada. |
| 3.5  | ✅ | `test_3_5_latency.py`, `get_server_time.sql` | Certificación de Latencia P95 | Validado tras resolver issues de Cold Start. |

## 6. Criterios Generales de Aceptación MVP (Fase 4)
- [✅] El sistema debe ser capaz de representar visualmente las dependencias entre flows (Step 4.2).
- [✅] El backend analítico responde preguntas sobre el Event Store y métricas de negocio usando lenguaje natural (Step 4.3).
- [✅] El chat analítico lateral es accesible y funcional desde el dashboard del frontend (Step 4.4).
- [✅] Los errores en el grafo de procesos no deben impedir el funcionamiento del resto del sistema.
- [✅] Validación de precisión en respuestas analíticas (Step 4.5).

---
*Documento actualizado por el protocolo CONTEXTO tras la certificación exitosa de la Fase 4.*
