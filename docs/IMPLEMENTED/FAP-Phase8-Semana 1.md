# FAP v2 — Semana 1: Definicion de Desarrollo (v3 — verificada contra el codigo)

> **Restricciones absolutas:**
> 1. Supabase almacena **solo datos del sistema agentino** — nunca datos de la operatoria
> 2. **Nunca modificar archivos de CrewAI** (`src/crews/`, `src/flows/multi_crew_flow.py`)
> 3. Token tracking se implementa en la capa FAP (BaseFlowState/EventStore), no en CrewAI
> 4. El `api.ts` existente tiene auth JWT — no reemplazar

---

## Estado real del codigo (verificado 2026-04-05)

### Lo que YA existe y NO hay que crear

| Archivo | Que tiene |
|---------|-----------|
| `dashboard/app/(app)/page.tsx` | Overview con `SectionCards` (5 metric cards via `useTasks()` + `useApprovals()`) + tabla de tareas recientes |
| `dashboard/app/(app)/workflows/page.tsx` | Lista de `WorkflowTemplate` desde `GET /workflows`, filtros por status, cards con link a detalle |
| `dashboard/lib/api.ts` | `fapFetch()` con `Authorization: Bearer` + `X-Org-ID`. Exporta `api.get/post/put/delete` |
| `dashboard/lib/types.ts` | `Task`, `TaskStatus`, `PaginatedTasks`, `Approval`, `DomainEvent`, `Organization`, `OrgMember`, `WorkflowTemplate`, `Agent` |
| `dashboard/components/section-cards.tsx` | 5 cards (Total, Completadas, Ejecutando, Errores, HITL) calculadas **client-side** desde `useTasks()` + `useApprovals()` |
| `src/api/routes/workflows.py` | CRUD de `workflow_templates` en prefix `/workflows` — **ya registrado en `main.py:82`** |
| `src/flows/state.py:48` | `tokens_used: int = Field(default=0, ge=0)` — el campo existe |
| `supabase/migrations/002_governance.sql:28` | `ADD COLUMN IF NOT EXISTS tokens_used INTEGER DEFAULT 0` en `tasks` |
| `supabase/migrations/002_governance.sql:20` | `ADD COLUMN IF NOT EXISTS flow_id TEXT` en `tasks` |
| `supabase/migrations/002_governance.sql:50-62` | Tabla `pending_approvals` con RLS, indices, `expires_at` |
| `supabase/migrations/006_workflow_templates.sql` | Tabla `workflow_templates` |
| `src/api/main.py:78-83` | 6 routers registrados: webhooks, tasks, approvals, chat, **workflows**, bartenders |
| `src/api/middleware.py:103-118` | `require_org_id` como FastAPI Depends |
| `src/db/session.py:174-191` | `get_tenant_client()` context manager con RLS |
| `src/flows/registry.py:85-87` | `flow_registry.list_flows()` retorna lista de flow names |

### Gaps reales (lo que NO existe)

| Gap | Donde esta el problema | Impacto |
|-----|----------------------|---------|
| `tokens_used` nunca se escribe | `base_flow.py:200-212` — `persist_state()` no incluye `tokens_used` en el UPDATE | Columna siempre queda en 0 |
| No hay metodo `update_tokens()` | `state.py` — el campo existe pero sin metodo para acumular | Subclases no pueden reportar tokens |
| No hay evento `flow.tokens_recorded` | `base_flow.py` — solo emite `flow.created/completed/rejected` | EventStore no registra uso de tokens |
| No hay vista `v_flow_metrics` | Ninguna migracion la define | No se pueden consultar metricas agregadas eficientemente |
| No hay endpoint `/metrics` o `/flow-metrics` | `src/api/routes/` — no existe `metrics.py` ni `flow_metrics.py` | Dashboard no tiene fuente server-side de metricas |
| `SectionCards` calcula client-side | `section-cards.tsx` — descarga todos los tasks para contar en JS | Ineficiente, no escala, no incluye tokens |
| No hay hooks `useMetrics` ni `useFlowMetrics` | `dashboard/hooks/` — no existen | Sin fetching de metricas server-side |
| No hay tipos de metricas | `dashboard/lib/types.ts` — faltan `OverviewMetrics`, `FlowTypeMetrics` | Sin tipado para respuestas nuevas |

