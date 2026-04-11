# FAP v2 — Semana 2: Definición Final del MVP (Baseline Fase 8)

> **Estado del Proyecto:** ✅ Fase 8 Baseline CERRADA (Token Tracking + Infraestructura Core).
> **Objetivo Actual:** Implementar los 3 pilares finales para el MVP (Tickets, Transcripts y Agent Panel).

## Resumen de Cierre de Fase 8 (Baseline)
A partir de abril de 2026, el sistema cuenta con una base sólida de gobernanza y trazabilidad. Los siguientes componentes se consideran **Producción-Ready** y no se tocarán más allá de mantenimiento:

1. **Token Tracking Híbrido:** Real (kickoff_async) para flows de IA y Estimado para flows deterministas (Bartenders).
2. **Gobernanza de Datos:** Persistencia de estados, métricas acumulativas y auditoría de eventos append-only.
3. **Dashboard Base:** Visualización de métricas generales, lista de flows disponibles y ejecución manual rápida.
4. **Auth & Multitenancy:** Aislamiento por organización y autenticación JWT integrada.


---

## Estado real del codigo (verificado archivo por archivo)

### Lo que YA existe (Semana 1 completada)

| Componente | Archivo | Detalle |
|------------|---------|---------|
| `tokens_used` en tasks | `002_governance.sql:28` | `INTEGER DEFAULT 0` |
| `assigned_agent_role` en tasks | `002_governance.sql:21` | `TEXT` — **NO crear `assigned_agent`** |
| `update_tokens()` en state | `src/flows/state.py:110-113` | Existe |
| `persist_state()` escribe tokens | `src/flows/base_flow.py:219` | Existe |
| Evento `flow.tokens_recorded` | `src/flows/base_flow.py:145-154` | Existe |
| Vista `v_flow_metrics` | `018_flow_metrics_view.sql` | Existe |
| `GET /flow-metrics` | `src/api/routes/flow_metrics.py` | 4 endpoints (incluye `/by-agent`) |
| `useMetrics` hook | `dashboard/hooks/useMetrics.ts` | Polling 10s |
| `useFlowMetrics` hook | `dashboard/hooks/useFlowMetrics.ts` | Polling 10s |
| `useAgentMetrics` hook | `dashboard/hooks/useAgentMetrics.ts` | Consulta `/flow-metrics/by-agent` |
| Tipos TS metricas | `dashboard/lib/types.ts:101+` | `OverviewMetrics`, `FlowTypeMetrics`, `FlowRun` |
| SectionCards 6 cards | `dashboard/components/section-cards.tsx` | Server-side via `useMetrics` |
| Overview page | `dashboard/app/(app)/page.tsx` | Flows registrados + Actividad reciente |

### Lo que YA existe (pre-Semana 1, pre-existente)

| Componente | Archivo | Detalle |
|------------|---------|---------|
| `GET /flows/available` | `src/api/routes/flows.py:95-110` | Lista flows del registry |
| `POST /flows/{type}/run` | `src/api/routes/flows.py:113-140` | Ejecuta flow en background |
| `FLOW_INPUT_SCHEMAS` | `src/api/routes/flows.py:38-85` | Schemas para bartenders |
| `useFlows` hook | `dashboard/hooks/useFlows.ts` | Lista + ejecuta flows |
| `RunFlowDialog` | `dashboard/components/flows/RunFlowDialog.tsx` | Dialog con selector + form |
| Boton "Ejecutar Flow" | `dashboard/app/(app)/workflows/page.tsx:40` | Integrado en workflows page |
| `GET /tasks/{id}` | `src/api/routes/tasks.py:56-68` | Retorna `tokens_used` |
| `GET /tasks` | `src/api/routes/tasks.py:71-95` | Paginated, incluye `tokens_used` |
| `TaskResponse` model | `src/api/routes/tasks.py:22-32` | Incluye `tokens_used: int` |
| Agent detail page | `dashboard/app/(app)/agents/[id]/page.tsx` | SOUL + tokens + config |
| Agent list page | `dashboard/app/(app)/agents/page.tsx` | Grid de agentes |
| `GET /flow-metrics/by-agent` | `src/api/routes/flow_metrics.py:106-138` | Heuristic match role→flow_type |
| Agents router | **NO existe** como `src/api/routes/agents.py` | Metricas via `/flow-metrics/by-agent` |
| Flows router | `src/api/main.py:23` | Registrado como `flows_router` |
| `execute_flow()` | `src/api/routes/webhooks.py:90-107` | Background execution compartida |
| EventStore | `src/events/store.py` | Append-only + append_sync |
| Vault | `src/db/vault.py` | `get_secret()`, `list_secrets()` |
| `BaseCrew._extract_token_usage()` | `src/crews/base_crew.py:134-167` | Existe (lee crew.result) |
| `BaseCrew.get_last_tokens_used()` | `src/crews/base_crew.py:169-171` | Existe |

### El Salto al MVP: De Aplicación Core a Plataforma de Gestión

El objetivo del MVP es transformar a FluxAgentPro de un "motor de ejecución" a una **Plataforma de Gestión de Servicios Agentinos**. Para lograrlo, los siguientes tres entregables cierran el ciclo de vida del producto:

| Entregable | Concepto | Valor para el MVP |
|------------|----------|-------------------|
| **E4: Sistema de Tickets** | Gestión de Demanda | Permite desacoplar la solicitud de la ejecución, priorizar trabajo y trackear backlog de forma profesional. |
| **E5: Panel de Agente 2.0** | Visibilidad Operativa | Centro de mando para cada agente: historial de tareas, herramientas del Vault y eficiencia. |
| **E6: Run Transcripts** | Transparencia (Wow Factor) | Visualización en tiempo real de qué está pensando y haciendo la IA durante un run. |

---


## Entregable 4 — Levantar Tickets

### Contexto

Hoy se puede ejecutar un flow via `POST /flows/{type}/run` o `RunFlowDialog`. No hay forma de:
- Solicitar trabajo que queda en backlog
- Priorizar solicitudes
- Asignar a un agente especifico
- Ver historial de solicitudes con estado
- Vincular una ejecucion con la solicitud original

### Modelo de datos

```
tickets:
  id              UUID PRIMARY KEY
  org_id          TEXT NOT NULL          -- multi-tenant via RLS
  title           TEXT NOT NULL
  description     TEXT
  flow_type       TEXT                   -- Flow a ejecutar (FK implicita a registry)
  priority        TEXT DEFAULT 'medium'  -- low, medium, high, urgent
  status          TEXT DEFAULT 'backlog' -- backlog, todo, in_progress, done, blocked, cancelled
  input_data      JSONB                  -- parametros para el Flow
  task_id         UUID                   -- FK a tasks.id (se llena al ejecutar)
  created_by      TEXT                   -- user_id del creador
  assigned_to     TEXT                   -- agent_role asignado (opcional)
  notes           TEXT                   -- notas del operador
  created_at      TIMESTAMPTZ DEFAULT now()
  updated_at      TIMESTAMPTZ DEFAULT now()
  resolved_at     TIMESTAMPTZ
```

### Cambios necesarios

#### Paso 4.1 — Migracion `019_tickets.sql` (CREAR)

