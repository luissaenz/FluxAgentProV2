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
    - **E4 - Tickets (Back-end):** Tabla `tickets` con RLS, endpoints CRUD y ejecución de flows. Hardening completo: estado `blocked`, preservación de notas, trazabilidad via `correlation_id`.
    - **E4 - Tickets (UX/Feedback):** Hook `useExecuteTicket` potenciado con notificaciones de ciclo de vida (Loading, Success, Error). Trazabilidad visual de `task_id` iniciada. Notificaciones específicas para errores de backend y errores de red.
    - **Trazabilidad (CERRADA):** Infraestructura de `correlation_id` estandarizada (`ticket-{id}`) de extremo a extremo. Columna indexada en `domain_events`.
- **Parcialmente Implementado:**
    - **E4 - Tickets (UI):** Vistas de lista (`tickets/page.tsx`) y detalle (`tickets/[id]/page.tsx`) funcionales pero con diseño básico. Los botones de ejecución ya integran el feedback visual del Step 1.3.
- **No existe aún:**
    - **E6 - Run Transcripts:** No hay visualización de trazas en tiempo real.
    - **E5 - Agent Panel 2.0:** Falta integración con personalidad (SOUL) y herramientas del Vault.

## 3. Contratos Técnicos Vigentes
- **Modelos de Datos:**
    - `tickets`: `id`, `org_id`, `title`, `description`, `flow_type`, `priority`, `status`, `task_id`, `notes`.
    - `domain_events`: Columna `correlation_id` (TEXT) indexada.
- **API Endpoints:**
    - `POST /tickets/{id}/execute`: Retorna `{ "status": "success", "task_id": "..." }` o error con `detail.error`.
- **Frontend Hooks:**
    - `useExecuteTicket`: Firma actualizada: `mutate({ ticketId, ticketTitle })`. Integra `sonner` para feedback.
- **Convenciones:**
    - Trazabilidad forzada vía `X-Task-Correlation-ID` (en backend) y visualización truncada en UI.

## 4. Decisiones de Arquitectura Tomadas
- **Feedback Proactivo:** Se ha decidido integrar el estado de carga (`toast.loading`) directamente en el hook de mutación para garantizar consistencia entre todas las vistas que ejecutan tickets.
- **Delegación de Error:** La extracción del mensaje de error se centraliza en `api.ts` para que todos los hooks consuman un `error.message` ya sanitizado y rico en contexto (priorizando el `detail` de FastAPI).
- **Persistencia de Trazas:** Se utiliza el prefijo `ticket-` en el `correlation_id` para permitir la reconstrucción del historial de ejecución desde la vista de tickets sin acoplamiento directo entre tablas.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 4.4 | ✅ | `src/api/routes/tickets.py` | Hardening de `/execute` | Manejo de estados `blocked` y notas de error. |
| 1.2 | ✅ | `src/flows/state.py`, `src/api/routes/tickets.py` | Estandarización de `correlation_id` | Trazabilidad end-to-end con prefijos. |
| 1.3 | ✅ | `dashboard/hooks/useTickets.ts`, `tickets/page.tsx` | Feedback visual con Sonner Toasts | Toasts de éxito con Task ID y errores específicos. |

## 6. Criterios Generales de Aceptación MVP
- **Tickets:** Se puede crear, priorizar y ejecutar un flow desde un ticket con visibilidad del resultado.
- **Transcripts:** Se visualiza al menos un evento de "pensamiento" durante la ejecución.
- **Calidad:** Cero errores de TypeScript en el build (`npm run build`). Robustez ante caídas de red o errores de lógica del agente.