---

## Alcance Semana 1: tres entregables

```
Entregable 1: Token Tracking (Backend — activar campo existente)
Entregable 2: Endpoint de Metricas (Backend — nuevo)
Entregable 3: Conectar Frontend a Metricas Server-side (enriquecer lo existente)
```

---

## Entregable 1 — Token Tracking en Backend

### Contexto

`tokens_used` ya existe como columna en `tasks` (migracion 002) y como campo en `BaseFlowState` (state.py:48). El problema: `persist_state()` no lo incluye en el UPDATE, asi que siempre queda en 0.

### Cambios necesarios

**Paso 1.1 — `src/flows/state.py`: agregar `update_tokens()`**

Agregar metodo a `BaseFlowState` (despues de linea 49):

```python
def update_tokens(self, tokens: int) -> "BaseFlowState":
    """Acumular tokens usados. Llamar desde _run_crew() de la subclase."""
    self.tokens_used += tokens
    return self
```

**Paso 1.2 — `src/flows/base_flow.py`: dos cambios**

**Cambio A** — En `persist_state()` (linea 200-212), agregar `tokens_used` al dict del UPDATE:

```python
# Agregar esta linea al dict existente:
"tokens_used": self.state.tokens_used,
```

**Cambio B** — En `execute()`, despues de `self.state.complete(result)` (linea 141) y antes de `await self.persist_state()` (linea 147):

```python
if self.state.tokens_used > 0:
    await self.emit_event("flow.tokens_recorded", {
        "tokens_used": self.state.tokens_used,
        "flow_type": self.flow_type,
    })
```

**Paso 1.3 — Migracion `018_flow_metrics_view.sql`: vista de metricas**

> Nota: Hay 17 migraciones existentes (001-017). Esta es la 018.

```sql
-- supabase/migrations/018_flow_metrics_view.sql

-- Indices de soporte
CREATE INDEX IF NOT EXISTS idx_tasks_flow_type ON tasks(org_id, flow_type);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(org_id, created_at DESC);

-- Vista: metricas agregadas por flow_type (solo datos del sistema agentino)
CREATE OR REPLACE VIEW v_flow_metrics AS
SELECT
    org_id,
    flow_type,
    COUNT(*)                                               AS total_runs,
    COUNT(*) FILTER (WHERE status = 'completed')           AS completed,
    COUNT(*) FILTER (WHERE status = 'failed')              AS failed,
    COUNT(*) FILTER (WHERE status = 'running')             AS running,
    COUNT(*) FILTER (WHERE status = 'awaiting_approval')   AS awaiting_approval,
    COUNT(*) FILTER (WHERE status = 'pending')             AS pending,
    COALESCE(SUM(tokens_used), 0)                          AS total_tokens,
    COALESCE(AVG(tokens_used) FILTER (WHERE tokens_used > 0), 0)::INTEGER AS avg_tokens,
    MAX(updated_at)                                        AS last_run_at
FROM tasks
GROUP BY org_id, flow_type;

-- La vista hereda RLS de tasks (SECURITY INVOKER por defecto en PostgreSQL)
```

**Paso 1.4 — Contrato para subclases (patron, no archivo a modificar)**

Las subclases de BaseFlow deben llamar a `self.state.update_tokens(n)` dentro de `_run_crew()`:

```python
# En una subclase concreta — ejemplo
async def _run_crew(self) -> Dict[str, Any]:
    crew = create_mi_crew(...)
    result = crew.kickoff(inputs=self.state.input_data)

    # Reportar tokens SIN tocar CrewAI — solo lee lo que ya devuelve
    if hasattr(result, 'usage_metrics') and result.usage_metrics:
        tokens = result.usage_metrics.get('total_tokens', 0)
        self.state.update_tokens(tokens)

    return {"output": str(result)}
```

### Archivos a tocar

| Archivo | Accion |
|---------|--------|
| `src/flows/state.py` | MODIFICAR — agregar `update_tokens()` |
| `src/flows/base_flow.py` | MODIFICAR — 2 cambios: `persist_state()` + `execute()` |
| `supabase/migrations/018_flow_metrics_view.sql` | CREAR — indices + vista |

