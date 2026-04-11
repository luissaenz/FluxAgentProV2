# 🗺️ ESTADO DE FASE: FASE 8 - SEMANA 2

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un motor de ejecución técnica a una **Plataforma de Gestión de Servicios Agentinos** estable y lista para MVP.
- **Pasos de la Fase:**
    1. **E4: Sistema de Tickets** (Backlog y gestión de demanda). [EN PROGRESO]
    2. **E5: Panel de Agente 2.0** (Visibilidad operativa y eficiencia). [PENDIENTE]
    3. **E6: Run Transcripts** (Transparencia en tiempo real de ejecución). [PENDIENTE]
- **Dependencias:**
    - E4 requiere la infraestructura de `organizations` y `tasks` (Fase 8 Baseline - Completado).
    - E6 requiere el `EventStore` para emitir trazas de pensamiento de la IA (Fase 8 Baseline - Completado).

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **E4 - Tickets (Back-end):** Tabla `tickets` con RLS, endpoints CRUD y ejecución de flows. Hardening completo: manejo de errores con estado `blocked`, preservación de notas, trazabilidad via `correlation_id`, vinculación de `task_id` incluso en fallos.
    - **Estandarización del `correlation_id` (CERRADA):** Infraestructura de tracing de extremo a extremo implementada. Columna `correlation_id` indexada en `domain_events`. Propagación obligatoria desde routers (Tickets, Webhooks, Manual, Chat) hasta el núcleo de ejecución.
- **Parcialmente Implementado:**
    - **E4 - Tickets (UI):** Rutas creadas en `dashboard/app/(app)/tickets`, tipos TS definidos. Falta refinamiento de la vista de lista y formulario de creación.
- **No existe aún:**
    - **E6 - Run Transcripts:** No hay visualización de trazas en tiempo real en el dashboard.
    - **E5 - Agent Panel 2.0:** La vista actual es básica; falta integración profunda con métricas de eficiencia y herramientas del Vault.

## 3. Contratos Técnicos Vigentes
- **Modelos de Datos:**
    - `tickets`: `id`, `org_id`, `title`, `description`, `flow_type`, `priority`, `status`, `input_data`, `task_id`, `assigned_to`, `notes`.
    - `tasks`: Incluye `tokens_used` y `assigned_agent_role`.
    - `domain_events`: Ahora incluye columna `correlation_id` (TEXT) indexada para auditoría de trazas.
    - `BaseFlowState`: Campo `correlation_id` (str) obligatorio para garantizar trazabilidad desde el inicio.
- **Endpoints API:**
    - `/tickets`: CRUD completo + `/execute`.
    - `/flow-metrics`: Métricas por flow y por agente.
    - `/flows`: Registro y ejecución directa (legacy/admin).
- **Convenciones:**
    - Soft-delete en tickets vía `status = 'cancelled'`.
    - Multi-tenant forzado vía `X-Org-ID` header y RLS en Postgres.
- **Estructura:**
    - `src/api/routes`: Modularización por recurso.
    - `dashboard/hooks`: Lógica de datos desacoplada de la UI.

## 4. Decisiones de Arquitectura Tomadas
- **Patrón de Ejecución:** Los tickets desacoplan la *solicitud* de la *ejecución*. Un ticket puede estar en backlog antes de convertirse en una `task` de ejecución.
- **Trazabilidad de Extremo a Extremo:** Cada origen de disparo utiliza prefijos semánticos obligatorios en el `correlation_id`: `ticket-{id}`, `manual-{type}-{org_prefix}-{uuid}`, `webhook-{uuid}`, `chat-{conv_id}`.
- **Persistencia Directa en Eventos:** Se prioriza la persistencia del `correlation_id` en la tabla `domain_events` como columna indexada de primer nivel para habilitar los futuros *Run Transcripts* con alto rendimiento (evitando JOINs con snapshots).
- **Soporte Legacy:** El sistema carga estados antiguos asignando un ID `legacy-task-{id}` automáticamente para evitar fallos de validación en ejecuciones previas a la Fase 8.
- **Delegación de Emisión:** Se centraliza la emisión de eventos de estado de flujo en `BaseFlow`, eliminando emisiones manuales duplicadas en routers para mantener la integridad de la traza.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 8.Base | ✅ | `002_governance.sql`, `base_flow.py`, `dashboard/` | Baseline de métricas y tokens | Infraestructura core terminada. |
| 4.1 | ✅ | `019_tickets.sql` | Tabla tickets con RLS | Soporte multi-tenant integrado. |
| 4.2 | ✅ | `src/api/routes/tickets.py` | API de tickets y `/execute` | Implementación de ejecución asíncrona. |
| 4.3 | ✅ | `src/api/main.py` | Registro de router | API conectada. |
| 4.4 | ✅ | `src/api/routes/webhooks.py`, `src/api/routes/tickets.py` | Hardening de `/execute`: execute_flow retorna Dict con error/task_id, helpers para blocked/done, preservación de notas | 8/8 criterios cumplidos, 17 tests, validación APROBADA. |
| 1.2 | ✅ | `021_add_event_correlation.sql`, `src/flows/state.py`, `src/api/routes/chat.py` | Estandarización de `correlation_id` con prefijos semánticos y persistencia en DB | Trazabilidad end-to-end garantizada. |

## 6. Criterios Generales de Aceptación MVP
- **Tickets:** Se puede crear, priorizar y ejecutar un flow desde un ticket.
- **Panel:** El agente muestra su historial de consumo de tokens y tareas resueltas.
- **Transcripts:** Se visualiza al menos un evento de "pensamiento" o "acción" durante la ejecución de un flow.
- **Calidad:** Cero errores de TypeScript en el build y manejo de excepciones en Python que no rompan el worker.
