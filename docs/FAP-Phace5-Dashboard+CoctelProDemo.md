# Fase 5 — Dashboard + CoctelPro Demo

> **Definición cerrada.** Basada en el backend de Fases 1–4 ya implementado.
> Todo el código propuesto es consistente con los patterns existentes.

---

## Visión del sistema

Las Fases 1–4 construyeron un backend sólido: flows, HITL, vault, guardrails, MDC.
Pero todo eso solo existe como API. Fase 5 agrega la capa visual que convierte
ese backend en algo que podés mostrar, vender y operar.

### Criterio de éxito

Demo completa de CoctelPro corriendo en laptop, con Kanban visible y HITL funcionando de punta a punta.

### Decisión de diseño

El Dashboard es una aplicación Next.js separada que consume la API de FastAPI + Supabase directamente.
No hay lógica de negocio en el frontend — todo el estado canónico sigue viviendo en el backend Python.

---

## 01 — Stack tecnológico

| Tecnología | Uso | Estado |
|---|---|---|
| Next.js 14 (App Router) | Server Components para carga inicial, Client Components para Realtime y acciones | ⭐ NUEVO |
| Supabase JS Client | Auth + Realtime subscriptions + RLS automático por usuario | ⭐ NUEVO |
| TanStack Query v5 | Cache de server state, invalidation por eventos Realtime, optimistic updates | ⭐ NUEVO |
| Tailwind CSS v3 | Estilo utilitario; componentes UI tipo Jira sin librería pesada | ⭐ NUEVO |
| shadcn/ui | Componentes accesibles (Dialog, Table, Badge, Dropdown) sin opinionado visual | ⭐ NUEVO |
| Supabase Auth | Login con email/password o magic link. JWT con rol en claims | ⭐ NUEVO |
| FastAPI (Fases 1–4) | Backend existente. Dashboard lo consume vía fetch desde API routes de Next.js | existente |

### Auth: dos capas

Supabase Auth maneja la sesión del usuario en el Dashboard.
FastAPI verifica el JWT de Supabase en cada request como middleware.
El `org_id` activo viaja como header `X-Org-ID`.
FastAPI valida que ese `org_id` le pertenezca al usuario autenticado antes de pasarlo a `TenantClient`.

---

## 02 — Bloques de la fase

### 5A — Dashboard UI

- Panel general con métricas (Overview)
- Kanban de tareas en tiempo real
- Centro de aprobaciones HITL
- Historial y logs de eventos
- Trigger manual de flows
- Configuración de agentes y workflows

### 5B — CoctelPro Demo

- 4 agentes con SOUL definido (Ventas, Logística, Compras, Finanzas)
- Workflows conectados vía HITL
- Datos de prueba realistas
- Flujos demo ejecutables (cotización, compra)
- Script de demo guiado

### 5C — Memoria vectorial *(opcional para v1 demo)*

- `pgvector` ya tiene tabla (`memory_vectors`, Fase 3)
- Código Python existe en `src/db/memory.py`
- Lo que falta: activarla y exponer búsquedas en Dashboard
- **Diferible** si los flujos demo de CoctelPro no la requieren visiblemente

---

## 03 — Estructura del proyecto Dashboard