---

## Entregable 2 — Endpoint de Metricas (Backend)

### Contexto

El dashboard necesita metricas agregadas del servidor. Hoy `SectionCards` las calcula client-side descargando todos los tasks. Se crea un unico archivo `flow_metrics.py` con dos endpoints.

> **Naming:** Se usa prefix `/flow-metrics` para no colisionar con `/workflows` existente (templates CRUD).

### Cambios necesarios

**Paso 2.1 — `src/api/routes/flow_metrics.py` (CREAR)**

```python
"""Metricas del sistema agentino para el dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from ..middleware import require_org_id
from ...db.session import get_tenant_client

router = APIRouter(prefix="/flow-metrics", tags=["flow-metrics"])


@router.get("")
async def get_overview_metrics(org_id: str = Depends(require_org_id)):
    """
    Metricas globales para el Overview (SectionCards).

    Retorna SOLO datos del sistema agentino:
    - Conteos de tasks por status
    - Total de tokens consumidos
    - Aprobaciones pendientes
    - Ultimos 10 eventos

    NUNCA retorna payload ni result (datos de operatoria).
    """
    with get_tenant_client(org_id) as db:
        tasks_result = db.table("tasks").select(
            "status, tokens_used"
        ).execute()

        approvals_result = db.table("pending_approvals").select(
            "id", count="exact"
        ).eq("status", "pending").execute()

        events_result = db.table("domain_events").select(
            "event_type, aggregate_type, aggregate_id, created_at, payload"
        ).order("created_at", desc=True).limit(10).execute()

    status_counts: dict = {}
    total_tokens = 0
    for row in (tasks_result.data or []):
        s = row.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
        total_tokens += row.get("tokens_used", 0) or 0

    return {
        "tasks": {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
        },
        "tokens": {
            "total": total_tokens,
        },
        "approvals": {
            "pending": approvals_result.count or 0,
        },
        "events": {
            "recent": events_result.data or [],
        },
    }


@router.get("/by-type")
async def get_metrics_by_flow_type(org_id: str = Depends(require_org_id)):
    """
    Metricas por flow_type (usa vista v_flow_metrics).
    Para enriquecer Overview con seccion de flows activos.
    """
    with get_tenant_client(org_id) as db:
        result = db.table("v_flow_metrics").select("*").execute()

    return result.data or []


@router.get("/by-type/{flow_type}/runs")
async def get_flow_runs(
    flow_type: str,
    org_id: str = Depends(require_org_id),
    limit: int = 20,
    offset: int = 0,
):
    """
    Historial de ejecuciones de un flow type.
    Solo datos del sistema agentino — NO incluye payload ni result.
    """
    with get_tenant_client(org_id) as db:
        result = (
            db.table("tasks")
            .select(
                "id, flow_type, status, tokens_used, "
                "created_at, updated_at, error, correlation_id"
            )
            .eq("flow_type", flow_type)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    return result.data or []
```

**Paso 2.2 — `src/api/main.py`: registrar router**

Agregar junto a los imports existentes:

```python
from .routes.flow_metrics import router as flow_metrics_router
```

Agregar junto a los `include_router` existentes (linea 83):

```python
app.include_router(flow_metrics_router)
```

> **NO tocar `workflows_router`** — ya existe y funciona para `workflow_templates`.

### Archivos a tocar

| Archivo | Accion |
|---------|--------|
| `src/api/routes/flow_metrics.py` | CREAR |
| `src/api/main.py` | MODIFICAR — agregar 1 router |

---

## Entregable 3 — Conectar Frontend a Metricas Server-side

### Contexto

Las paginas ya existen y funcionan. `workflows/page.tsx` ya consume `GET /workflows` que ya existe en el backend. El trabajo es:
1. Crear hooks para consumir el nuevo endpoint `/flow-metrics`
2. Migrar `SectionCards` de calculo client-side a datos del servidor + agregar card de Tokens
3. Agregar secciones de flows activos y activity feed al Overview
4. Ampliar tipos TypeScript

### Cambios necesarios

