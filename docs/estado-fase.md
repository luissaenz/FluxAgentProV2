# 🗺️ ESTADO DE FASE: FASE 2 - INICIADA 🏗️

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un motor de ejecución técnica a una **Plataforma de Gestión de Servicios Agentinos** estable y robusta (MVP Fase 1).
- **Pasos de la Fase:**
    1. **1.1 [Backend]:** Hardening del endpoint `/execute` (Estados `blocked`, notas de errores). [COMPLETADO]
    2. **1.2 [Backend]:** Estandarización de `correlation_id` (Trazabilidad end-to-end). [COMPLETADO]
    3. **1.3 [Frontend]:** Feedback visual en `useExecuteTicket` (Sonner Toasts). [COMPLETADO]
    4. **1.4 [Frontend]:** Refinamiento UI en Lista de Tickets (Spinners, animaciones, refresco). [COMPLETADO]
    5. **1.5 [Validación]:** Prueba E2E ciclovida completa. [COMPLETADO]
- **Dependencias:**
    - E4 Baseline (Tickets) - Finalizado con éxito.
    - Infraestructura de trazabilidad operativa.

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **E4 - Tickets (Back-end):** Endpoint `POST /tickets/{id}/execute` robusto. Maneja errores de infraestructura y lógica. Preserva historial de errores en `notes`.
    - **Trazabilidad:** Propagation de `correlation_id` (`ticket-{id}`) funcionando desde API -> Flow -> EventStore.
    - **Estabilización:** Corregidos errores de serialización JSON detectados en la extracción de IDs de tareas. El backend ahora retorna objetos `TicketResponse` completos tras ejecución.
    - **UI/UX:** Lista de tickets interactiva con indicadores de carga por fila (`animate-pulse` + spinners). Feedback proactivo vía `toast.loading` y `toast.success/error`.
    - **Fase 2 (E5) - Agent Panel 2.0:** Migración `020_agent_metadata.sql` completada. Estructura de SOUL lista para integración.
    - **Fase 3 (E6) - Run Transcripts:** Sin visualización de trazas en tiempo real.

## 3. Contratos Técnicos Vigentes
- **Modelos de Datos:**
    - `tickets`: `id`, `org_id`, `title`, `description`, `flow_type`, `priority`, `status`, `task_id`, `notes`.
    - `agent_metadata`: `id`, `org_id`, `agent_role`, `display_name`, `soul_narrative`, `avatar_url`.
- **API Endpoints:**
    - `POST /tickets/{id}/execute`: Retorna el objeto `TicketResponse` actualizado (Step 1.1 + fixes).
    - `X-Task-Correlation-ID`: Header estandarizado para trazabilidad cruzada.
- **Frontend Hooks:**
    - `useExecuteTicket`: Invalida `['tickets']` y `['ticket', ticketId]` al finalizar. Gestiona el ciclo de vida del toast id automáticamente.

## 4. Decisiones de Arquitectura Tomadas
- **Single Source of Truth:** El `correlation_id` se genera en la API y es la única clave de unión entre Tickets y Eventos de Dominio.
- **Resiliencia Frontend:** Detección de errores de red específica en los hooks para evitar que el usuario se confunda con "mensajes de error de API" cuando el problema es de conexión local.
- **Auto-mapping:** En `GenericFlow`, si no hay datos de entrada, el backend mapea automáticamente el título/descripción a la clave `text`.
- **Autonomía de DDL:** Las migraciones de base de datos deben ser autocontenidas, definiendo funciones de utilidad locales (ej: `handle_updated_at`) para evitar dependencias fallidas durante la ejecución en entornos limpios.
- **Bypass de RLS Operativo:** Todas las tablas de dominio deben incluir políticas que permitan el acceso explícito al rol `service_role` para asegurar la operatividad del backend y procesos de fondo.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 1.1 | ✅ | `src/api/routes/tickets.py` | Hardening de `/execute` | Manejo de estados `blocked` y notas de error. |
| 1.2 | ✅ | `src/flows/state.py`, `src/flows/base_flow.py` | Estandarización de `correlation_id` | Trazabilidad end-to-end con prefijos. |
| 1.3 | ✅ | `dashboard/hooks/useTickets.ts` | Feedback visual con Sonner Toasts | Toasts de carga, éxito y error detallado. |
| 1.4 | ✅ | `tickets/page.tsx` | Refinamiento de UI | Indicadores de carga por fila y spinners. |
| 1.5 | ✅ | `src/scripts/validate_e2e_lifecycle.py`, `LAST/validacion.md` | Validación E2E Certificada | Ciclo completo verificado: Ticket -> Flow -> Task -> EventStore. Todas las pruebas PASS. |
| 2.1 | ✅ | `supabase/migrations/020_agent_metadata.sql` | Esquema de Personalidad (SOUL) | Migración robustecida con bypass de `service_role` y seed data inicial. |

## 6. Criterios Generales de Aceptación MVP
- **Tickets:** Happy path completo. Gestión de errores sin crash. Persistencia en DB verificada con `correlation_id` estandarizado.
- **Calidad:** Código compila, validación técnica automatizada exitosa en entorno de desarrollo.
- **Próximo Objetivo:** Continuar Fase 2 con el **Paso 2.2 [Backend]:** Integrar `get_agent_detail` con un `LEFT JOIN` hacia la nueva tabla `agent_metadata`.