```sql
-- supabase/migrations/019_tickets.sql

-- Tabla de tickets (solicitudes de trabajo)
CREATE TABLE IF NOT EXISTS tickets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    title           TEXT NOT NULL,
    description     TEXT,
    flow_type       TEXT,
    priority        TEXT NOT NULL DEFAULT 'medium',
    status          TEXT NOT NULL DEFAULT 'backlog',
    input_data      JSONB,
    task_id         UUID,
    created_by      TEXT,
    assigned_to     TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_tickets_org ON tickets(org_id);
CREATE INDEX IF NOT EXISTS idx_tickets_org_status ON tickets(org_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_task ON tickets(task_id);

-- RLS — MISMO PATRON que tasks (010_service_role_rls_bypass)
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY tickets_org_access ON tickets
    FOR ALL
    USING (
        auth.role() = 'service_role'
        OR org_id::text = current_org_id()
    );

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_tickets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_tickets_updated_at();
```

#### Paso 4.2 — `src/api/routes/tickets.py` (CREAR)

```python
"""Endpoints para gestion de tickets (solicitudes de trabajo)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ..middleware import require_org_id
from ...db.session import get_tenant_client
from ...flows.registry import flow_registry

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ── Request/Response models ─────────────────────────────────


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    flow_type: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    input_data: Optional[Dict[str, Any]] = None
    assigned_to: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class TicketResponse(BaseModel):
    id: str
    org_id: str
    title: str
    description: Optional[str] = None
    flow_type: Optional[str] = None
    priority: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None


class TicketsListResponse(BaseModel):
    items: List[TicketResponse]
    total: int


# ── Helpers ─────────────────────────────────────────────────


def _to_ticket_response(row: dict) -> TicketResponse:
    return TicketResponse(
        id=row["id"],
        org_id=str(row["org_id"]),
        title=row["title"],
        description=row.get("description"),
        flow_type=row.get("flow_type"),
        priority=row.get("priority", "medium"),
        status=row.get("status", "backlog"),
        input_data=row.get("input_data"),
        task_id=row.get("task_id"),
        created_by=row.get("created_by"),
        assigned_to=row.get("assigned_to"),
        notes=row.get("notes"),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        resolved_at=str(row["resolved_at"]) if row.get("resolved_at") else None,
    )


# ── Routes ──────────────────────────────────────────────────


@router.get("", response_model=TicketsListResponse)
async def list_tickets(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = Query(None),
    flow_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Lista tickets con filtros opcionales."""
    with get_tenant_client(org_id) as db:
        query = db.table("tickets").select("*", count="exact")

        if status:
            query = query.eq("status", status)
        if flow_type:
            query = query.eq("flow_type", flow_type)
        if priority:
            query = query.eq("priority", priority)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    return TicketsListResponse(
        items=[_to_ticket_response(t) for t in (result.data or [])],
        total=result.count or 0,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    org_id: str = Depends(require_org_id),
):
    """Obtiene un ticket por ID."""
    with get_tenant_client(org_id) as db:
        result = (
            db.table("tickets")
            .select("*")
            .eq("id", ticket_id)
            .maybe_single()
            .execute()
        )

    if result.data is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return _to_ticket_response(result.data)


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    body: TicketCreate,
    org_id: str = Depends(require_org_id),
):
    """Crea un nuevo ticket."""
    # Validar flow_type si se proporciona
    if body.flow_type and not flow_registry.has(body.flow_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Flow type '{body.flow_type}' not found. "
                f"Available: {flow_registry.list_flows()}"
            ),
        )

    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    ticket_data: Dict[str, Any] = {
        "id": ticket_id,
        "org_id": org_id,
        "title": body.title,
        "description": body.description,
        "flow_type": body.flow_type,
        "priority": body.priority,
        "status": "backlog",
        "input_data": body.input_data,
        "created_at": now,
        "updated_at": now,
    }
    if body.assigned_to:
        ticket_data["assigned_to"] = body.assigned_to

    with get_tenant_client(org_id) as db:
        result = db.table("tickets").insert(ticket_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create ticket")

    return _to_ticket_response(result.data[0])


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    org_id: str = Depends(require_org_id),
):
    """Actualiza un ticket (estado, notas, asignacion)."""
    update_data: Dict[str, Any] = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if update_data.get("status") in ("done", "cancelled"):
        update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()

    with get_tenant_client(org_id) as db:
        result = (
            db.table("tickets")
            .update(update_data)
            .eq("id", ticket_id)
            .execute()
        )

    if not result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return _to_ticket_response(result.data[0])


@router.post("/{ticket_id}/execute")
async def execute_ticket(
    ticket_id: str,
    org_id: str = Depends(require_org_id),
):
    """
    Ejecuta el Flow asociado a un ticket.
    - Verifica que el ticket existe y tiene flow_type
    - Cambia status a in_progress
    - Dispara el Flow via background task (reutiliza execute_flow de webhooks)
    - Al completar, vincula task_id al ticket y actualiza status
    """
    from .webhooks import execute_flow
    from fastapi import BackgroundTasks

    with get_tenant_client(org_id) as db:
        ticket_result = (
            db.table("tickets")
            .select("*")
            .eq("id", ticket_id)
            .maybe_single()
            .execute()
        )

    if not ticket_result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket = ticket_result.data
    if not ticket.get("flow_type"):
        raise HTTPException(
            status_code=400,
            detail="Ticket has no flow_type to execute",
        )

    if ticket.get("status") in ("in_progress", "done"):
        raise HTTPException(
            status_code=409,
            detail=f"Ticket is already {ticket['status']}",
        )

    if not flow_registry.has(ticket["flow_type"]):
        raise HTTPException(
            status_code=404,
            detail=f"Flow type '{ticket['flow_type']}' not found",
        )

    # Cambiar a in_progress
    now = datetime.now(timezone.utc).isoformat()
    with get_tenant_client(org_id) as db:
        db.table("tickets").update({
            "status": "in_progress",
            "updated_at": now,
        }).eq("id", ticket_id).execute()

    # Disparar el Flow en background — usamos el patron de webhooks.py
    # pero necesitamos pasar BackgroundTasks — la forma mas limpia es
    # crear un helper async directo que actualice el ticket al completar.
    import asyncio
    from uuid import uuid4

    correlation_id = f"ticket-{ticket_id}"
    task_id = None

    try:
        task_id = await execute_flow(
            flow_type=ticket["flow_type"],
            org_id=org_id,
            input_data=ticket.get("input_data") or {},
            correlation_id=correlation_id,
            callback_url=None,
        )
    except Exception as exc:
        # Si falla, marcar ticket como blocked
        with get_tenant_client(org_id) as db:
            db.table("tickets").update({
                "status": "blocked",
                "notes": f"Execution error: {str(exc)}",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", ticket_id).execute()
        raise HTTPException(
            status_code=500,
            detail=f"Flow execution failed: {str(exc)}",
        )

    # Vincular task_id y actualizar estado
    final_status = "done"  # Asumimos exito si no hubo excepcion
    with get_tenant_client(org_id) as db:
        db.table("tickets").update({
            "task_id": task_id,
            "status": final_status,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", ticket_id).execute()

    return {
        "ticket_id": ticket_id,
        "task_id": task_id,
        "status": final_status,
    }


@router.delete("/{ticket_id}", response_model=TicketResponse)
async def delete_ticket(
    ticket_id: str,
    org_id: str = Depends(require_org_id),
):
    """Elimina un ticket (soft-delete: status = cancelled)."""
    now = datetime.now(timezone.utc).isoformat()
    with get_tenant_client(org_id) as db:
        result = (
            db.table("tickets")
            .update({
                "status": "cancelled",
                "resolved_at": now,
                "updated_at": now,
            })
            .eq("id", ticket_id)
            .execute()
        )

    if not result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return _to_ticket_response(result.data[0])
```