**Paso 3.1 — Ampliar `dashboard/lib/types.ts`**

Agregar al final del archivo existente (despues de linea 97):

```typescript
// ── Metricas del sistema agentino ─────────────────────────

export interface OverviewMetrics {
  tasks: {
    total: number
    by_status: Record<string, number>
  }
  tokens: {
    total: number
  }
  approvals: {
    pending: number
  }
  events: {
    recent: DomainEvent[]
  }
}

export interface FlowTypeMetrics {
  flow_type: string
  total_runs: number
  completed: number
  failed: number
  running: number
  awaiting_approval: number
  pending: number
  total_tokens: number
  avg_tokens: number
  last_run_at: string | null
}

export interface FlowRun {
  id: string
  flow_type: string
  status: TaskStatus
  tokens_used: number
  created_at: string
  updated_at: string
  error: string | null
  correlation_id: string | null
}
```

**Paso 3.2 — `dashboard/hooks/useMetrics.ts` (CREAR)**

Usa `api.get()` existente (ya incluye JWT + X-Org-ID):

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { OverviewMetrics } from '@/lib/types'

export function useMetrics(orgId: string) {
  return useQuery<OverviewMetrics>({
    queryKey: ['metrics', orgId],
    queryFn: () => api.get('/flow-metrics'),
    enabled: !!orgId,
    refetchInterval: 10_000,
    staleTime: 5_000,
  })
}
```

**Paso 3.3 — `dashboard/hooks/useFlowMetrics.ts` (CREAR)**

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { FlowTypeMetrics, FlowRun } from '@/lib/types'

export function useFlowMetrics(orgId: string) {
  return useQuery<FlowTypeMetrics[]>({
    queryKey: ['flow-metrics-by-type', orgId],
    queryFn: () => api.get('/flow-metrics/by-type'),
    enabled: !!orgId,
    refetchInterval: 10_000,
    staleTime: 5_000,
  })
}

export function useFlowRuns(orgId: string, flowType: string) {
  return useQuery<FlowRun[]>({
    queryKey: ['flow-runs', orgId, flowType],
    queryFn: () => api.get(`/flow-metrics/by-type/${flowType}/runs`),
    enabled: !!orgId && !!flowType,
    staleTime: 5_000,
  })
}
```

**Paso 3.4 — Migrar `dashboard/components/section-cards.tsx`**

Estado actual: usa `useTasks()` (descarga todos los tasks) + `useApprovals()` para calcular conteos en JS. Tiene 5 cards.

Migrar a: usar `useMetrics()` que trae datos ya agregados del servidor. Agregar 6ta card de Tokens.

```typescript
'use client'

import { useMetrics } from '@/hooks/useMetrics'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { LayoutDashboard, CheckCircle, Clock, AlertTriangle, ShieldCheck, Coins } from 'lucide-react'

export function SectionCards() {
  const { orgId } = useCurrentOrg()
  const { data: metrics, isLoading } = useMetrics(orgId)

  const stats = {
    total: metrics?.tasks.total ?? 0,
    completed: metrics?.tasks.by_status['completed'] ?? 0,
    running: metrics?.tasks.by_status['running'] ?? 0,
    failed: metrics?.tasks.by_status['failed'] ?? 0,
    tokens: metrics?.tokens.total ?? 0,
    pendingApprovals: metrics?.approvals.pending ?? 0,
  }

  const successRate =
    stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
      <MetricCard
        title="Total tareas"
        value={stats.total}
        icon={<LayoutDashboard className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Completadas"
        value={stats.completed}
        subtitle={`${successRate}% exito`}
        icon={<CheckCircle className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Ejecutando"
        value={stats.running}
        icon={<Clock className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Errores"
        value={stats.failed}
        icon={<AlertTriangle className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Tokens totales"
        value={stats.tokens}
        format="number"
        icon={<Coins className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <Card className={stats.pendingApprovals > 0 ? 'border-amber-300 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-900/10' : ''}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">HITL pendientes</CardTitle>
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <div className="text-2xl font-bold">{stats.pendingApprovals}</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  loading,
  format,
}: {
  title: string
  value: number
  subtitle?: string
  icon: React.ReactNode
  loading?: boolean
  format?: 'number'
}) {
  const displayValue = format === 'number' ? value.toLocaleString() : value.toString()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <>
            <div className="text-2xl font-bold">{displayValue}</div>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
```

