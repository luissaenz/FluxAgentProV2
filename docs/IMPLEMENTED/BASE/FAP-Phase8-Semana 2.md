# FAP v2 — Semana 2: Definición de Desarrollo (v2 - Implementado)

> **Estado:** Implementado y verificado en código
> **Fecha:** 2026-04-06

> **Restricciones absolutas:**
> 1. Supabase almacena **solo datos del sistema agentino** — nunca datos de la operatoria
> 2. **Nunca modificar archivos de CrewAI** (`src/crews/`, `src/flows/multi_crew_flow.py`)
> 3. Token tracking se implementa en la capa FAP (BaseFlowState/EventStore), no en CrewAI
> 4. El `api.ts` existente tiene auth JWT — no reemplazar

---

## Estado real del código (verificado 2026-04-06)

### Lo que YA existe (Semana 1 completada)

| Archivo | Que tiene |
|---------|-----------|
| `src/flows/state.py` | `tokens_used` field + `update_tokens()` method |
| `src/flows/base_flow.py` | `persist_state()` escribe `tokens_used` + emite `flow.tokens_recorded` |
| `src/crews/base_crew.py` | `_extract_token_usage()` + `get_last_tokens_used()` - captura tokens reales de CrewAI |
| `src/flows/multi_crew_flow.py` | Cada crew actualiza `self.state.update_tokens(crew.get_last_tokens_used())` |
| `src/flows/dynamic_flow.py` | Cada step actualiza tokens |
| `supabase/migrations/018_flow_metrics_view.sql` | Vista `v_flow_metrics` con agregaciones |
| `src/api/routes/flow_metrics.py` | `GET /flow-metrics`, `/by-type`, `/by-type/{type}/runs`, `/by-agent` |
| `dashboard/hooks/useMetrics.ts` | Hook para métricas globales (polling 10s) |
| `dashboard/hooks/useFlowMetrics.ts` | Hook para métricas por flow-type + flow runs |
| `dashboard/components/section-cards.tsx` | 6 cards server-side (incluye Tokens totales) |
| `dashboard/app/(app)/page.tsx` | Overview con Flows Registrados + Actividad Reciente |
| `dashboard/app/(app)/workflows/page.tsx` | Lista de workflows con filtros |

### Lo que YA existe (pre-Semana 1, pre-existente)

| Archivo | Que tiene |
|---------|-----------|
| `src/api/routes/tasks.py` | `GET /tasks/{id}`, `GET /tasks` (paginated con filtros) + `tokens_used` |
| `src/api/routes/approvals.py` | `POST /approvals/{task_id}` (approve/reject) |
| `src/api/routes/workflows.py` | CRUD de `workflow_templates` |
| `src/api/routes/webhooks.py` | `POST /webhooks/{org_id}/{flow_type}` — dispara un Flow |
| `src/flows/registry.py` | Flow registry con `list_flows()`, lookup por nombre |
| `src/db/vault.py` | `get_secret()`, `list_secrets()` — Vault de secretos |
| `src/tools/base_tool.py` | `OrgBaseTool` con `_get_secret()` |
| `src/db/session.py` | `get_tenant_client()` con RLS |
| `supabase/migrations/002_governance.sql` | Tabla `tasks`, `pending_approvals`, `domain_events`, `secrets` |
| `supabase/migrations/006_workflow_templates.sql` | Tabla `workflow_templates` |
| `dashboard/app/(app)/approvals/page.tsx` | Centro de aprobaciones HITL |
| `dashboard/app/(app)/agents/page.tsx` | Grid de agentes del catalog |
| `dashboard/app/(app)/tasks/page.tsx` | Historial de tareas con filtros |
| `dashboard/app/(app)/tasks/[id]/page.tsx` | Detalle de tarea + event timeline |
| `dashboard/app/(app)/events/page.tsx` | Timeline de eventos de dominio |
| `dashboard/app/(app)/kanban/page.tsx` | Kanban board |
| `dashboard/hooks/useRealtimeDashboard.ts` | Supabase Realtime channels para tasks, approvals, events |
| `dashboard/lib/api.ts` | `fapFetch()` con JWT + X-Org-ID. `api.get/post/put/delete` |
| `dashboard/lib/types.ts` | `Task`, `Approval`, `DomainEvent`, `WorkflowTemplate`, `Agent`, etc. |

---

## Lo que SE IMPLEMENTÓ en Semana 2 (2026-04-06)

### Entregable 4: Levantar Tickets (simplificado)

**Decisión de diseño:** En lugar de un sistema completo de tickets (tabla + CRUD), se implementó un diálogo de ejecución directa que reutiliza el sistema existente de flows.

**Archivos creados:**

| Archivo | Descripción |
|---------|-------------|
| `src/api/routes/flows.py` | `GET /flows/available` + `POST /flows/{type}/run` — lista flows y ejecuta |
| `dashboard/hooks/useFlows.ts` | Hook para obtener flows disponibles + ejecutar |
| `dashboard/components/flows/RunFlowDialog.tsx` | Dialog para seleccionar flow y ejecutar con parámetros |
| `dashboard/app/(app)/workflows/page.tsx` | Ya tenía trigger manual — ahora tiene botón "Ejecutar Flow" |

**Características implementadas:**
- Lista de flows disponibles desde el registry
- Schemas de input predefinidos para Bartenders (preventa, reserva, alerta, cierre)
- Ejecución en background con task_id devuelto
- Formulario dinámico basado en el schema del flow