```
dashboard/
├── app/
│   ├── layout.tsx                  # Root layout: Auth provider + Query provider
│   ├── (auth)/
│   │   └── login/page.tsx          # Login con Supabase Auth
│   └── (app)/
│       ├── layout.tsx              # Sidebar + header + org selector
│       ├── page.tsx                # Overview / home
│       ├── kanban/page.tsx         # Kanban realtime
│       ├── approvals/page.tsx      # Centro de aprobaciones HITL
│       ├── tasks/
│       │   ├── page.tsx            # Historial paginado
│       │   └── [id]/page.tsx       # Detalle de task + eventos
│       ├── agents/
│       │   ├── page.tsx            # Lista de agentes
│       │   └── [id]/page.tsx       # Detalle/edición de agente
│       ├── workflows/
│       │   ├── page.tsx            # Lista de workflow_templates
│       │   └── [id]/page.tsx       # Detalle/trigger manual
│       ├── events/page.tsx         # Log de domain_events realtime
│       └── architect/page.tsx      # Chat MDC (usa POST /chat/)
│
├── components/
│   ├── kanban/
│   │   ├── KanbanBoard.tsx         # Tablero con columnas
│   │   ├── KanbanColumn.tsx        # Columna individual
│   │   └── TaskCard.tsx            # Card de tarea (normal + aprobación)
│   ├── approvals/
│   │   ├── ApprovalList.tsx        # Lista con badge de pendientes
│   │   └── ApprovalDetail.tsx      # Detalle con botones approve/reject
│   ├── events/
│   │   └── EventTimeline.tsx       # Timeline de domain_events de un task
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── OrgSelector.tsx         # Dropdown org (solo fap_admin)
│   └── ui/                         # shadcn/ui components
│
├── hooks/
│   ├── useRealtimeDashboard.ts     # Suscripciones Realtime (ver sección 06)
│   ├── useTasks.ts                 # TanStack Query para tasks
│   ├── useApprovals.ts             # TanStack Query para approvals
│   └── useCurrentOrg.ts           # org_id activo + cambio de org
│
├── lib/
│   ├── supabase.ts                 # createBrowserClient + createServerClient
│   ├── api.ts                      # fetch wrapper con X-Org-ID header
│   └── types.ts                    # Tipos TS espejando modelos Python
│
└── middleware.ts                   # Proteger rutas auth con Supabase middleware
```

---

## 04 — Vistas del Dashboard

### Overview (home)

- Métricas: tasks hoy / semana
- Tasa de éxito de flows
- Tokens usados vs cuota
- Aprobaciones pendientes (count con badge)
- Últimas 5 tareas (lista rápida)
- Agentes activos

### Kanban de tareas

Columnas: `pending` → `running` → `pending_approval` → `completed` / `failed`

- Cards con flow_type, tiempo transcurrido, agente asignado
- Cards de aprobación destacadas con borde ámbar
- Click en card → panel lateral de detalle
- Actualización en tiempo real sin polling
- Filtro por flow_type y rango de fechas

### Centro de aprobaciones

- Lista de aprobaciones pendientes con badge contador en sidebar
- Detalle completo del payload de la aprobación
- Botones Aprobar / Rechazar con campo de notas opcional
- Historial de decisiones pasadas (quién aprobó/rechazó y cuándo)

### Historial de tareas

- Lista paginada de tasks
- Filtros: status, flow_type, rango de fechas
- Click → timeline de domain_events del flow
- Input/output del flow expandible
- Tokens usados por task

### Agentes y workflows

- Lista de agentes de la org con SOUL/SKILL legible
- Lista de workflow_templates con status: draft / active / archived
- Trigger manual de un workflow con formulario de input_data JSON
- Acceso al chat MDC (Architect)

### Logs de eventos

- Stream de domain_events en tiempo real
- Filtro por task_id o event_type
- Payload expandible por evento
- Útil para debugging durante la demo

---

## 05 — Sistema de roles (Fase 5)

> **Decisión:** Tres roles hardcodeados. La asignación se hace directo en la tabla `org_members`.
> Un sistema de roles configurable desde el Dashboard queda para Fase 6.

| Rol | Scope | Puede |
|---|---|---|
| `fap_admin` | Plataforma global | Ver todas las orgs, cambiar org activa, crear/desactivar orgs, ver métricas globales, gestionar cualquier org |
| `org_owner` | Su org | Ver Kanban, aprobar/rechazar HITL, disparar flows, ver historial y logs, configurar agentes y workflows |
| `org_operator` | Su org (lectura + aprobaciones) | Ver Kanban, aprobar/rechazar HITL, ver historial y logs. No puede disparar flows ni editar agentes |

---

## 06 — Supabase Realtime

El Kanban usa Supabase Realtime (WebSocket) para actualizarse sin polling.
Se suscriben tres canales al montar el componente.

**Requerimiento:** habilitar Realtime para las tablas `tasks`, `pending_approvals` y `domain_events`
desde el panel de Supabase → Database → Replication. Sin esto, las suscripciones no reciben eventos.