#### Paso 4.3 — `src/api/main.py`: registrar router

Agregar junto a los imports existentes (despues de linea 23):

```python
from .routes.tickets import router as tickets_router
```

Agregar junto a los `include_router` existentes (despues de linea 92):

```python
app.include_router(tickets_router)
```

### Frontend — Tickets

#### Paso 4.4 — Ampliar `dashboard/lib/types.ts`

Agregar al final del archivo existente (despues de linea ~133):

```typescript
// ── Tickets ─────────────────────────

export type TicketStatus =
  | 'backlog'
  | 'todo'
  | 'in_progress'
  | 'done'
  | 'blocked'
  | 'cancelled'

export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Ticket {
  id: string
  org_id: string
  title: string
  description: string | null
  flow_type: string | null
  priority: TicketPriority
  status: TicketStatus
  input_data: Record<string, unknown> | null
  task_id: string | null
  created_by: string | null
  assigned_to: string | null
  notes: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export interface TicketCreate {
  title: string
  description?: string
  flow_type?: string
  priority?: TicketPriority
  input_data?: Record<string, unknown>
  assigned_to?: string
}

export interface TicketUpdate {
  status?: TicketStatus
  notes?: string
  assigned_to?: string
}
```

#### Paso 4.5 — Actualizar `StatusLabel` para tickets

El componente `StatusLabel` (`dashboard/components/shared/StatusLabel.tsx`) actualmente maneja `TaskStatus`. Hay que agregar soporte para `TicketStatus`.

**Opcion A (recomendada):** Extender el componente existente para que acepte ambos tipos de status.

**Opcion B:** Crear `TicketStatusLabel` separado.

Usar **Opcion A** — modificar `StatusLabel.tsx` para que el mapa de labels incluya:

```typescript
// Agregar al mapping existente:
'backlog': { label: 'Backlog', variant: 'secondary' as const },
'todo': { label: 'Todo', variant: 'outline' as const },
'in_progress': { label: 'En progreso', variant: 'default' as const },
'done': { label: 'Hecho', variant: 'success' as const },
'blocked': { label: 'Bloqueado', variant: 'destructive' as const },
'cancelled': { label: 'Cancelado', variant: 'secondary' as const },
```

#### Paso 4.6 — `dashboard/hooks/useTickets.ts` (CREAR)

```typescript
'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Ticket, TicketCreate, TicketUpdate } from '@/lib/types'

export function useTickets(
  orgId: string,
  filters?: { status?: string; flow_type?: string; priority?: string }
) {
  return useQuery<{ items: Ticket[]; total: number }>({
    queryKey: ['tickets', orgId, filters],
    queryFn: () => {
      const params = new URLSearchParams()
      if (filters?.status) params.set('status', filters.status)
      if (filters?.flow_type) params.set('flow_type', filters.flow_type)
      if (filters?.priority) params.set('priority', filters.priority)
      const qs = params.toString()
      return api.get(`/tickets${qs ? `?${qs}` : ''}`)
    },
    enabled: !!orgId,
    refetchInterval: 10_000,
    staleTime: 5_000,
  })
}

export function useTicket(orgId: string, ticketId: string) {
  return useQuery<Ticket>({
    queryKey: ['ticket', orgId, ticketId],
    queryFn: () => api.get(`/tickets/${ticketId}`),
    enabled: !!orgId && !!ticketId,
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: TicketCreate) => api.post('/tickets', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}

export function useUpdateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ticketId, body }: { ticketId: string; body: TicketUpdate }) =>
      api.patch(`/tickets/${ticketId}`, body),
    onSuccess: (_data, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}

export function useExecuteTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ticketId: string) => api.post(`/tickets/${ticketId}/execute`),
    onSuccess: (_data, ticketId) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}
```

#### Paso 4.7 — `dashboard/components/tickets/CreateTicketForm.tsx` (CREAR)

```typescript
'use client'

import { useState } from 'react'
import { useCreateTicket } from '@/hooks/useTickets'
import { useFlows } from '@/hooks/useFlows'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { TicketPriority } from '@/lib/types'

interface CreateTicketFormProps {
  onSuccess: () => void
}

export function CreateTicketForm({ onSuccess }: CreateTicketFormProps) {
  const { data: flows, isLoading: loadingFlows } = useFlows()
  const createTicket = useCreateTicket()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [flowType, setFlowType] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('medium')
  const [inputJson, setInputJson] = useState('{}')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!title.trim()) {
      setError('El titulo es obligatorio')
      return
    }

    let inputData: Record<string, unknown> | undefined
    if (inputJson.trim() && inputJson !== '{}') {
      try {
        inputData = JSON.parse(inputJson)
      } catch {
        setError('El JSON de parametros no es valido')
        return
      }
    }

    try {
      await createTicket.mutateAsync({
        title,
        description: description || undefined,
        flow_type: flowType || undefined,
        priority,
        input_data: inputData,
      })
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear ticket')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="ticket-title">Titulo *</Label>
        <Input
          id="ticket-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Descripcion breve de la solicitud"
        />
      </div>

      <div>
        <Label htmlFor="ticket-description">Descripcion</Label>
        <Textarea
          id="ticket-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Detalles adicionales..."
          rows={2}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="ticket-flow">Flow</Label>
          <Select value={flowType} onValueChange={setFlowType}>
            <SelectTrigger id="ticket-flow">
              <SelectValue placeholder="Seleccionar Flow" />
            </SelectTrigger>
            <SelectContent>
              {loadingFlows ? (
                <SelectItem value="__loading__" disabled>Cargando...</SelectItem>
              ) : (
                flows?.map((f) => (
                  <SelectItem key={f.flow_type} value={f.flow_type}>
                    {f.name || f.flow_type}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="ticket-priority">Prioridad</Label>
          <Select value={priority} onValueChange={(v) => setPriority(v as TicketPriority)}>
            <SelectTrigger id="ticket-priority">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Baja</SelectItem>
              <SelectItem value="medium">Media</SelectItem>
              <SelectItem value="high">Alta</SelectItem>
              <SelectItem value="urgent">Urgente</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label htmlFor="ticket-inputs">Parametros (JSON)</Label>
        <Textarea
          id="ticket-inputs"
          value={inputJson}
          onChange={(e) => setInputJson(e.target.value)}
          placeholder='{"clave": "valor"}'
          rows={4}
          className="font-mono text-sm"
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => onSuccess()}>
          Cancelar
        </Button>
        <Button type="submit" disabled={createTicket.isPending}>
          {createTicket.isPending ? 'Creando...' : 'Crear Ticket'}
        </Button>
      </div>
    </form>
  )
}
```