**No implementado (del documento original):**
- Tabla `tickets` separada
- Estados de ticket (backlog → todo → in_progress → done)
- Prioridades formales
- Asignación a agentes

---

### Entregable 5: Panel de Agente

**Archivos creados/modificados:**

| Archivo | Descripción |
|---------|-------------|
| `src/api/routes/flow_metrics.py` | Endpoint `/flow-metrics/by-agent` — agrega tokens por agente |
| `dashboard/hooks/useAgentMetrics.ts` | Hook para métricas de agentes |
| `dashboard/app/(app)/agents/[id]/page.tsx` | Panel de agente enriquecido con tokens |

**Características implementadas:**
- Panel de tokens consumidos (mostrando total por agente)
- Link al Vault para credenciales
- SOUL definition (ya existía)
- Configuración (max_iter, allowed_tools)

**No implementado (del documento original):**
- Historial de tareas del agente (requiere columna `assigned_agent` en tasks)
- Endpoint `/agents/{role}/detail` más completo
- Tabs con vista de tareas y credentials

---

### Entregable 6: Run Transcript

**Estado:** No implementado en esta semana.

**Pendiente para futura iteración:**
- Endpoint `/transcripts/{task_id}` 
- Supabase Realtime subscription para streaming
- Hook `useFlowTranscript.ts`
- UI de transcript en tiempo real

---

## Modelo de datos actual

### tasks (ya existe)
```sql
tasks:
  id              UUID PRIMARY KEY
  org_id          TEXT NOT NULL
  flow_type       TEXT NOT NULL
  status          TEXT DEFAULT 'pending'
  input_data      JSONB
  result          JSONB
  error           TEXT
  tokens_used     INTEGER DEFAULT 0  -- Semester 1: token tracking real
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ
```

### domain_events (ya existe)
```sql
domain_events:
  id              UUID PRIMARY KEY
  org_id          TEXT NOT NULL
  aggregate_type  TEXT
  aggregate_id    TEXT
  event_type      TEXT
  payload         JSONB
  actor           TEXT
  sequence        INTEGER
  created_at      TIMESTAMPTZ
```

---

## Gaps restantes (para futura iteración)

| Gap | Impacto | Prioridad |
|-----|---------|-----------|
| Sistema de tickets formal | No hay ciclo de vida de solicitudes estructurado | Media |
| Transcript en tiempo real | Debugging difícil de flows en ejecución | Alta |
| Columna `assigned_agent` en tasks | No se puede filtrar tareas por agente | Baja |
| Endpoint `/agents/{role}/detail` completo | Panel de agente limitada la visibilidad | Baja |

---

## Comparativa: Documento vs Implementado

| Feature | Documento v1 | Implementado v2 |
|---------|-------------|-----------------|
| Ticket table | ✅ `019_tickets.sql` | ❌ (simplificado a dialog) |
| CRUD tickets | ✅ `POST/GET/PATCH/DELETE` | ❌ |
| UI tickets | ✅ `/tickets/page.tsx` | ❌ |
| RunFlowDialog | ❌ | ✅ `RunFlowDialog.tsx` |
| `/flows/available` | ❌ | ✅ `flows.py` |
| Token tracking real | ✅ (en diseño) | ✅ (implementado en Semana 1) |
| Panel agente tokens | ✅ `agents/[id]` mejorado | ✅ Parcial |
| `/flow-metrics/by-agent` | ❌ | ✅ `flow_metrics.py` |
| Run transcript | ✅ | ❌ No implementado |

---

## Decisiones de diseño tomadas

1. **Tickets simplificados:** En lugar de crear una tabla separada de tickets, reutilamos el sistema de flows existente. El "ticket" es el propio task cuando se ejecuta desde la UI.

2. **Token tracking en BaseCrew:** Los tokens se capturan en `_extract_token_usage()` del CrewAI result, se almacenan en el estado del flow, y se persisten en `tasks.tokens_used`.

3. **Panel de agente incremental:** En lugar de reescribir completamente la página, se agregó el componente de tokens y el link al Vault sobre la página existente.

4. **Run transcript diferido:** Requiere Supabase Realtime setup más complejo. Postergado para próxima iteración.

---

## Próximos pasos sugeridos (Semana 3)

1. **Sistema de tickets completo** — si el usuario necesita ciclo de vida formal
2. **Run transcript** — para debugging en tiempo real
3. **Cron scheduling** — configurar periodicidad de flows (ya existe scheduler en `bartenders_jobs.py`)
4. **Inbox** — mensajes de agentes al humano (relacionado con HITL)

---

## Archivos tocados en esta semana

### Backend
- `src/api/routes/flows.py` (NUEVO)
- `src/api/routes/flow_metrics.py` (MODIFICADO - agregado by-agent)
- `src/api/routes/tasks.py` (MODIFICADO - tokens_used en response)
- `src/api/main.py` (MODIFICADO - registrado flows_router)
- `src/crews/base_crew.py` (MODIFICADO - token extraction)
- `src/flows/multi_crew_flow.py` (MODIFICADO - token tracking)
- `src/flows/dynamic_flow.py` (MODIFICADO - token tracking)

### Frontend
- `dashboard/hooks/useFlows.ts` (NUEVO)
- `dashboard/hooks/useAgentMetrics.ts` (NUEVO)
- `dashboard/components/flows/RunFlowDialog.tsx` (NUEVO)
- `dashboard/app/(app)/workflows/page.tsx` (MODIFICADO - agregado RunFlowDialog)
- `dashboard/app/(app)/agents/[id]/page.tsx` (MODIFICADO - panel de tokens)