```typescript
// hooks/useRealtimeDashboard.ts
import { useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { useQueryClient } from '@tanstack/react-query'

export function useRealtimeDashboard(orgId: string) {
  const queryClient = useQueryClient()

  useEffect(() => {
    const channel = supabase
      .channel(`dashboard-${orgId}`)

      // Kanban: cualquier cambio en tasks de esta org
      .on('postgres_changes', {
        event: '*', schema: 'public', table: 'tasks',
        filter: `org_id=eq.${orgId}`
      }, () => {
        queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })
      })

      // Badge de aprobaciones: inserts/updates en pending_approvals
      .on('postgres_changes', {
        event: '*', schema: 'public', table: 'pending_approvals',
        filter: `org_id=eq.${orgId}`
      }, () => {
        queryClient.invalidateQueries({ queryKey: ['approvals', orgId] })
      })

      // Log de eventos en tiempo real
      .on('postgres_changes', {
        event: 'INSERT', schema: 'public', table: 'domain_events',
        filter: `org_id=eq.${orgId}`
      }, (payload) => {
        queryClient.setQueryData(['events', orgId], (old: any[]) =>
          [payload.new, ...(old ?? [])].slice(0, 200)
        )
      })

      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [orgId, queryClient])
}
```

### Flujo de datos: aprobación HITL en tiempo real

1. Agente ejecuta flow → llama `request_approval()` → lanza `FlowSuspendedException`
2. Backend crea fila en `pending_approvals` con `status="pending"`
3. Supabase Realtime emite evento al Dashboard instantáneamente
4. Dashboard muestra badge rojo en ícono de aprobaciones + card ámbar en Kanban
5. Jefe hace click → aprueba o rechaza
6. Dashboard llama `POST /approvals/{task_id}`
7. Backend restaura snapshot y reanuda el flow
8. Task pasa a `running` → `completed` en tiempo real en el Kanban

---

## 07 — Base de datos — Cambios en Fase 5

### Resumen de migraciones

| Archivo | Qué hace | Estado |
|---|---|---|
| `001_set_config_rpc.sql` | RLS base, set_config(), current_org_id() | Fase 1 ✓ |
| `002_governance.sql` | pending_approvals, secrets, extensiones tasks/snapshots | Fase 2 ✓ |
| `010_org_mcp_servers.sql` | MCP servers por org | Fase 3 ✓ |
| `007_memory_vectors.sql` | pgvector para memoria semántica | Fase 3 ✓ |
| `006_workflow_templates.sql` | Workflows generados por Architect | Fase 4 ✓ |
| `008_org_members.sql` | Miembros por org con roles Dashboard | ⭐ NUEVO Fase 5 |
| Supabase Realtime config | Habilitar replica en tasks, pending_approvals, domain_events | ⭐ Configurar Fase 5 |

### `sql/008_org_members.sql`

```sql
-- Miembros de una org con su rol en el Dashboard.
-- Un usuario puede pertenecer a múltiples orgs con roles distintos.
CREATE TABLE org_members (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL,              -- Supabase Auth uid
  email      TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'org_operator'
               CHECK (role IN ('fap_admin', 'org_owner', 'org_operator')),
  is_active  BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, user_id)
);

ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;

-- Un miembro solo ve su propio registro
CREATE POLICY "own_membership" ON org_members
  FOR SELECT USING (user_id = auth.uid());

-- fap_admin puede ver todos
CREATE POLICY "fap_admin_all" ON org_members
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM org_members m
       WHERE m.user_id = auth.uid() AND m.role = 'fap_admin'
    )
  );
```

### `src/api/middleware/auth.py` — validar org membership

```python
from fastapi import Request, HTTPException
from src.db.session import get_service_client

async def verify_org_access(request: Request) -> str:
    """Verifica que el usuario autenticado tenga acceso al org_id del header."""
    org_id = request.headers.get("X-Org-ID")
    user_id = request.state.user_id  # Del JWT de Supabase

    if not org_id:
        raise HTTPException(status_code=400, detail="X-Org-ID header required")

    # fap_admin puede acceder a cualquier org
    db = get_service_client()
    member = db.table("org_members") \
        .select("role") \
        .eq("org_id", org_id) \
        .eq("user_id", user_id) \
        .eq("is_active", True) \
        .maybe_single().execute()

    if not member.data:
        raise HTTPException(status_code=403, detail="No access to this org")

    request.state.org_role = member.data["role"]
    return org_id
```