#### Paso 4.8 — `dashboard/app/(app)/tickets/page.tsx` (CREAR)

```typescript
'use client'

import { useState } from 'react'
import { useTickets, useExecuteTicket } from '@/hooks/useTickets'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { PageHeader } from '@/components/shared/PageHeader'
import { DataTable } from '@/components/data-table'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Play } from 'lucide-react'
import { ColumnDef } from '@tanstack/react-table'
import type { Ticket } from '@/lib/types'
import { CreateTicketForm } from '@/components/tickets/CreateTicketForm'
import Link from 'next/link'

const PRIORITY_BADGES: Record<string, string> = {
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  medium: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  urgent: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
}

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  urgent: 'Urgente',
}

export default function TicketsPage() {
  const { orgId } = useCurrentOrg()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [dialogOpen, setDialogOpen] = useState(false)

  const { data: ticketsData, isLoading } = useTickets(orgId, {
    status: statusFilter || undefined,
  })
  const executeTicket = useExecuteTicket()

  const columns: ColumnDef<Ticket>[] = [
    {
      accessorKey: 'title',
      header: 'Titulo',
      cell: ({ row }) => (
        <Link
          href={`/tickets/${row.getValue('id')}`}
          className="font-medium text-primary hover:underline"
        >
          {row.getValue('title')}
        </Link>
      ),
    },
    {
      accessorKey: 'flow_type',
      header: 'Flow',
      cell: ({ row }) => (row.getValue('flow_type') as string) || '—',
    },
    {
      accessorKey: 'priority',
      header: 'Prioridad',
      cell: ({ row }) => {
        const p = row.getValue('priority') as string
        return (
          <Badge className={PRIORITY_BADGES[p]}>
            {PRIORITY_LABELS[p] || p}
          </Badge>
        )
      },
    },
    {
      accessorKey: 'status',
      header: 'Estado',
      cell: ({ row }) => <StatusLabel status={row.getValue('status')} />,
    },
    {
      accessorKey: 'task_id',
      header: 'Task',
      cell: ({ row }) => {
        const taskId = row.getValue('task_id') as string | null
        return taskId ? (
          <Link
            href={`/tasks/${taskId}`}
            className="font-mono text-xs text-muted-foreground hover:underline"
          >
            {taskId.slice(0, 8)}...
          </Link>
        ) : (
          '—'
        )
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const ticket = row.original
        const canExecute =
          ticket.status !== 'in_progress' &&
          ticket.status !== 'done' &&
          ticket.status !== 'cancelled' &&
          !!ticket.flow_type

        if (!canExecute) return null

        return (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => executeTicket.mutate(ticket.id)}
            disabled={executeTicket.isPending}
          >
            <Play className="h-4 w-4" />
          </Button>
        )
      },
    },
  ]

  return (
    <>
      <PageHeader
        title="Tickets"
        description="Solicitudes de trabajo para los agentes"
        action={
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Ticket
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Crear Ticket</DialogTitle>
              </DialogHeader>
              <CreateTicketForm onSuccess={() => setDialogOpen(false)} />
            </DialogContent>
          </Dialog>
        }
      />

      <div className="mb-4 flex gap-2">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Todos los estados" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Todos</SelectItem>
            <SelectItem value="backlog">Backlog</SelectItem>
            <SelectItem value="todo">Todo</SelectItem>
            <SelectItem value="in_progress">En progreso</SelectItem>
            <SelectItem value="done">Hecho</SelectItem>
            <SelectItem value="blocked">Bloqueado</SelectItem>
            <SelectItem value="cancelled">Cancelado</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        data={ticketsData?.items ?? []}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No hay tickets aun. Crea uno para empezar."
        pageSize={20}
      />
    </>
  )
}
```

#### Paso 4.9 — `dashboard/app/(app)/tickets/[id]/page.tsx` (CREAR)

```typescript
'use client'

import { useParams } from 'next/navigation'
import { useTicket, useExecuteTicket } from '@/hooks/useTickets'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { BackButton } from '@/components/shared/BackButton'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Play } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import Link from 'next/link'

const PRIORITY_BADGES: Record<string, string> = {
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  medium: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  urgent: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
}

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  urgent: 'Urgente',
}

export default function TicketDetailPage() {
  const { id } = useParams() as { id: string }
  const { orgId } = useCurrentOrg()
  const { data: ticket, isLoading } = useTicket(orgId, id)
  const executeTicket = useExecuteTicket()

  if (isLoading) {
    return <p className="py-12 text-center text-muted-foreground">Cargando...</p>
  }
  if (!ticket) {
    return <p className="py-12 text-center text-muted-foreground">Ticket no encontrado</p>
  }

  const canExecute =
    ticket.status !== 'in_progress' &&
    ticket.status !== 'done' &&
    ticket.status !== 'cancelled' &&
    !!ticket.flow_type

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <BackButton href="/tickets" />
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{ticket.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge className={PRIORITY_BADGES[ticket.priority]}>
              {PRIORITY_LABELS[ticket.priority]}
            </Badge>
            <StatusLabel status={ticket.status} />
            {ticket.flow_type && (
              <Badge variant="outline">{ticket.flow_type}</Badge>
            )}
          </div>
        </div>
        {canExecute && (
          <Button
            onClick={() => executeTicket.mutate(ticket!.id)}
            disabled={executeTicket.isPending}
          >
            <Play className="mr-2 h-4 w-4" />
            Ejecutar
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Informacion</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {ticket.description && (
              <div>
                <strong>Descripcion:</strong>
                <p className="text-muted-foreground mt-1">{ticket.description}</p>
              </div>
            )}
            <div>
              <strong>Creado:</strong>{' '}
              {formatDistanceToNow(new Date(ticket.created_at), {
                addSuffix: true,
                locale: es,
              })}
            </div>
            <div>
              <strong>Actualizado:</strong>{' '}
              {formatDistanceToNow(new Date(ticket.updated_at), {
                addSuffix: true,
                locale: es,
              })}
            </div>
            {ticket.resolved_at && (
              <div>
                <strong>Resuelto:</strong>{' '}
                {formatDistanceToNow(new Date(ticket.resolved_at), {
                  addSuffix: true,
                  locale: es,
                })}
              </div>
            )}
            {ticket.task_id && (
              <div>
                <strong>Task:</strong>{' '}
                <Link
                  href={`/tasks/${ticket.task_id}`}
                  className="text-primary hover:underline"
                >
                  {ticket.task_id.slice(0, 12)}...
                </Link>
              </div>
            )}
            {ticket.assigned_to && (
              <div>
                <strong>Asignado a:</strong> {ticket.assigned_to}
              </div>
            )}
            {ticket.notes && (
              <div>
                <strong>Notas:</strong>
                <p className="text-muted-foreground mt-1">{ticket.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {ticket.input_data && Object.keys(ticket.input_data).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Parametros</CardTitle>
            </CardHeader>
            <CardContent>
              <CodeBlock code={ticket.input_data} />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
```

#### Paso 4.10 — Agregar "Tickets" al sidebar

Modificar `dashboard/components/nav-main.tsx` para agregar entrada de navegacion:

