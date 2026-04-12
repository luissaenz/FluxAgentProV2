# 🗺️ ESTADO DE FASE: FASE 2 - AGENT PANEL 🏗️

## 1. Resumen de Fase
- **Objetivo:** Dotar a los agentes de personalidad narrativa (SOUL) y enriquecer la visibilidad de sus herramientas y capacidades dentro de la plataforma (MVP Fase 2).
- **Pasos de la Fase:**
    1. **1.x [Hardening]:** Completar robustez de tickets y trazabilidad. [FINALIZADO ✅]
    2. **2.1 [DB]:** Migración `020_agent_metadata.sql` (Esquema SOUL). [COMPLETADO ✅]
    3. **2.2 [Backend]:** Enriquecimiento de `GET /agents/{id}/detail` con metadata. [COMPLETADO ✅]
    4. **2.3 [Frontend]:** Implementar componente `AgentPersonalityCard.tsx`. [PRÓXIMO 🎯]
    5. **2.4 [Frontend]:** Refactorizar pestaña de "Herramientas" (Metadata-driven UI). [PENDIENTE]
    6. **2.5 [Validación]:** Test de aislamiento multi-tenant para SOUL. [PENDIENTE]

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **Infraestructura de Tickets (Hardening):** Ciclo de vida completo (Backlog -> In Progress -> Done/Blocked) verificado. El sistema captura errores de ejecución y los persiste en el ticket.
    - **Trazabilidad (Correlation ID):** Estandarización de `correlation_id` (prefijos `ticket-`, `manual-`, `bartenders-`) propagada correctamente desde API hasta `BaseFlow` y `EventStore`.
    - **Backend de Agentes (Fase 2):** El endpoint de detalle ahora realiza un LEFT JOIN con `agent_metadata`, inyectando `display_name`, `soul_narrative` y `avatar_url`. Posee fallbacks automáticos si no hay metadata.
    - **Dominio Especializado (Bartenders NOA):** Módulo completo de operación para eventos (Preventa, Reserva, Alerta, Cierre) implementado como prueba de concepto de la flexibilidad del motor de flows.
    - **UI/UX Dashboard:** Lista de tickets con indicadores de carga síncronos, notificaciones reactivas (Sonner) y navegación fluida entre tareas y agentes.

- **Parcialmente Implementado:**
    - **Frontend de Agentes:** La vista de detalle aún muestra el `soul_json` crudo en lugar de la narrativa enriquecida. Falta el componente visual para la personalidad del agente.
    - **Real-time (Fase 3):** Los eventos de dominio se registran pero no se emiten via Supabase Realtime hacia el frontend aún.

## 3. Contratos Técnicos Vigentes
- **Modelos de Datos:**
    - `tickets`: Soporta estados `blocked` y campos de `notes` dinámicos para logs de error.
    - `agent_metadata`: Vincula rol y organización con identidad visual y narrativa.
    - `domain_events`: Almacena el rastro de ejecución vinculado por `correlation_id`.
- **API Endpoints:**
    - `POST /tickets/{id}/execute`: Orquesta la ejecución y vincula el `task_id` resultante.
    - `GET /agents/{id}/detail`: Contrato enriquecido: `{ agent: { ..., display_name, soul_narrative }, metrics: { ... }, credentials: [ ... ] }`.
    - `POST /bartenders/*`: Suite de endpoints de dominio para procesos de negocio específicos.
- **Frontend Hooks:**
    - `useExecuteTicket`: Gestiona estados locales de carga y sincronización con React Query.
    - `useAgentDetail`: Consume el contrato enriquecido del backend.

## 4. Decisiones de Arquitectura Tomadas
- **Resiliencia de Metadata:** Si un agente no tiene registro en `agent_metadata`, el backend genera un `display_name` amigable basado en su `role` y mantiene la nulidad de la narrativa sin romper la respuesta.
- **Trazabilidad por Prefijos:** Uso de esquemas de naming en el `correlation_id` para identificar el origen de la ejecución (`ticket-{id}`, `bartenders-preventa-{hash}`, etc.).
- **Despliegue de DDL:** Uso de políticas RLS que otorgan bypass al `service_role` para asegurar que el motor de ejecución no se vea bloqueado por restricciones de seguridad a nivel de fila diseñadas para usuarios.
- **Backend-Driven Forms:** Los schemas de input para los flows se definen en el servidor (`FLOW_INPUT_SCHEMAS`) para centralizar la validación, aunque el frontend aún no los consume dinámicamente al 100%.

## 5. Registro de Pasos Completados (MVP)

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 1.1 | ✅ | `src/api/routes/tickets.py` | Hardening de `/execute` | Manejo de estados `blocked` y persistencia de errores. |
| 1.2 | ✅ | `src/flows/base_flow.py` | Estandarización de `correlation_id` | Trazabilidad end-to-end garantizada. |
| 1.3 | ✅ | `dashboard/hooks/useTickets.ts` | Feedback visual Sonner | Integración de toasts de carga/éxito/error. |
| 1.4 | ✅ | `tickets/page.tsx` | Refinamiento de UI | Indicadores por fila y refresco automático. |
| 1.5 | ✅ | `tests/scripts/...` | Validación E2E Certificada | Ciclo Ticket -> Task -> Events validado. |
| 2.1 | ✅ | `supabase/migrations/020...` | Esquema SOUL (Metadata) | Tabla `agent_metadata` con RLS. |
| 2.2 | ✅ | `src/api/routes/agents.py` | Backend de Personalidad | LEFT JOIN con metadata y fallbacks de naming. |

## 6. Criterios Generales de Aceptación MVP
- **Trazabilidad:** Cualquier ejecución debe ser rastreable en el `event_store` filtrando por `correlation_id`.
- **Estabilidad:** Errores de red o de lógica del agente se muestran al usuario sin dejar el sistema en estado inconsistente.
- **Identidad:** Los agentes dejan de ser entidades puramente técnicas para tener una representación "humana" en el sistema.
- **Próximo Objetivo:** Implementar `AgentPersonalityCard.tsx` y actualizar `AgentDetailPage` para consumir los campos de identidad (display_name, narrative, avatar).