---

## 08 — CoctelPro en FAP (Bloque 5B)

CoctelPro es una empresa de servicios de bartending y bebidas para eventos.
Es el cliente demo que vive dentro de FAP como org real, con agentes reales y workflows reales.
El objetivo es demostrar FAP haciendo algo concreto y entendible por cualquier persona.

### Los 4 agentes de CoctelPro

| Agente | Rol | Trigger principal | HITL |
|---|---|---|---|
| Agente Ventas | Atiende consultas, genera cotizaciones | Mensaje de cliente con datos de evento | Descuento >15% o cliente VIP |
| Agente Logística | Calcula insumos, arma checklist de evento | Cotización aprobada | Evento >150 pax o ubicación especial |
| Agente Compras | Genera órdenes de compra | Lista de insumos de Logística | Siempre (nunca compra autónomo) |
| Agente Finanzas | Registra ingresos/egresos, alerta márgenes | Pago confirmado o compra aprobada | Margen <20% o gasto no presupuestado |

### Flujo demo recomendado (12 minutos)

1. **Disparar `cotizacion_flow`** desde el Dashboard con datos de un evento (casamiento 80 pax, $500k)
2. Mostrar el Kanban moviéndose en tiempo real: `pending` → `running`
3. Agente Ventas genera cotización con descuento 18% → aparece card ámbar "Esperando aprobación"
4. Ir al Centro de Aprobaciones → mostrar el detalle completo del payload
5. **Aprobar** la cotización → task pasa a `completed` en tiempo real
6. Disparar `compras_flow` → Agente Compras pide compra $120.000 → HITL
7. **Rechazar** la compra → mostrar que el flow se marca como `rejected`
8. Abrir log de eventos → mostrar el trail completo de decisiones

### Qué hay que definir antes de implementar 5B

**Pendiente de definir:**
- SOUL completo de cada agente (personalidad, reglas rígidas)
- Fórmulas de cálculo de Logística (pax → insumos)
- Umbrales exactos de HITL por agente
- Datos de prueba realistas para la demo

**Ya disponible:**
- Arquitectura de agentes definida (4 roles)
- Infraestructura HITL funcionando (Fase 2)
- ArchitectFlow para generar workflows (Fase 4)
- Tablas SQL listas para insertar datos

---

## 09 — Timeline — 10 semanas

> **Supuesto:** Una persona (vos + IA) trabajando.
> Los bloques 5A y 5B pueden ir en paralelo parcialmente — mientras 5A está en construcción,
> la definición de SOUL de agentes (5B) no requiere código.

### Semanas 1–2: Fundación — Setup + Auth + Layout

- Crear proyecto Next.js 14 con App Router
- Configurar Supabase Auth (email/password)
- Layout base: sidebar, header, OrgSelector
- Middleware de protección de rutas (`middleware.ts`)
- Tabla `org_members` + middleware FastAPI (`verify_org_access`)
- Conectar fetch wrapper con header `X-Org-ID`

### Semanas 3–4: Kanban Realtime

- Habilitar Realtime en Supabase para `tasks`, `pending_approvals`, `domain_events`
- Hook `useRealtimeDashboard`
- `KanbanBoard` con 5 columnas
- `TaskCard` con estado visual (colores por status)
- Card especial para `pending_approval` con borde ámbar
- Panel lateral de detalle al hacer click en card

### Semana 5: Centro de Aprobaciones HITL

- Vista `/approvals` con lista + badge contador en sidebar
- `ApprovalDetail`: payload expandido, contexto del flow
- Botones Aprobar / Rechazar con campo de notas
- Llamada a `POST /approvals/{task_id}`
- Actualización optimista del estado en UI

### Semana 6: Historial + Logs de eventos

- Vista `/tasks` paginada con filtros (status, flow_type, fechas)
- Detalle de task: `EventTimeline` con `domain_events`
- Vista `/events`: stream en tiempo real
- Input/output del flow expandible en detalle