**Paso 3.5 — Enriquecer `dashboard/app/(app)/page.tsx`**

La pagina ya tiene `SectionCards` + tabla de tareas recientes. Agregar:
- Seccion "Flows Registrados" con `useFlowMetrics()` — muestra cada flow type con conteos y tokens
- Seccion "Actividad Reciente" con los ultimos eventos de `useMetrics()`

```typescript
'use client'

import { SectionCards } from '@/components/section-cards'
import { DataTable } from '@/components/data-table'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { useTasks } from '@/hooks/useTasks'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useMetrics } from '@/hooks/useMetrics'
import { useFlowMetrics } from '@/hooks/useFlowMetrics'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ColumnDef } from '@tanstack/react-table'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import type { Task } from '@/lib/types'
import Link from 'next/link'

const columns: ColumnDef<Task>[] = [
  {
    accessorKey: 'task_id',
    header: 'ID',
    cell: ({ row }) => (
      <Link href={`/tasks/${row.getValue('task_id')}`} className="font-medium text-primary hover:underline">
        {(row.getValue('task_id') as string).slice(0, 12)}...
      </Link>
    ),
  },
  {
    accessorKey: 'flow_type',
    header: 'Flow',
  },
  {
    accessorKey: 'status',
    header: 'Estado',
    cell: ({ row }) => <StatusLabel status={row.getValue('status')} />,
  },
  {
    accessorKey: 'created_at',
    header: 'Creado',
    cell: ({ row }) =>
      formatDistanceToNow(new Date(row.getValue('created_at')), {
        addSuffix: true,
        locale: es,
      }),
  },
]

export default function OverviewPage() {
  const { orgId } = useCurrentOrg()
  const { data: tasksData, isLoading } = useTasks(orgId)
  const { data: metrics, isLoading: loadingMetrics } = useMetrics(orgId)
  const { data: flows, isLoading: loadingFlows } = useFlowMetrics(orgId)
  const tasks = tasksData?.items?.slice(0, 10) || []

  return (
    <>
      <SectionCards />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Flows activos */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Flows Registrados</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingFlows ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : !flows?.length ? (
              <p className="text-sm text-muted-foreground">
                No hay flows registrados aun.
              </p>
            ) : (
              <div className="space-y-2">
                {flows.map((flow) => (
                  <div
                    key={flow.flow_type}
                    className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                  >
                    <div className="flex flex-col">
                      <span className="font-medium">{flow.flow_type}</span>
                      <span className="text-xs text-muted-foreground">
                        {flow.total_runs} ejecuciones · {flow.total_tokens.toLocaleString()} tokens
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {flow.running > 0 && (
                        <Badge variant="secondary">{flow.running} activos</Badge>
                      )}
                      {flow.failed > 0 && (
                        <Badge variant="destructive">{flow.failed} errores</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Activity feed */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Actividad Reciente</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingMetrics ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !metrics?.events.recent.length ? (
              <p className="text-sm text-muted-foreground">
                Sin eventos recientes.
              </p>
            ) : (
              <div className="space-y-1">
                {metrics.events.recent.map((event, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-xs py-1 border-b last:border-0"
                  >
                    <span className="font-mono text-muted-foreground">
                      {event.event_type}
                    </span>
                    <span className="text-muted-foreground">
                      {formatDistanceToNow(new Date(event.created_at), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div>
        <h3 className="mb-4 text-lg font-semibold">Tareas recientes</h3>
        <DataTable
          data={tasks}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No hay tareas aun"
          pageSize={10}
        />
      </div>
    </>
  )
}
```

### Archivos a tocar

| Archivo | Accion |
|---------|--------|
| `dashboard/lib/types.ts` | AMPLIAR — agregar `OverviewMetrics`, `FlowTypeMetrics`, `FlowRun` |
| `dashboard/hooks/useMetrics.ts` | CREAR |
| `dashboard/hooks/useFlowMetrics.ts` | CREAR |
| `dashboard/components/section-cards.tsx` | MODIFICAR — migrar a `useMetrics()` + agregar card Tokens |
| `dashboard/app/(app)/page.tsx` | MODIFICAR — agregar flows activos + activity feed |