```typescript
// Agregar al array de items existentes:
{
  title: 'Tickets',
  url: '/tickets',
  icon: Ticket,  // importar de lucide-react
  isActive: false,
}
```

---

## Entregable 5 — Panel de Agente Completo

### Contexto

La pagina `agents/[id]` ya existe y muestra:
- Role + badge activo/inactivo
- Tokens consumidos (via `useAgentMetrics` → `/flow-metrics/by-agent`)
- SOUL definition
- Config (max_iter, allowed_tools)
- Link placeholder al Vault

Lo que falta:
- Historial de tareas ejecutadas por este agente
- Tabs para organizar la informacion
- Credenciales reales del Vault (nombres de secrets, no valores)
- Metricas mejoradas (no heuristica)

### Problema: `assigned_agent_role` nunca se popula

La columna `assigned_agent_role` existe en `tasks` (migracion 002) pero **ningun flow la escribe**. Para poder filtrar tareas por agente, necesitamos que los flows la populen.

**Solucion:** Modificar `BaseFlow.create_task_record()` para aceptar un `assigned_agent_role` opcional, y que los flows bartenders lo seteen.

### Cambios necesarios

#### Paso 5.1 — `src/flows/base_flow.py`: agregar `assigned_agent_role` al crear task

Modificar `create_task_record()` (despues de linea ~166, en el dict de insert):

```python
# Agregar al dict de insert en create_task_record():
"assigned_agent_role": self.extra_kwargs.get("assigned_agent_role"),
```

Esto permite que cualquier flow pase `assigned_agent_role="A1_requerimientos"` al instanciarse y se persista automaticamente.

#### Paso 5.2 — Flows bartenders: pasar `assigned_agent_role`

En cada metodo de `preventa_flow.py` y `cierre_flow.py`, al llamar al constructor del flow o al crear la task, pasar el agent role.

**Alternativa pragmatic:** Como los bartenders flows son secuenciales (A1→A2→A3→A4), el `assigned_agent_role` cambia durante la ejecucion. La forma mas limpia es emitir un evento por cada step con el agent_role, y agregar una tabla de `task_steps` que vincule (task_id, agent_role, tokens_used).

**Pero eso es scope creep.** La solucion pragmatic para Semana 2 es:

- Usar `assigned_agent_role` = el role del **primer agente** del flow (ya que el flow se identifica con el agente principal)
- O simplemente no filtrar por agente en bartenders (que son multi-agent secuenciales) y reservar el filtro por agente para flows de `BaseCrew` (single-agent)

**Decision:** Para flows creados via `BaseCrew` (que tienen un solo agent_role), `assigned_agent_role` tiene sentido. Para bartenders flows (multi-agent), no se filtra por agente individual — se filtra por flow_type.

Esto significa que el endpoint `/flow-metrics/by-agent` seguira siendo heuristico para bartenders, pero sera preciso para flows de BaseCrew.

#### Paso 5.3 — `src/api/routes/agents.py` (CREAR)

Endpoint para detalle enriquecido de agente.

```python
"""Endpoints para detalle de agentes con metricas."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from ..middleware import require_org_id
from ...db.session import get_tenant_client

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/{agent_id}/detail")
async def get_agent_detail(
    agent_id: str,
    org_id: str = Depends(require_org_id),
):
    """
    Detalle completo de un agente.
    Incluye: datos del catalog, metricas de tokens, tareas recientes,
    y referencias a credenciales en Vault (solo nombres, nunca valores).
    """
    from fastapi import HTTPException

    with get_tenant_client(org_id) as db:
        # Agent data
        agent_result = (
            db.table("agent_catalog")
            .select("*")
            .eq("id", agent_id)
            .eq("org_id", org_id)
            .maybe_single()
            .execute()
        )

    if not agent_result.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_result.data
    agent_role = agent.get("role", "")

    # Tareas donde este agente participo (via assigned_agent_role)
    with get_tenant_client(org_id) as db:
        tasks_result = (
            db.table("tasks")
            .select("id, flow_type, status, tokens_used, created_at, updated_at, error")
            .eq("assigned_agent_role", agent_role)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        # Agregados de tokens para este agente
        tokens_result = (
            db.table("tasks")
            .select("tokens_used")
            .eq("assigned_agent_role", agent_role)
            .execute()
        )

    total_tokens = sum(
        t.get("tokens_used", 0)
        for t in (tokens_result.data or [])
    )

    status_counts = {}
    for t in (tasks_result.data or []):
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Credenciales — solo nombres de secrets asociados a las tools del agente
    secret_refs = []
    allowed_tools = agent.get("allowed_tools") or []
    if allowed_tools:
        try:
            from ...tools.registry import tool_registry
            for tool_name in allowed_tools:
                tool_meta = tool_registry.get(tool_name)
                if tool_meta:
                    # Cada tool puede requerir secretos
                    secret_refs.append({
                        "tool": tool_name,
                        "description": tool_meta.description if hasattr(tool_meta, 'description') else None,
                    })
        except Exception:
            pass  # Si no se puede cargar el registry, continuar sin refs

    return {
        "agent": agent,
        "metrics": {
            "total_tokens": total_tokens,
            "tasks_by_status": status_counts,
            "recent_tasks": tasks_result.data or [],
        },
        "credentials": secret_refs,
    }
```

#### Paso 5.4 — `src/api/main.py`: registrar router

```python
from .routes.agents import router as agents_router
# ...
app.include_router(agents_router)
```

### Frontend — Panel de Agente

#### Paso 5.5 — Ampliar `dashboard/lib/types.ts`

```typescript
// ── Agente detallado con metricas ─────────────────────────

export interface AgentDetail {
  agent: Agent
  metrics: {
    total_tokens: number
    tasks_by_status: Record<string, number>
    recent_tasks: Array<{
      id: string
      flow_type: string
      status: TaskStatus
      tokens_used: number
      created_at: string
      updated_at: string
      error: string | null
    }>
  }
  credentials: Array<{
    tool: string
    description: string | null
  }>
}
```

#### Paso 5.6 — `dashboard/hooks/useAgentDetail.ts` (CREAR)

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AgentDetail } from '@/lib/types'