### Semana 7: Agentes + Workflows + Trigger manual + Overview

- Vista `/agents`: lista con SOUL/SKILL legible
- Vista `/workflows`: templates activos/draft/archived
- Trigger manual: formulario con `input_data` JSON
- Vista `/architect`: chat MDC embebido
- Overview / home con métricas resumen

### Semana 8: CoctelPro — Definición y setup (5B)

- Definir SOUL de los 4 agentes
- Insertar agentes en `agent_catalog`
- Crear workflows con ArchitectFlow o directo en DB
- Configurar guardrails y umbrales HITL por agente
- Cargar datos de prueba realistas

### Semana 9: Demo end-to-end + polish

- Ejecutar flujo completo de demo (cotización → compra → rechazo)
- Corregir bugs visuales y de estado
- Polish visual del Kanban y aprobaciones
- Script de demo escrito y ensayado
- 5C (memoria vectorial) si queda tiempo

### Semana 10: Buffer + ajustes finales

- Margen para imprevistos
- Refinamiento de UX según feedback propio
- Documentación interna básica

---

## 10 — Orden de implementación (dependencias)

| # | Paso | Depende de |
|---|---|---|
| 1 | Setup Next.js + Supabase Auth | — |
| 2 | Tabla `org_members` + middleware FastAPI | 1 |
| 3 | Layout base + OrgSelector | 1, 2 |
| 4 | Habilitar Realtime en Supabase | — |
| 5 | Hook `useRealtimeDashboard` | 4 |
| 6 | KanbanBoard + TaskCard | 3, 5 |
| 7 | Centro de Aprobaciones | 3, 5 |
| 8 | Historial + EventTimeline | 3 |
| 9 | Agentes / Workflows / Trigger manual | 3 |
| 10 | SOUL de agentes CoctelPro | — (puede ir en paralelo) |
| 11 | Setup CoctelPro en DB | 9, 10 |
| 12 | Demo end-to-end + polish | 6, 7, 8, 11 |

---

## 11 — Criterio de éxito

### Criterio técnico

- Dashboard corre en local con `npm run dev`
- Backend Python corre con `uvicorn main:app`
- Kanban se actualiza sin F5 al cambiar tasks
- Aprobación HITL fluye de punta a punta
- Los 3 roles funcionan con accesos correctos
- Sin errores de consola durante el flujo demo

### Criterio demo

- CoctelPro tiene los 4 agentes configurados
- Se puede ejecutar `cotizacion_flow` desde el Dashboard
- Aparece una aprobación pendiente en tiempo real
- Se puede aprobar/rechazar desde la UI
- El log de eventos muestra el trail completo
- La demo completa dura menos de 15 minutos

### Fuera de scope para Fase 5

Deploy en cloud, billing, SSO, GDPR, marketplace, SDK, memoria vectorial (5C),
gestión de roles desde UI, múltiples orgs simultáneas en demo, mobile responsiveness.

---

## 12 — Reglas de implementación

1. **El frontend es solo vista.** Ninguna lógica de negocio en Next.js. Toda decisión pasa por el backend Python.
2. **TanStack Query es la única fuente de verdad en cliente.** No hay estado local duplicado de tasks o approvals.
3. **Realtime invalida, no reemplaza.** Los eventos Realtime solo llaman `invalidateQueries`. El fetch real siempre va a la API.
4. **El `org_id` viaja siempre como header.** Nunca en el body ni en la URL.
5. **Optimistic updates solo en aprobaciones.** Es la única acción donde la latencia es visible y el rollback es simple.

---

## Resumen de archivos Fase 5

| Archivo | Tipo | Descripción |
|---|---|---|
| `sql/008_org_members.sql` | SQL nuevo | Tabla de miembros con roles |
| `src/api/middleware/auth.py` | Python nuevo | Verificación de org membership |
| `dashboard/` | Next.js nuevo | Aplicación completa del Dashboard |
| `dashboard/hooks/useRealtimeDashboard.ts` | TS nuevo | Suscripciones Realtime |
| Supabase Realtime config | Config | Habilitar replica en 3 tablas |
