# 🗺️ ESTADO DE FASE: FASE 2 - AGENT PANEL 🏗️

## 1. Resumen de Fase
- **Objetivo:** Dotar a los agentes de personalidad narrativa (SOUL) y enriquecer la visibilidad de sus herramientas y capacidades dentro de la plataforma (MVP Fase 2).
- **Pasos de la Fase:**
    1. **1.x [Hardening]:** Completar robustez de tickets y trazabilidad. [FINALIZADO ✅]
    2. **2.1 [DB]:** Migración `020_agent_metadata.sql` (Esquema SOUL). [COMPLETADO ✅]
    3. **2.2 [Backend]:** Enriquecimiento de `GET /agents/{id}/detail` con metadata. [COMPLETADO ✅]
    4. **2.3 [Frontend]:** Implementar componente `AgentPersonalityCard.tsx` (Premium). [COMPLETADO ✅]
    5. **2.4 [Frontend]:** Refactorizar pestaña de "Herramientas" (Metadata-driven UI). [COMPLETADO ✅]
    6. **2.5 [Validación]:** Test de aislamiento multi-tenant para SOUL. [PENDIENTE]

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **Identidad de Agentes (SOUL UI Premium):** Refabricación de `AgentPersonalityCard` con **Framer Motion** (animaciones suave de entrada) y **Radix UI Avatar** (gestión robusta de fallbacks). Muestra narrativa SOUL con estilo tipográfico diferenciado.
    - **Capacidades de Agentes (Tools UI):** Nuevo componente `AgentToolsCard` que transforma la lista técnica de herramientas en un grid de tarjetas inteligentes. Muestra descripciones legibles mapeadas desde `lib/tool-registry-metadata.ts` y badges de "Aprobación", "Credencial" y "Timeout".
    - **Infraestructura de Tickets (Hardening):** Ciclo de vida completo (Backlog -> In Progress -> Done/Blocked) verificado. El sistema captura errores de ejecución y los persiste en el ticket.
    - **Trazabilidad (Correlation ID):** Estandarización de `correlation_id` (prefijos `ticket-`, `manual-`, `bartenders-`) propagada correctamente desde API hasta `BaseFlow` y `EventStore`.
    - **Backend de Agentes (Fase 2):** El endpoint de detalle ahora realiza un LEFT JOIN con `agent_metadata`, inyectando `display_name`, `soul_narrative` y `avatar_url`. Posee fallbacks automáticos si no hay metadata.
    - **Dominio Especializado (Bartenders NOA):** Módulo completo de operación para eventos (Preventa, Reserva, Alerta, Cierre) implementado como prueba de concepto de la flexibilidad del motor de flows.
    - **UI/UX Dashboard:** Lista de tickets con indicadores de carga síncronos, notificaciones reactivas (Sonner) y navegación fluida entre tareas y agentes.

- **Parcialmente Implementado:**
    - **Real-time (Fase 3):** Los eventos de dominio se registran pero no se emiten via Supabase Realtime hacia el frontend aún.

## 3. Contratos Técnicos Vigentes
- **Modelos de Datos:**
    - `tickets`: Soporta estados `blocked` y campos de `notes` dinámicos para logs de error.
    - `agent_metadata`: Vincula rol y organización con identidad visual y narrativa.
    - `domain_events`: Almacena el rastro de ejecución vinculado por `correlation_id`.
- **API Endpoints:**
    - `POST /tickets/{id}/execute`: Orquesta la ejecución y vincula el `task_id` resultante.
    - `GET /agents/{id}/detail`: Contrato enriquecido: `{ agent: { ..., display_name, soul_narrative }, metrics: { ... }, credentials: [ ... ] }`.
- **Frontend Hooks & Types:**
    - `lib/types.ts`: Interfaz `Agent` enriquecida con campos SOUL. `AgentDetail` incluye `credentials`.
    - `lib/tool-registry-metadata.ts`: Mapping estático para descripciones ricas de herramientas.
- **Librerías Adicionales:**
    - `framer-motion`: Animaciones premium.
    - `@radix-ui/react-avatar`: Componente de identidad estándar.

## 4. Decisiones de Arquitectura Tomadas
- **Resiliencia de Metadata:** Si un agente no tiene registro en `agent_metadata`, el backend genera un `display_name` amigable basado en su `role` y mantiene la nulidad de la narrativa sin romper la respuesta.
- **Estructura de Componentes por Dominio:** Los componentes específicos de agentes residen en `dashboard/components/agents/`. Se eliminaron duplicados en `shared/`.
- **Trazabilidad por Prefijos:** Uso de esquemas de naming en el `correlation_id` para identificar el origen de la ejecución (`ticket-{id}`).
- **Premium UI standard:** Uso obligatorio de Framer Motion para componentes de identidad para elevar la percepción de calidad del MVP.

## 5. Registro de Pasos Completados (Phase 2 Focus)

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 2.1 | ✅ | `supabase/migrations/020...` | Esquema SOUL (Metadata) | Tabla `agent_metadata` con RLS. |
| 2.2 | ✅ | `src/api/routes/agents.py` | Backend de Personalidad | LEFT JOIN con metadata y fallbacks de naming. |
| 2.3 | ✅ | `AgentPersonalityCard.tsx` | UI Premium (Framer/Radix) | Animaciones de entrada y fallbacks de Radix. |
| 2.4 | ✅ | `AgentToolsCard.tsx` | Metadata-driven Tools | Uso de mapping estático centralizado. |

## 6. Criterios Generales de Aceptación MVP
Definición de "listo" para esta fase:
- El happy path de visualización de perfil funciona end-to-end (DB -> API -> UI).
- Las herramientas muestran descripción narrativa, no solo nombres técnicos.
- La identidad del agente (Avatar/Name) es consistente en todo el dashboard.
- El código compila sin errores y utiliza componentes estandarizados (Shadcn/Radix).
- Las animaciones no impactan negativamente en la performance percibida.

---
*Documento actualizado por el protocolo CONTEXTO de Antigravity.*