export function useAgentDetail(orgId: string, agentId: string) {
  return useQuery<AgentDetail>({
    queryKey: ['agent-detail', orgId, agentId],
    queryFn: () => api.get(`/agents/${agentId}/detail`),
    enabled: !!orgId && !!agentId,
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}
```

#### Paso 5.7 — Enriquecer `dashboard/app/(app)/agents/[id]/page.tsx`

La pagina ya existe con SOUL + tokens + config. Se reemplaza por una version con tabs.

```typescript
'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { createClient } from '@/lib/supabase'
import { useAgentDetail } from '@/hooks/useAgentDetail'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { BackButton } from '@/components/shared/BackButton'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Skeleton } from '@/components/ui/skeleton'
import { Bot, Key, Coins, AlertTriangle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import type { Agent } from '@/lib/types'
import Link from 'next/link'

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { orgId } = useCurrentOrg()

  // Agent catalog data (query directa, como ya funciona)
  const { data: agent, isLoading: loadingAgent } = useQuery<Agent | null>({
    queryKey: ['agent', id],
    queryFn: async () => {
      const supabase = createClient()
      const { data } = await supabase
        .from('agent_catalog')
        .select('*')
        .eq('id', id)
        .single()
      return data
    },
    enabled: !!id,
  })

  // Detalle enriquecido con metricas
  const { data: detail, isLoading: loadingDetail } = useAgentDetail(orgId, id || '')

  if (loadingAgent) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (!agent) {
    return (
      <p className="py-12 text-center text-muted-foreground">
        Agente no encontrado
      </p>
    )
  }

  const metrics = detail?.metrics
  const credentials = detail?.credentials || []
  const soul = agent.soul_json || {}

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <BackButton href="/agents" />
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bot className="h-6 w-6" />
            {agent.role}
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={agent.is_active ? 'success' : 'secondary'}>
              {agent.is_active ? 'Activo' : 'Inactivo'}
            </Badge>
            {agent.model && (
              <Badge variant="outline">{agent.model}</Badge>
            )}
          </div>
        </div>
      </div>

      {/* Metricas rapidas */}
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Tokens totales"
          value={
            loadingDetail
              ? '...'
              : (metrics?.total_tokens ?? agentTokenUsageFromFallback(agent, orgId)).toLocaleString()
          }
          icon={<Coins className="h-4 w-4" />}
        />
        <MetricCard
          label="Tareas completadas"
          value={metrics?.tasks_by_status.completed ?? '—'}
        />
        <MetricCard
          label="Tareas fallidas"
          value={metrics?.tasks_by_status.failed ?? '—'}
          icon={
            (metrics?.tasks_by_status.failed ?? 0) > 0
              ? <AlertTriangle className="h-4 w-4 text-destructive" />
              : undefined
          }
        />
        <MetricCard
          label="Max iteraciones"
          value={agent.max_iter}
        />
      </div>

      <Tabs defaultValue="info">
        <TabsList>
          <TabsTrigger value="info">Informacion</TabsTrigger>
          <TabsTrigger value="tasks">
            Tareas {metrics?.recent_tasks.length ? `(${metrics.recent_tasks.length})` : ''}
          </TabsTrigger>
          <TabsTrigger value="credentials">
            Credenciales ({credentials.length})
          </TabsTrigger>
        </TabsList>

        {/* Tab: Informacion */}
        <TabsContent value="info" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Configuracion</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div><strong>Role:</strong> {agent.role}</div>
              <div><strong>Modelo:</strong> {agent.model || '—'}</div>
              <div><strong>Max iteraciones:</strong> {agent.max_iter}</div>
              <div>
                <strong>Herramientas:</strong>{' '}
                {(agent.allowed_tools || []).join(', ') || '—'}
              </div>
            </CardContent>
          </Card>

          <Accordion type="single" collapsible>
            <AccordionItem value="soul">
              <AccordionTrigger>SOUL Definition (Prompt)</AccordionTrigger>
              <AccordionContent>
                <CodeBlock code={soul} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </TabsContent>

        {/* Tab: Tareas */}
        <TabsContent value="tasks">
          <Card>
            <CardHeader>
              <CardTitle>Tareas Recientes</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingDetail ? (
                <p className="text-sm text-muted-foreground">Cargando...</p>
              ) : !metrics?.recent_tasks.length ? (
                <p className="text-sm text-muted-foreground">
                  Sin tareas para este agente.
                </p>
              ) : (
                <div className="space-y-2">
                  {metrics.recent_tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between rounded border px-3 py-2 text-sm"
                    >
                      <div className="flex items-center gap-3">
                        <Link
                          href={`/tasks/${task.id}`}
                          className="font-mono text-primary hover:underline"
                        >
                          {task.id.slice(0, 8)}...
                        </Link>
                        <Badge variant="outline">{task.flow_type}</Badge>
                        <span>{task.tokens_used.toLocaleString()} tokens</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusLabel status={task.status} />
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(task.created_at), {
                            addSuffix: true,
                            locale: es,
                          })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Credenciales */}
        <TabsContent value="credentials">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Key className="h-4 w-4" />
                Credenciales en Vault
              </CardTitle>
            </CardHeader>
            <CardContent>
              {credentials.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Sin credenciales asociadas.
                </p>
              ) : (
                <div className="space-y-2">
                  {credentials.map((cred, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 rounded border px-3 py-2 text-sm"
                    >
                      <Key className="h-4 w-4 text-muted-foreground" />
                      <span className="font-mono">{cred.tool}</span>
                      {cred.description && (
                        <span className="text-xs text-muted-foreground">
                          — {cred.description}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-3">
                Solo se muestran los nombres de las herramientas que requieren credenciales.
                Los valores nunca se exponen.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string
  value: string | number
  icon?: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}

// Fallback: usar useAgentMetrics si el endpoint de detail no carga
function agentTokenUsageFromFallback(_agent: Agent, _orgId: string): number {
  // Este fallback se usa solo durante loading
  return 0
}
```

#### Paso 5.8 — Actualizar `dashboard/app/(app)/agents/page.tsx`

La pagina ya funciona correctamente. **No modificar.** Solo se modifica si se quiere agregar metricas de tokens en las cards del grid, pero eso es opcional.

---

## Entregable 6 — Run Transcript

### Contexto

Cuando un Flow se ejecuta, los eventos se guardan en `domain_events`. Pero no hay forma de:
- Ver todos los eventos de una ejecucion especifica
- Observar eventos en tiempo real mientras el flow corre
- Entender que paso paso a paso en un flow fallido

### Arquitectura

```
Flow ejecutandose
  → EventStore.append() / append_sync() → domain_events (INSERT)
                                              ↓
                            Supabase Realtime channel
                            filter: aggregate_id = task_id
                                              ↓
                Frontend subscribe → renderiza eventos en vivo
```

### Cambios necesarios

#### Paso 6.1 — `src/api/routes/transcripts.py` (CREAR)

```python
"""Transcripts de ejecucion de Flows."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Query

from ..middleware import require_org_id
from ...db.session import get_tenant_client

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/{task_id}")
async def get_flow_transcript(
    task_id: str,
    org_id: str = Depends(require_org_id),
    limit: int = Query(200, ge=1, le=1000),
):
    """
    Transcript historico de un Flow run.
    Retorna eventos de dominio filtrados por aggregate_id = task_id.

    NUNCA incluye valores de secretos — los payloads ya estan en DB
    sin secretos (la redaccion se hace al almacenar, no al leer).
    """
    # Verificar que la task existe y pertenece al org
    with get_tenant_client(org_id) as db:
        task_result = (
            db.table("tasks")
            .select("id, flow_type, status")
            .eq("id", task_id)
            .maybe_single()
            .execute()
        )

    if not task_result.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_result.data

    # Obtener eventos del Flow run
    with get_tenant_client(org_id) as db:
        events_result = (
            db.table("domain_events")
            .select("id, event_type, aggregate_type, aggregate_id, payload, sequence, created_at")
            .eq("aggregate_id", task_id)
            .order("sequence", desc=False)
            .limit(limit)
            .execute()
        )

    events = []
    for evt in (events_result.data or []):
        events.append({
            "id": evt.get("id"),
            "event_type": evt.get("event_type"),
            "aggregate_type": evt.get("aggregate_type"),
            "aggregate_id": evt.get("aggregate_id"),
            "payload": evt.get("payload"),
            "sequence": evt.get("sequence"),
            "created_at": evt.get("created_at"),
        })

    return {
        "task_id": task_id,
        "flow_type": task.get("flow_type"),
        "status": task.get("status"),
        "events": events,
    }
```

#### Paso 6.2 — `src/api/main.py`: registrar router

```python
from .routes.transcripts import router as transcripts_router
# ...
app.include_router(transcripts_router)
```

### Frontend — Run Transcript

#### Paso 6.3 — Verificar Supabase Realtime esta habilitado

En Supabase Dashboard → Database → Replication → asegurarse de que:
- La tabla `domain_events` tiene **Realtime enabled**
- El stream incluye `INSERT` events

Si no esta habilitado, ejecutar:

```sql
-- En Supabase SQL editor
ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
```

#### Paso 6.4 — `dashboard/hooks/useFlowTranscript.ts` (CREAR)

```typescript
'use client'

import { useEffect, useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { createClient } from '@/lib/supabase/client'
import type { DomainEvent } from '@/lib/types'

interface TranscriptEvent extends DomainEvent {
  sequence: number
}

export function useFlowTranscript(orgId: string, taskId: string) {
  const [liveEvents, setLiveEvents] = useState<TranscriptEvent[]>([])
  const [isLive, setIsLive] = useState(false)

  // Historico desde API
  const { data: historicalData, isLoading } = useQuery<{
    task_id: string
    flow_type: string
    status: string
    events: TranscriptEvent[]
  }>({
    queryKey: ['transcript', orgId, taskId],
    queryFn: () => api.get(`/transcripts/${taskId}`),
    enabled: !!orgId && !!taskId,
  })

  // Realtime subscription
  useEffect(() => {
    if (!orgId || !taskId) return

    const supabase = createClient()
    const channel = supabase.channel(`transcript:${taskId}`)

    channel
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'domain_events',
          filter: `aggregate_id=eq.${taskId}`,
        },
        (payload) => {
          const newEvent = payload.new as TranscriptEvent
          setLiveEvents((prev) => {
            // Evitar duplicados
            if (prev.some((e) => e.id === newEvent.id)) return prev
            return [...prev, newEvent]
          })
          setIsLive(true)
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          setIsLive(true)
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          setIsLive(false)
        }
      })

    return () => {
      supabase.removeChannel(channel)
      setIsLive(false)
    }
  }, [orgId, taskId])

  // Combinar historico + live
  const allEvents = [...(historicalData?.events ?? []), ...liveEvents]

  // Deduplicar por id
  const seen = new Set<string>()
  const uniqueEvents = allEvents.filter((e) => {
    if (seen.has(e.id)) return false
    seen.add(e.id)
    return true
  })

  // Ordenar por sequence
  uniqueEvents.sort((a, b) => (a.sequence || 0) - (b.sequence || 0))

  return {
    events: uniqueEvents,
    flowType: historicalData?.flow_type,
    status: historicalData?.status,
    isLoading,
    isLive,
  }
}
```

#### Paso 6.5 — `dashboard/app/(app)/tasks/[id]/transcript/page.tsx` (CREAR)

```typescript
'use client'

import { useParams } from 'next/navigation'
import { useFlowTranscript } from '@/hooks/useFlowTranscript'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { BackButton } from '@/components/shared/BackButton'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, Radio, FileText } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

export default function TranscriptPage() {
  const { id } = useParams() as { id: string }
  const { orgId } = useCurrentOrg()
  const { events, flowType, status, isLoading, isLive } = useFlowTranscript(orgId, id)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <BackButton href={`/tasks/${id}`} />
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Transcript
          </h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
            {flowType && <Badge variant="outline">{flowType}</Badge>}
            {status && <StatusLabel status={status} />}
            {isLive && (
              <Badge variant="secondary" className="flex items-center gap-1">
                <Radio className="h-3 w-3 animate-pulse text-green-500" />
                En vivo
              </Badge>
            )}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm">Eventos ({events.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[600px] px-4">
            {isLoading ? (
              <div className="flex items-center gap-2 py-8 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Cargando transcript...
              </div>
            ) : events.length === 0 ? (
              <p className="py-8 text-sm text-muted-foreground">Sin eventos aun.</p>
            ) : (
              <div className="space-y-2 py-2">
                {events.map((event, i) => (
                  <TranscriptEvent key={event.id} event={event} index={i} />
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}

function TranscriptEvent({
  event,
  index,
}: {
  event: TranscriptEvent
  index: number
}) {
  const time = event.created_at
    ? formatDistanceToNow(new Date(event.created_at), {
        addSuffix: false,
        locale: es,
      })
    : ''

  return (
    <div className="rounded border px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-muted-foreground">
          #{index + 1}
        </span>
        <code className="text-xs bg-muted px-1 py-0.5 rounded">
          {event.event_type}
        </code>
        <span className="text-xs text-muted-foreground ml-auto">{time}</span>
      </div>
      {event.payload && Object.keys(event.payload).length > 0 && (
        <div className="mt-1">
          <CodeBlock code={event.payload} />
        </div>
      )}
    </div>
  )
}

interface TranscriptEvent extends DomainEvent {
  sequence: number
}
```

#### Paso 6.6 — Agregar enlace al transcript en `tasks/[id]/page.tsx`

Modificar la pagina de detalle de tarea existente para agregar un boton "Ver Transcript".

Leer la pagina actual y agregar despues del titulo o en el header:

```typescript
// Importar
import Link from 'next/link'
import { FileText } from 'lucide-react'

// Agregar junto al titulo o en un action slot:
<Link
  href={`/tasks/${id}/transcript`}
  className="text-sm text-primary hover:underline flex items-center gap-1"
>
  <FileText className="h-4 w-4" />
  Ver Transcript
</Link>
```

#### Paso 6.7 — Agregar Realtime a `domain_events` en Supabase

Ejecutar en Supabase SQL editor:

```sql
-- Habilitar Realtime para domain_events
ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
```

---

## Resumen completo de archivos

### Backend — 5 archivos

| Archivo | Accion | Descripcion |
|---------|--------|-------------|
| `supabase/migrations/019_tickets.sql` | **CREAR** | Tabla `tickets` con RLS, indices, trigger |
| `src/api/routes/tickets.py` | **CREAR** | CRUD + execute |
| `src/api/routes/agents.py` | **CREAR** | Detalle de agente con metricas |
| `src/api/routes/transcripts.py` | **CREAR** | Transcript historico de un Flow run |
| `src/api/main.py` | **MODIFICAR** | Registrar 3 routers nuevos |

### Backend — 1 archivo existente a modificar

| Archivo | Accion | Descripcion |
|---------|--------|-------------|
| `src/flows/base_flow.py` | **MODIFICAR** | Agregar `assigned_agent_role` al insert de `create_task_record()` |

### Frontend — 11 archivos

| Archivo | Accion | Descripcion |
|---------|--------|-------------|
| `dashboard/lib/types.ts` | **AMPLIAR** | `Ticket`, `TicketCreate`, `TicketUpdate`, `AgentDetail` |
| `dashboard/components/shared/StatusLabel.tsx` | **MODIFICAR** | Agregar labels para TicketStatus |
| `dashboard/hooks/useTickets.ts` | **CREAR** | Hooks para tickets (list, get, create, update, execute) |
| `dashboard/hooks/useAgentDetail.ts` | **CREAR** | Hook para detalle de agente |
| `dashboard/hooks/useFlowTranscript.ts` | **CREAR** | Hook para transcript historico + realtime |
| `dashboard/components/tickets/CreateTicketForm.tsx` | **CREAR** | Formulario de creacion de tickets |
| `dashboard/app/(app)/tickets/page.tsx` | **CREAR** | Lista de tickets con filtros |
| `dashboard/app/(app)/tickets/[id]/page.tsx` | **CREAR** | Detalle de ticket |
| `dashboard/app/(app)/agents/[id]/page.tsx` | **MODIFICAR** | Panel con tabs (info, tareas, credenciales) |
| `dashboard/app/(app)/tasks/[id]/transcript/page.tsx` | **CREAR** | Transcript en tiempo real |
| `dashboard/app/(app)/tasks/[id]/page.tsx` | **MODIFICAR** | Agregar enlace a transcript |
| `dashboard/components/nav-main.tsx` | **MODIFICAR** | Agregar entrada "Tickets" al sidebar |

### Infraestructura

| Componente | Accion |
|------------|--------|
| Supabase Realtime en `domain_events` | Habilitar via SQL |

---

## Dependencias y orden de ejecucion

```
Paso 1: Migracion 019 (tickets) en Supabase
         ↓
Paso 2: Endpoints de tickets (tickets.py)
         ↓
Paso 3: UI de tickets (hooks + componentes + paginas)
         ↓
Paso 4: Sidebar entry para Tickets
         ↓
Paso 5: Endpoint de agents detail (agents.py)
         ↓
Paso 6: Panel de agente con tabs (frontend)
         ↓
Paso 7: Endpoint de transcripts (transcripts.py)
         ↓
Paso 8: Realtime de domain_events en Supabase
         ↓
Paso 9: UI de transcript + hook realtime (frontend)
         ↓
Paso 10: Enlace a transcript en task detail page
```

---

## Validacion al finalizar la Semana 2

| Check | Como validar |
|-------|-------------|
| Tickets CRUD | `POST /tickets` → crear, `GET /tickets` → listar, `PATCH /tickets/{id}` → actualizar |
| Ejecutar ticket | `POST /tickets/{id}/execute` → cambia status, dispara Flow, vincula task_id |
| UI tickets | Navegar a `/tickets` → lista con filtros, boton "Nuevo Ticket" funciona |
| Crear ticket desde UI | Dialog → valida JSON → crea ticket → aparece en lista |
| Detalle ticket | `/tickets/{id}` → muestra info, parametros, boton ejecutar |
| Panel agente tabs | `/agents/{id}` → tabs Info/Tareas/Credenciales visibles |
| Tareas por agente | Tab Tareas muestra tareas filtradas por `assigned_agent_role` |
| Credenciales agente | Tab Credenciales muestra tools del agente con referencias al Vault |
| Transcript historico | `GET /transcripts/{task_id}` → retorna eventos ordenados por sequence |
| Transcript realtime | Ejecutar Flow → navegar a `/tasks/{id}/transcript` → badge "En vivo" activo |
| Eventos aparecen en vivo | Mientras el Flow corre, nuevos eventos se renderizan automaticamente |
| Enlace a transcript | En `/tasks/{id}` hay un link "Ver Transcript" |
| Sidebar entry | "Tickets" visible en el sidebar navegable |
| RLS respeta tenant | Dos orgs ven solo sus datos |
| Auth funciona | Requests sin JWT retornan 401 |
| Sin datos de operatoria | Endpoints NO exponen `payload` ni `result` con secretos |

---

## Lo que NO se toca en Semana 2

- `src/crews/` — codigo protegido de CrewAI
- `src/flows/multi_crew_flow.py` — codigo protegido
- `dashboard/lib/api.ts` — ya tiene auth JWT, no reemplazar
- `supabase/migrations/001-018` — migraciones existentes, no modificar
- `dashboard/app/(app)/agents/page.tsx` — lista de agentes, funciona bien
- `src/api/routes/flows.py` — ya funciona para available + run
- `src/api/routes/flow_metrics.py` — ya funciona, incluyendo `/by-agent`

---

## Notas de diseno

### Tickets vs RunFlowDialog

Son complementarios, no excluyentes:

| | RunFlowDialog | Tickets |
|---|---|---|
| Proposito | Ejecucion inmediata | Solicitud con ciclo de vida |
| Priorizacion | No | Si |
| Asignacion | No | Si |
| Backlog | No | Si |
| Historial | No | Si |
| Vinculacion task | Implicita | Explicita (task_id) |

### assigned_agent_role

La columna ya existe pero nunca se popula. En Semana 2:
- Se agrega al `create_task_record()` de `BaseFlow` como valor opcional via `extra_kwargs`
- Para flows de `BaseCrew` (single-agent), se setea automaticamente con el role del agent
- Para bartenders flows (multi-agent secuencial), no se setea — el filtro por agente no aplica

### `/flow-metrics/by-agent`

Sigue siendo heuristico. Es util para vista general pero NO para datos precisos por agente. El endpoint `/agents/{id}/detail` usa `assigned_agent_role` para datos precisos (donde aplica).

### Transcripts y secretos

Los payloads de `domain_events` **nunca deben contener secretos**. La redaccion se hace **al almacenar** (las tools del Vault nunca exponen valores al LLM ni al payload). El endpoint de transcripts solo retorna lo que ya esta en DB.

### Supabase Realtime

Requiere que la tabla `domain_events` este publicada en `supabase_realtime`. Si no lo esta, el hook de transcript funciona pero sin parte en vivo — muestra solo historico.

---

---

## Plan de Acción Inmediato (Pipeline de Calidad)

| Acción | Responsable | Estado |
|--------|-------------|--------|
| **Backend Integration** | Agentic Backend | ⏳ Pendiente |
| **Frontend UI/UX** | UI Designer Agent | ⏳ Pendiente |
| **Validación MVP** | QA Reviewer | ⏳ Pendiente |

### Pasos Críticos:
1. **Infraestructura:** Ejecutar migración `019_tickets.sql`.
2. **API:** Implementar routers de `tickets`, `agents` y `transcripts`.
3. **Puliendo la UX:** Integrar Realtime en Transcripts y Tabs en el Panel de Agente.

---

> [!IMPORTANT]
> **Definición de Cerrado (Fase 8 Baseline):**
> Se declara que el desarrollo técnico hasta este momento (Token Tracking, FlowRegistry, PersistentState, Metrics API) es el **Core Estable**. El equipo se enfoca exclusivamente en los 3 entregables del MVP para asegurar una salida a producción impecable.

## Deuda técnica conocida (no bloqueante)

| Deuda | Impacto | Cuando resolver |
|-------|---------|----------------|
| `/flow-metrics/by-agent` es heurístico para bartenders | Tokens por agente son aproximación | Post-MVP |
| `assigned_agent_role` no se popula en bartenders | No hay filtro por agente en multi-flow | Post-MVP |
| Paginación en Transcripts | Carga pesada en flows de 1000+ eventos | Post-MVP |

