# Plan Granular de Implementación MVP — FluxAgentPro v2

Este documento desglosa las fases del MVP en pasos unitarios y atómicos para facilitar la implementación quirúrgica y la validación continua.

## User Review Required

> [!IMPORTANT]
> Se ha optado por un enfoque de **pasos unitarios**. Cada paso debe ser validado (ya sea mediante pruebas de API o verificación visual) antes de proceder con el siguiente.

---

## Fase 1: Hardening de Tickets (E4)
*Objetivo: Asegurar que el sistema de solicitudes sea robusto y confiable.*

*   **Paso 1.1 [Backend]:** Refactorizar el endpoint `POST /tickets/{id}/execute` en `src/api/routes/tickets.py`.
    *   *Detalle:* Capturar excepciones del motor de ejecución y actualizar el estado del ticket a `blocked` incluyendo el error en el campo `notes`.
*   **Paso 1.2 [Backend]:** Estandarización del `correlation_id`.
    *   *Detalle:* Asegurar que el `correlation_id` (formato `ticket-{id}`) se propague correctamente desde el router hasta el `BaseFlow` para trazabilidad cruzada.
*   **Paso 1.3 [Frontend]:** Potenciar el hook `useExecuteTicket` en `dashboard/hooks/useTickets.ts`.
    *   *Detalle:* Integrar soporte para notificaciones (Toasts) de éxito o error al disparar la ejecución.
*   **Paso 1.4 [Frontend]:** Refinar la UI de la Lista de Tickets (`tickets/page.tsx`).
    *   *Detalle:* Añadir indicadores de carga específicos por fila al ejecutar y refrescar los datos automáticamente tras la respuesta.
*   **Paso 1.5 [Validación]:** Prueba E2E de ciclo de vida.
    *   *Acción:* Crear un ticket → Ejecutar → Verificar que el `task_id` se vincula correctamente y el estado cambia a `done`/`blocked`.

---

## Fase 2: Agent Panel 2.0 (E5)
*Objetivo: Dotar a los agentes de personalidad (SOUL) y visibilidad de sus herramientas.*

*   **Paso 2.1 [DB]:** Ejecutar migración `020_agent_metadata.sql`.
    *   *Detalle:* Crear la tabla `agent_metadata` con RLS, vinculada al `agent_role` y `org_id`.
*   **Paso 2.2 [Backend]:** Evolucionar el router de agentes en `src/api/routes/agents.py`.
    *   *Detalle:* El endpoint `get_agent_detail` debe realizar un LEFT JOIN con `agent_metadata` para obtener la personalidad y descripción enriquecida.
*   **Paso 2.3 [Frontend]:** Implementar componente `AgentPersonalityCard.tsx`.
    *   *Detalle:* Mostrar el SOUL del agente no como JSON crudo, sino como una descripción narrativa legible por humanos en la pestaña "Información".
*   **Paso 2.4 [Frontend]:** Refactorizar pestaña de "Credenciales y Herramientas".
    *   *Detalle:* Utilizar la metadata del `tool_registry` para mostrar descripciones claras de qué hace cada herramienta asignada al agente.
*   **Paso 2.5 [Validación]:** Verificación de Aislamiento.
    *   *Acción:* Confirmar que el Agente A en la Org 1 no puede ver la metadata de personalidad del Agente A en la Org 2.

---

## Fase 3: Real-time Run Transcripts (E6)
*Objetivo: Transparencia total durante la ejecución de tareas de IA.*

*   **Paso 3.1 [DB]:** Habilitar Supabase Realtime.
    *   *Acción:* Ejecutar script para incluir la tabla `domain_events` en la publicación `supabase_realtime`.
*   **Paso 3.2 [Backend]:** Refinar endpoint de Transcripts en `src/api/routes/transcripts.py`.
    *   *Detalle:* Optimizar la consulta para obtener el "snapshot" inicial de eventos antes de que entre el streaming.
*   **Paso 3.3 [Frontend]:** Crear componente `TranscriptTimeline.tsx`.
    *   *Detalle:* Implementar la lógica de suscripción vía cliente de Supabase para eventos de tipo `flow_step`, `agent_thought` y `tool_output`.
*   **Paso 3.4 [Frontend]:** Integración en la Vista de Tarea.
    *   *Detalle:* Añadir una pestaña de "Live Transcript" en `tasks/[id]/page.tsx` que sea el foco principal durante ejecuciones activas.
*   **Paso 3.5 [Validación]:** Test de Latencia.
    *   *Acción:* Ejecutar un flow complejo y verificar que el transcript se actualiza en menos de 1 segundo tras el evento real.

---

## Fase 4: Capa de Inteligencia Visual y Analítica
*Objetivo: Herramientas avanzadas de supervisión y diagnóstico.*

*   **Paso 4.1 [Framework]:** Metadata de Escalamiento en el `registry.py`.
    *   *Detalle:* Añadir campos `depends_on` y `category` a los flows para modelar la jerarquía de procesos de negocio.
*   **Paso 4.2 [Frontend]:** Implementar `FlowHierarchyView.tsx`.
    *   *Detalle:* Visualización gráfica (árbol) de cómo se conectan los flows (ej. un flow de "Venta" que escala a uno de "Facturación").
*   **Paso 4.3 [Backend]:** Implementar `AnalyticalCrew` en `src/crews/analytical_crew.py`.
    *   *Detalle:* Crear un agente especializado con acceso a herramientas SQL y de EventStore para procesar consultas complejas.
*   **Paso 4.4 [Frontend]:** Implementar `AnalyticalAssistantChat.tsx`.
    *   *Detalle:* Chat lateral disponible en el dashboard de Analítica para interactuar con el crew analítico.
*   **Paso 4.5 [Validación]:** Test de Precisión Analítica.
    *   *Acción:* Preguntar al chat: "¿Cuál es el agente con mayor tasa de éxito en la última semana?" y verificar contra base de datos.
