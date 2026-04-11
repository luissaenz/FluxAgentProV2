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
    - **Fase 8 Baseline (CERRADA):** Token Tracking (Real/Estimado), Gobernanza de Datos (RLS, auditoría append-only), Dashboard Base (Métricas, Flows registrados).
    - **E4 - Tickets (Back-end):** Tabla `tickets` con RLS, endpoints CRUD y ejecución de flows asociados via `POST /tickets/{id}/execute`.
- **Parcialmente Implementado:**
    - **E4 - Tickets (UI):** Rutas creadas en `dashboard/app/(app)/tickets`, tipos TS definidos. Falta refinamiento de la vista de lista y formulario de creación.
- **No existe aún:**
    - **E6 - Run Transcripts:** No hay visualización de trazas en tiempo real en el dashboard.
    - **E5 - Agent Panel 2.0:** La vista actual es básica; falta integración profunda con métricas de eficiencia y herramientas del Vault.

## 3. Contratos Técnicos Vigentes
- **Modelos de Datos:**
    - `tickets`: `id`, `org_id`, `title`, `description`, `flow_type`, `priority`, `status`, `input_data`, `task_id`, `assigned_to`, `notes`.
    - `tasks`: Incluye `tokens_used` y `assigned_agent_role`.
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
- **Trazabilidad:** Uso de `EventStore` (tabla `domain_events`) como fuente de verdad para el historial de ejecución y futuros Transcripts.
- **Seguridad:** Aislamiento total por `org_id` usando el patrón `TenantClient` que inyecta el contexto en cada sesión de base de datos.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 8.Base | ✅ | `002_governance.sql`, `base_flow.py`, `dashboard/` | Baseline de métricas y tokens | Infraestructura core terminada. |
| 4.1 | ✅ | `019_tickets.sql` | Tabla tickets con RLS | Soporte multi-tenant integrado. |
| 4.2 | ✅ | `src/api/routes/tickets.py` | API de tickets y `/execute` | Implementación de ejecución asíncrona. |
| 4.3 | ✅ | `src/api/main.py` | Registro de router | API conectada. |

## 6. Criterios Generales de Aceptación MVP
- **Tickets:** Se puede crear, priorizar y ejecutar un flow desde un ticket.
- **Panel:** El agente muestra su historial de consumo de tokens y tareas resueltas.
- **Transcripts:** Se visualiza al menos un evento de "pensamiento" o "acción" durante la ejecución de un flow.
- **Calidad:** Cero errores de TypeScript en el build y manejo de excepciones en Python que no rompan el worker.