---

## Resumen completo de archivos

### Backend — 4 archivos

| Archivo | Accion | Descripcion |
|---------|--------|-------------|
| `supabase/migrations/018_flow_metrics_view.sql` | CREAR | Indices + vista `v_flow_metrics` |
| `src/flows/state.py` | MODIFICAR | Agregar `update_tokens()` |
| `src/flows/base_flow.py` | MODIFICAR | `persist_state()` incluye tokens + `execute()` emite evento |
| `src/api/routes/flow_metrics.py` | CREAR | `GET /flow-metrics` + `/by-type` + `/by-type/{type}/runs` |
| `src/api/main.py` | MODIFICAR | Registrar 1 router nuevo |

### Frontend — 5 archivos

| Archivo | Accion | Descripcion |
|---------|--------|-------------|
| `dashboard/lib/types.ts` | AMPLIAR | `OverviewMetrics`, `FlowTypeMetrics`, `FlowRun` |
| `dashboard/hooks/useMetrics.ts` | CREAR | Consume `GET /flow-metrics` via `api.get()` existente |
| `dashboard/hooks/useFlowMetrics.ts` | CREAR | Consume `GET /flow-metrics/by-type` via `api.get()` existente |
| `dashboard/components/section-cards.tsx` | MODIFICAR | Migrar a server-side + agregar card Tokens (5 → 6 cards) |
| `dashboard/app/(app)/page.tsx` | MODIFICAR | Agregar secciones flows activos + activity feed |

---

## Dependencias y orden de ejecucion

```
Paso 1: Migracion 018 en Supabase
         ↓
Paso 2: state.py + base_flow.py (token tracking)
         ↓
Paso 3: flow_metrics.py + registrar en main.py
         ↓
Paso 4: types.ts + hooks (frontend)
         ↓
Paso 5: section-cards.tsx + page.tsx
```

---

## Validacion al finalizar la Semana 1

| Check | Como validar |
|-------|-------------|
| Tokens se persisten | Ejecutar un Flow → `SELECT tokens_used FROM tasks WHERE id = '{id}'` → valor > 0 |
| Vista funciona | `SELECT * FROM v_flow_metrics` → retorna filas |
| `/flow-metrics` responde | `curl -H "Authorization: Bearer {jwt}" -H "X-Org-ID: {id}" localhost:8000/flow-metrics` |
| `/flow-metrics/by-type` responde | Idem → retorna lista con conteos por flow_type |
| SectionCards 6 cards | Navegar a `/` → 6 cards incluyendo "Tokens totales" |
| Flows activos visible | Navegar a `/` → seccion "Flows Registrados" con datos |
| Activity feed visible | Navegar a `/` → seccion "Actividad Reciente" con eventos |
| Workflows sigue funcionando | Navegar a `/workflows` → lista de templates sin regresion |
| RLS respeta tenant | Con dos orgs, cada una ve solo sus datos |
| Sin datos de operatoria | `/flow-metrics/by-type/{type}/runs` NO retorna `payload` ni `result` |
| Auth funciona | Requests sin JWT retornan 401 |

---

## Lo que NO se toca en Semana 1

- `src/crews/` — codigo protegido de CrewAI
- `src/flows/multi_crew_flow.py` — codigo protegido
- `src/api/routes/workflows.py` — ya funciona para templates, no modificar
- `dashboard/lib/api.ts` — ya tiene auth JWT, no reemplazar
- `dashboard/app/(app)/workflows/page.tsx` — ya consume `GET /workflows` correctamente

---

## Notas

- **`payload` y `result` de tasks nunca se exponen** en endpoints de metricas
- **La vista `v_flow_metrics` solo agrega datos del sistema agentino**
- **Se usa `/flow-metrics`** (no `/flows`) para no colisionar con `/workflows` existente
- **Se reutiliza `api.get()` existente** que ya incluye JWT + X-Org-ID
- **Las rutas del dashboard son `dashboard/app/(app)/`** (sin `src/`, con route group `(app)`)
