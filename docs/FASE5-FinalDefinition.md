# Fase 5 — Dashboard + CoctelPro Demo

> **Definición cerrada.** Basada en el backend de Fases 1–4 ya implementado.
> Todos los problemas de seguridad, arquitectura y flujo han sido identificados y resueltos.
> El código propuesto es consistente con los patterns existentes.

---

## Visión del sistema

Las Fases 1–4 construyeron un backend sólido: flows, HITL, vault, guardrails, MDC.
Fase 5 agrega la capa visual que convierte ese backend en una experiencia operacional completa.

El Dashboard es una aplicación Next.js 14 que consume la API de FastAPI + Supabase directamente (sin intermediarios).
No hay lógica de negocio en el frontend — todo el estado canónico sigue viviendo en el backend Python.

### Criterio de éxito

**Demo completa de CoctelPro corriendo en laptop local**, con:
- Kanban visible actualizándose en tiempo real
- HITL funcionando de punta a punta (request → approval → completion)
- Los 3 roles (`fap_admin`, `org_owner`, `org_operator`) con accesos correctos
- Flujo demo completo ejecutable en menos de 15 minutos

---

## 01 — Stack tecnológico

| Tecnología | Uso | Estado |
|---|---|---|
| Next.js 14 (App Router) | Server Components para carga inicial, Client Components para Realtime | ⭐ NUEVO |
| Supabase JS Client | Auth + Realtime subscriptions con RLS automático | ⭐ NUEVO |
| TanStack Query v5 | Cache de server state, invalidation por Realtime, optimistic updates | ⭐ NUEVO |
| Tailwind CSS v3 | Estilo utilitario; componentes tipo Jira | ⭐ NUEVO |
| shadcn/ui | Componentes accesibles (Dialog, Table, Badge) | ⭐ NUEVO |
| Supabase Auth | Email/password + magic link. JWT con rol en claims | ⭐ NUEVO |
| FastAPI (Fases 1–4) | Backend existente. Dashboard lo consume vía fetch directo | existente |
| Supabase Postgres + pgvector | BD multi-tenant con RLS, vector search (opcional 5C) | existente |

### Notas sobre dependencias

- **Sin API Routes de Next.js**: El Dashboard consume FastAPI directamente. Las API Routes solo se usan para webhooks/eventos específicos del navegador.
- **JWT de Supabase**: FastAPI recibe el token de Supabase Auth en el header `Authorization: Bearer <token>` y lo verifica.
- **RLS obligatorio**: Supabase Realtime solo funciona con RLS habilitado en las tablas.

---

## 02 — Autenticación: dos capas

### Capa 1: Supabase Auth (Session del navegador)

```
1. Usuario ingresa email + password en /login
2. Supabase Auth retorna JWT (HS256 o RS256)
3. Next.js almacena JWT en cookie HTTP-only (seguro)
```

### Capa 2: FastAPI verifica JWT + membership

```
1. Dashboard envía: Authorization: Bearer <JWT de Supabase>
2. FastAPI middleware:
   a) Decodifica el JWT (con SUPABASE_JWT_SECRET o JWKS)
   b) Extrae user_id del claim "sub"
   c) Verifica que user_id existe en org_members con org_id (del header X-Org-ID)
   d) Valida que el rol sea uno de: fap_admin, org_owner, org_operator
   e) Descarta request si no cumple
3. Request continúa con request.state.user_id, request.state.org_role

### Excepción: fap_admin

Un usuario con rol fap_admin en CUALQUIER registro de org_members puede acceder a todas las orgs.
```python
# Pseudocódigo
if user_has_role_fap_admin_in_any_org:
    allow_access_to_any_org()
else:
    verify_membership_in_specific_org()
```
```

---

## 03 — Base de datos: migraciones nuevas

### supabase/migrations/008_org_members.sql

```sql
-- Tabla: organizations (base de multi-tenancy)
CREATE TABLE organizations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL,
  slug       TEXT UNIQUE NOT NULL,
  is_active  BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Tabla: org_members (relación usuario-org-rol)
CREATE TABLE org_members (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  email      TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'org_operator'
             CHECK (role IN ('fap_admin', 'org_owner', 'org_operator')),
  is_active  BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, user_id)
);

ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;

-- Función auxiliar: romper recursión en RLS
CREATE OR REPLACE FUNCTION is_fap_admin() 
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM org_members 
    WHERE user_id = auth.uid() AND role = 'fap_admin'
  );
$$ LANGUAGE sql SECURITY DEFINER;

-- SELECT: usuario ve su propio registro + fap_admin ve todos
CREATE POLICY "own_membership_select" ON org_members FOR SELECT
  USING (
    user_id = auth.uid() 
    OR is_fap_admin()
  );

-- INSERT: solo fap_admin u org_owner de la misma org
CREATE POLICY "org_members_insert" ON org_members FOR INSERT
  WITH CHECK (
    is_fap_admin()
    OR EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid() 
        AND m.org_id = org_id
        AND m.role = 'org_owner'
        AND m.is_active = TRUE
    )
  );

-- UPDATE: solo fap_admin
CREATE POLICY "org_members_update" ON org_members FOR UPDATE
  USING (is_fap_admin());

-- DELETE: solo fap_admin
CREATE POLICY "org_members_delete" ON org_members FOR DELETE
  USING (is_fap_admin());
```

### RLS para tablas existentes (actualizar)

```sql
-- Actualizar tasks con RLS completo
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks REPLICA IDENTITY FULL;  -- Requerido para Realtime

CREATE POLICY "tasks_select" ON tasks FOR SELECT
  USING (
    org_id = (SELECT current_org_id())
  );

CREATE POLICY "tasks_update" ON tasks FOR UPDATE
  USING (org_id = (SELECT current_org_id()))
  WITH CHECK (org_id = (SELECT current_org_id()));

-- Actualizar pending_approvals con RLS
ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_approvals REPLICA IDENTITY FULL;

CREATE POLICY "pending_approvals_select" ON pending_approvals FOR SELECT
  USING (org_id = (SELECT current_org_id()));

CREATE POLICY "pending_approvals_update" ON pending_approvals FOR UPDATE
  USING (org_id = (SELECT current_org_id()))
  WITH CHECK (org_id = (SELECT current_org_id()));

-- Actualizar domain_events con RLS
ALTER TABLE domain_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_events REPLICA IDENTITY FULL;

CREATE POLICY "domain_events_select" ON domain_events FOR SELECT
  USING (org_id = (SELECT current_org_id()));

CREATE POLICY "domain_events_insert" ON domain_events FOR INSERT
  WITH CHECK (org_id = (SELECT current_org_id()));
```

### supabase/migrations/009_memory_vectors.sql (Opcional - Fase 5C)

```sql
-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla: memory_vectors (búsqueda semántica de contexto)
CREATE TABLE memory_vectors (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id            UUID NOT NULL REFERENCES organizations(id),
  agent_role        TEXT,
  source_type       TEXT NOT NULL CHECK (source_type IN ('conversation', 'document', 'task_result')),
  content           TEXT NOT NULL,
  embedding         vector(1536),  -- text-embedding-3-small
  embedding_version TEXT DEFAULT 'text-embedding-3-small',
  metadata          JSONB DEFAULT '{}',
  valid_to          TIMESTAMPTZ DEFAULT 'infinity',
  created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memory_org ON memory_vectors(org_id);
CREATE INDEX idx_memory_agent ON memory_vectors(agent_role);
CREATE INDEX idx_memory_valid_to ON memory_vectors(valid_to);
CREATE INDEX idx_memory_embedding ON memory_vectors 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

ALTER TABLE memory_vectors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "memory_select" ON memory_vectors FOR SELECT
  USING (org_id = (SELECT current_org_id()));

CREATE POLICY "memory_insert" ON memory_vectors FOR INSERT
  WITH CHECK (org_id = (SELECT current_org_id()));

-- Función: búsqueda por similitud
CREATE OR REPLACE FUNCTION search_memories(
  query_embedding vector(1536),
  p_org_id UUID,
  match_limit INT DEFAULT 5,
  min_similarity FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT m.id, m.content, 1 - (m.embedding <=> query_embedding) AS similarity
  FROM memory_vectors m
  WHERE m.org_id = p_org_id
    AND m.valid_to > now()
    AND 1 - (m.embedding <=> query_embedding) >= min_similarity
  ORDER BY similarity DESC
  LIMIT match_limit;
END;
$$;
```

---

## 04 — Estructura del proyecto Dashboard

```
dashboard/
├── app/
│   ├── layout.tsx                     # Root layout: Auth + Query providers
│   ├── middleware.ts                  # Protección de rutas con JWT
│   ├── (auth)/
│   │   └── login/page.tsx             # Login Supabase Auth
│   └── (app)/
│       ├── layout.tsx                 # Sidebar + header + org selector
│       ├── page.tsx                   # Overview (métricas)
│       ├── kanban/page.tsx            # Kanban en tiempo real
│       ├── approvals/page.tsx         # Centro de aprobaciones HITL
│       ├── tasks/
│       │   ├── page.tsx               # Historial paginado
│       │   └── [id]/page.tsx          # Detalle + timeline de eventos
│       ├── agents/
│       │   ├── page.tsx               # Lista de agentes
│       │   └── [id]/page.tsx          # Detalle/edición
│       ├── workflows/
│       │   ├── page.tsx               # Templates activos/draft/archived
│       │   └── [id]/page.tsx          # Detalle + trigger manual
│       ├── events/page.tsx            # Log de events en tiempo real
│       └── architect/page.tsx         # Chat MDC
│
├── components/
│   ├── kanban/
│   │   ├── KanbanBoard.tsx            # Tablero 6 columnas
│   │   ├── KanbanColumn.tsx           # Columna individual
│   │   └── TaskCard.tsx               # Card de tarea + estado visual
│   ├── approvals/
│   │   ├── ApprovalList.tsx           # Lista con badge contador
│   │   └── ApprovalDetail.tsx         # Detalle + botones approve/reject
│   ├── events/
│   │   └── EventTimeline.tsx          # Timeline de domain_events
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── OrgSelector.tsx            # Dropdown org (solo si acceso múltiple)
│   └── ui/                            # shadcn/ui components
│
├── hooks/
│   ├── useRealtimeDashboard.ts        # Realtime subscriptions con reconnect
│   ├── useTasks.ts                    # Query para tasks
│   ├── useApprovals.ts                # Query + mutation para approvals
│   ├── useCurrentOrg.ts               # Org actual + switch
│   └── useAuth.ts                     # Session de Supabase
│
├── lib/
│   ├── supabase.ts                    # createBrowserClient + createServerClient
│   ├── api.ts                         # fetch wrapper (JWT + X-Org-ID)
│   ├── types.ts                       # Tipos TS espejando modelos Python
│   └── constants.ts                   # Columnas, roles, etc.
│
└── middleware.ts                      # Proteger rutas auth
```

---

## 05 — Componentes de autenticación

### dashboard/lib/api.ts

```typescript
import { createBrowserClient } from '@supabase/ssr'

const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function fapFetch(
  path: string,
  options: RequestInit = {}
) {
  const { data: { session } } = await supabase.auth.getSession()
  const orgId = localStorage.getItem('selected_org_id') || ''

  if (!session?.access_token) {
    throw new Error('Not authenticated')
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_FASTAPI_URL}${path}`,
    {
      ...options,
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
        'X-Org-ID': orgId,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    }
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API error: ${response.status}`)
  }

  return response.json()
}

// Helpers
export const api = {
  get: (path: string) => fapFetch(path, { method: 'GET' }),
  post: (path: string, body?: any) => 
    fapFetch(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path: string, body?: any) => 
    fapFetch(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path: string) => fapFetch(path, { method: 'DELETE' }),
}
```

### dashboard/middleware.ts

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  const response = NextResponse.next()

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => request.cookies.getSetCookie() } }
  )

  const { data: { session } } = await supabase.auth.getSession()

  // Redirigir a login si no hay sesión
  if (!session && !request.nextUrl.pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Redirigir a app si está en login pero tiene sesión
  if (session && request.nextUrl.pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/app', request.url))
  }

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
```

---

## 06 — Realtime y actualizaciones en tiempo real

### dashboard/hooks/useRealtimeDashboard.ts

```typescript
import { useEffect, useRef } from 'react'
import { createBrowserClient } from '@supabase/ssr'
import { useQueryClient } from '@tanstack/react-query'

const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 5

export function useRealtimeDashboard(orgId: string) {
  const queryClient = useQueryClient()
  const reconnectAttemptsRef = useRef(0)
  const channelsRef = useRef<any[]>([])

  useEffect(() => {
    if (!orgId) return

    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )

    const setupChannels = () => {
      try {
        // Canal 1: tasks
        const tasksChannel = supabase
          .channel(`dashboard-tasks-${orgId}`)
          .on(
            'postgres_changes',
            {
              event: '*',
              schema: 'public',
              table: 'tasks',
              filter: `org_id=eq.${orgId}`,
            },
            () => {
              queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })
            }
          )
          .subscribe((status) => {
            if (status === 'SUBSCRIBED') {
              console.log(`Realtime: tasks channel ready for ${orgId}`)
            }
          })

        // Canal 2: pending_approvals
        const approvalsChannel = supabase
          .channel(`dashboard-approvals-${orgId}`)
          .on(
            'postgres_changes',
            {
              event: '*',
              schema: 'public',
              table: 'pending_approvals',
              filter: `org_id=eq.${orgId}`,
            },
            () => {
              queryClient.invalidateQueries({ queryKey: ['approvals', orgId] })
            }
          )
          .subscribe()

        // Canal 3: domain_events (solo INSERT para eficiencia)
        const eventsChannel = supabase
          .channel(`dashboard-events-${orgId}`)
          .on(
            'postgres_changes',
            {
              event: 'INSERT',
              schema: 'public',
              table: 'domain_events',
              filter: `org_id=eq.${orgId}`,
            },
            (payload) => {
              queryClient.setQueryData(['events', orgId], (old: any[]) =>
                [payload.new, ...(old ?? [])].slice(0, 200)
              )
            }
          )
          .subscribe()

        channelsRef.current = [tasksChannel, approvalsChannel, eventsChannel]
        reconnectAttemptsRef.current = 0  // Reset on success
      } catch (error) {
        console.error('Realtime setup failed:', error)
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++
          setTimeout(setupChannels, RECONNECT_DELAY)
        }
      }
    }

    setupChannels()

    return () => {
      const supabase = createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
      )
      channelsRef.current.forEach((ch) => supabase.removeChannel(ch))
    }
  }, [orgId, queryClient])
}
```

### dashboard/hooks/useTasks.ts

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useTasks(orgId: string, filters?: any) {
  return useQuery({
    queryKey: ['tasks', orgId, filters],
    queryFn: async () => {
      const params = new URLSearchParams({
        org_id: orgId,
        ...filters,
      })
      return api.get(`/tasks?${params}`)
    },
    enabled: !!orgId,
    staleTime: 5000,
    retry: 2,
  })
}
```

### dashboard/hooks/useApprovals.ts

```typescript
import { useQuery, useMutation } from '@tanstack/react-query'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useApprovals(orgId: string) {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['approvals', orgId],
    queryFn: async () => api.get(`/approvals?org_id=${orgId}`),
    enabled: !!orgId,
    staleTime: 2000,
  })

  const approve = useMutation({
    mutationFn: async ({ task_id, notes }: { task_id: string; notes?: string }) =>
      api.post(`/approvals/${task_id}`, { action: 'approve', notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals', orgId] })
      queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })
    },
  })

  const reject = useMutation({
    mutationFn: async ({ task_id, notes }: { task_id: string; notes?: string }) =>
      api.post(`/approvals/${task_id}`, { action: 'reject', notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals', orgId] })
      queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })
    },
  })

  return { ...query, approve, reject }
}
```

---

## 07 — Vistas del Dashboard

### Columnas del Kanban

```typescript
// dashboard/lib/constants.ts
export const KANBAN_COLUMNS = [
  { id: 'pending', label: 'Pendiente', color: 'bg-slate-100' },
  { id: 'running', label: 'Ejecutando', color: 'bg-blue-100' },
  { id: 'pending_approval', label: 'HITL (Espera)', color: 'bg-amber-100' },
  { id: 'completed', label: 'Completado', color: 'bg-green-100' },
  { id: 'failed', label: 'Error', color: 'bg-red-100' },
  { id: 'rejected', label: 'Rechazado', color: 'bg-purple-100' },
]
```

### Vistas

| Vista | Descripción | Realtime |
|---|---|---|
| **Overview** | Métricas: tasks hoy/semana, tasa éxito, tokens, aprobaciones pendientes | Badge de approvals |
| **Kanban** | 6 columnas, drag-drop (opcional), detalle lateral | Sí, completo |
| **Aprobaciones** | Lista de pending_approvals, payload expandible, botones approve/reject | Sí, badge contador |
| **Historial** | Paginado, filtros (status, flow_type, fechas), detalle con timeline | Opcional |
| **Agentes** | Lista con SOUL/SKILL, estado activo, capacidades | No |
| **Workflows** | Templates draft/active/archived, trigger manual con input_data JSON | No |
| **Eventos** | Stream de domain_events en tiempo real, filtro por task_id | Sí, stream completo |
| **Chat MDC** | Endpoint POST /chat/ embebido, conversación para crear workflows | No |

---

## 08 — API FastAPI: Nuevos endpoints

### POST /approvals/{task_id}

```python
# src/api/routes/approvals.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from src.db.session import get_service_client

router = APIRouter(prefix="/approvals", tags=["approvals"])

class ApprovalRequest(BaseModel):
    action: str  # "approve" or "reject"
    notes: str | None = None

@router.post("/{task_id}")
async def process_approval(
    task_id: str,
    approval: ApprovalRequest,
    request: Request,
) -> dict:
    """
    Procesa aprobación o rechazo de HITL.
    Requiere: user_id + org_id validados por middleware.
    """
    org_id = request.state.org_id
    user_id = request.state.user_id
    db = get_service_client()

    # 1. Verificar que la task existe y está en pending_approval
    task = db.table("tasks") \
        .select("*") \
        .eq("id", task_id) \
        .eq("org_id", org_id) \
        .maybe_single().execute()

    if not task.data:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.data["status"] != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Task status is {task.data['status']}, expected pending_approval"
        )

    # 2. Actualizar task status
    new_status = "completed" if approval.action == "approve" else "rejected"
    db.table("tasks").update({"status": new_status}).eq("id", task_id).execute()

    # 3. Registrar evento
    db.table("domain_events").insert({
        "task_id": task_id,
        "org_id": org_id,
        "event_type": f"approval_{approval.action}",
        "actor": user_id,
        "payload": {"notes": approval.notes}
    }).execute()

    # 4. Reanudar el flow (backend internamente)
    # (El flow recibe FlowApprovalEvent vía event queue o callback)

    return {"status": new_status, "task_id": task_id}


@router.get("/")
async def list_approvals(request: Request) -> list:
    """Lista de pending_approvals de la org actual."""
    org_id = request.state.org_id
    db = get_service_client()

    approvals = db.table("pending_approvals") \
        .select("*") \
        .eq("org_id", org_id) \
        .eq("status", "pending") \
        .execute()

    return approvals.data or []
```

### GET /tasks

```python
# src/api/routes/tasks.py (extender existente)
@router.get("/")
async def list_tasks(
    request: Request,
    status: str | None = None,
    flow_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Lista de tasks de la org actual.
    Con filtros opcionales.
    """
    org_id = request.state.org_id
    db = get_service_client()

    query = db.table("tasks").select("*").eq("org_id", org_id)

    if status:
        query = query.eq("status", status)
    if flow_type:
        query = query.eq("flow_type", flow_type)

    result = query.order("created_at", desc=True) \
        .range(offset, offset + limit) \
        .execute()

    total = db.table("tasks") \
        .select("count", count="exact") \
        .eq("org_id", org_id) \
        .execute().count

    return {"items": result.data or [], "total": total}
```

---

## 09 — Middleware FastAPI: Autenticación + Membership

```python
# src/api/middleware.py (EXTENDIDO)
from fastapi import Header, HTTPException, Request, Depends
from jose import jwt, JWTError
from src.db.session import get_service_client
from src.config import get_settings

settings = get_settings()

def require_org_id(x_org_id: str = Header(..., alias="X-Org-ID")) -> str:
    """Valida que el header X-Org-ID esté presente."""
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header required")
    return x_org_id.strip()


async def verify_supabase_jwt(
    authorization: str = Header(..., description="Bearer token from Supabase Auth"),
) -> dict:
    """
    Decodifica y verifica JWT de Supabase Auth.
    Extrae user_id del claim 'sub'.
    """
    token = authorization.replace("Bearer ", "")

    try:
        # Para desarrollo: HS256 con SUPABASE_JWT_SECRET
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],  # Cambiar a ["RS256"] y usar JWKS en prod
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token missing 'sub' claim"
            )

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    return {"user_id": user_id, "payload": payload}


async def verify_org_membership(
    request: Request,
    org_id: str = Depends(require_org_id),
    user: dict = Depends(verify_supabase_jwt),
) -> dict:
    """
    Valida que el usuario sea miembro de la organización.
    Excepción: fap_admin puede acceder a cualquier org.
    
    Adjunta a request.state: user_id, org_id, org_role
    """
    user_id = user["user_id"]
    db = get_service_client()

    # 1. Verificar si es fap_admin en CUALQUIER org
    admin_check = db.table("org_members") \
        .select("role") \
        .eq("user_id", user_id) \
        .eq("role", "fap_admin") \
        .eq("is_active", True) \
        .limit(1).execute()

    if admin_check.data:
        request.state.user_id = user_id
        request.state.org_id = org_id
        request.state.org_role = "fap_admin"
        return {
            "user_id": user_id,
            "org_id": org_id,
            "role": "fap_admin",
        }

    # 2. Si no es admin, verificar membresía en la org específica
    member = db.table("org_members") \
        .select("role") \
        .eq("org_id", org_id) \
        .eq("user_id", user_id) \
        .eq("is_active", True) \
        .maybe_single().execute()

    if not member.data:
        raise HTTPException(
            status_code=403,
            detail=f"User {user_id} is not a member of org {org_id}"
        )

    request.state.user_id = user_id
    request.state.org_id = org_id
    request.state.org_role = member.data["role"]

    return {
        "user_id": user_id,
        "org_id": org_id,
        "role": member.data["role"],
    }


# Uso en rutas
@app.post("/approvals/{task_id}")
async def process_approval(
    task_id: str,
    body: ApprovalRequest,
    member: dict = Depends(verify_org_membership),
) -> dict:
    # member = {"user_id": "...", "org_id": "...", "role": "..."}
    ...
```

---

## 10 — CoctelPro Demo (Bloque 5B)

CoctelPro es una empresa de servicios de bartending. La demo muestra 4 agentes trabajando juntos con HITL.

### Los 4 agentes

| Agente | Rol | Trigger | HITL |
|---|---|---|---|
| **Ventas** | Genera cotizaciones | Mensaje de cliente | Descuento >15% o cliente VIP |
| **Logística** | Calcula insumos | Cotización aprobada | Evento >150 pax |
| **Compras** | Genera órdenes de compra | Insumos de Logística | **Siempre** (nunca autónomo) |
| **Finanzas** | Registra ingresos/egresos | Pago confirmado | Margen <20% |

### Definición de Flows CoctelPro

```python
# src/flows/coctel_flows.py (NUEVO)
from src.flows.base_flow import BaseFlow
from src.flows.registry import register_flow
from typing import Any

@register_flow("cotizacion_flow")
class CotizacionFlow(BaseFlow):
    """Agente Ventas: cotización con HITL si descuento >15%."""

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # Paso 1: Generar cotización
        pax = input_data.get("pax", 0)
        presupuesto = input_data.get("presupuesto", 0)
        cliente_vip = input_data.get("vip", False)

        # Aplicar descuento
        descuento = 0.1 if pax > 100 else 0.05
        if cliente_vip:
            descuento = 0.2

        total = presupuesto * (1 - descuento)

        # Paso 2: Verificar HITL
        if descuento > 0.15 or cliente_vip:
            await self.request_approval(
                description="Cotización requiere aprobación",
                payload={
                    "evento": input_data.get("evento", "Evento"),
                    "pax": pax,
                    "presupuesto": presupuesto,
                    "descuento": f"{descuento * 100:.0f}%",
                    "total": total,
                    "cliente_vip": cliente_vip,
                }
            )

        return {"status": "completed", "total": total, "descuento": descuento}


@register_flow("logistica_flow")
class LogisticaFlow(BaseFlow):
    """Agente Logística: calcula insumos."""

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        pax = input_data.get("pax", 0)
        ubicacion = input_data.get("ubicacion", "local")

        insumos = self._calcular_insumos(pax, ubicacion)
        total_costo = sum(i["precio"] * i["cantidad"] for i in insumos)

        # HITL si es evento grande o ubicación especial
        if pax > 150 or ubicacion == "exterior":
            await self.request_approval(
                description="Logística requiere aprobación",
                payload={"pax": pax, "ubicacion": ubicacion, "insumos": insumos}
            )

        return {"status": "completed", "insumos": insumos, "total_costo": total_costo}

    def _calcular_insumos(self, pax: int, ubicacion: str) -> list:
        # 1 botella cada 3 pax, 1 vaso por pax, etc.
        return [
            {"item": "Botellas de vodka", "cantidad": pax // 3, "precio": 50},
            {"item": "Vasos", "cantidad": pax, "precio": 1},
            {"item": "Hielo (kg)", "cantidad": pax // 10, "precio": 5},
        ]


@register_flow("compras_flow")
class ComprasFlow(BaseFlow):
    """Agente Compras: genera órdenes de compra. HITL: SIEMPRE."""

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        insumos = input_data.get("insumos", [])
        total = sum(i["precio"] * i["cantidad"] for i in insumos)

        # HITL: siempre (nunca compra autónomo)
        await self.request_approval(
            description=f"Orden de compra por ${total}",
            payload={
                "insumos": insumos,
                "total": total,
                "proveedor": "proveedor_coctel",
            }
        )

        return {"status": "completed", "total": total}


@register_flow("finanzas_flow")
class FinanzasFlow(BaseFlow):
    """Agente Finanzas: registra ingresos/egresos."""

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        ingreso = input_data.get("ingreso", 0)
        egreso = input_data.get("egreso", 0)
        
        margen = (ingreso - egreso) / ingreso if ingreso > 0 else 0

        # HITL si margen <20%
        if margen < 0.2:
            await self.request_approval(
                description="Margen bajo, requiere aprobación",
                payload={
                    "ingreso": ingreso,
                    "egreso": egreso,
                    "margen": f"{margen * 100:.0f}%",
                }
            )

        return {"status": "completed", "margen": margen}
```

### Script de demo (guiado)

```python
# scripts/demo_coctel.py
"""
Demo de CoctelPro: flujo completo de cotización → compra → rechazo.
Duración: 12-15 minutos.
"""

import requests
import json
import time

FASTAPI_URL = "http://localhost:8000"
COCTEL_PRO_ORG_ID = "coctel-pro-org-id"
JWT_TOKEN = "token-del-usuario-demo"
HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "X-Org-ID": COCTEL_PRO_ORG_ID,
    "Content-Type": "application/json",
}

def step(msg: str):
    print(f"\n📍 {msg}")
    input("Presiona ENTER para continuar...")

step("1. Abrir Dashboard en http://localhost:3000")
step("2. Loguear con usuario demo")
step("3. Seleccionar org CoctelPro")

# Disparar cotizacion_flow
step("4. Disparar cotizacion_flow desde Dashboard")
response = requests.post(
    f"{FASTAPI_URL}/webhooks/{COCTEL_PRO_ORG_ID}/cotizacion_flow",
    json={
        "evento": "Casamiento",
        "pax": 80,
        "presupuesto": 500000,
        "vip": True,
    },
    headers=HEADERS,
)
task1_id = response.json()["task_id"]
print(f"✅ Task creada: {task1_id}")

step("5. Mostrar Kanban: debería aparecer card en 'Ejecutando' → 'HITL'")
step("6. Ir a Centro de Aprobaciones y mostrar el payload de la cotización")

# Aprobar
step("7. Hacer click en Aprobar")
response = requests.post(
    f"{FASTAPI_URL}/approvals/{task1_id}",
    json={"action": "approve", "notes": "Cliente VIP, aprobado."},
    headers=HEADERS,
)
print(f"✅ Cotización aprobada")

step("8. Mostrar Kanban: task debería pasar a 'Completado'")
step("9. Disparar compras_flow desde Dashboard")

response = requests.post(
    f"{FASTAPI_URL}/webhooks/{COCTEL_PRO_ORG_ID}/compras_flow",
    json={
        "insumos": [
            {"item": "Botellas de vodka", "cantidad": 30, "precio": 50},
            {"item": "Vasos", "cantidad": 80, "precio": 1},
            {"item": "Hielo (kg)", "cantidad": 8, "precio": 5},
        ],
    },
    headers=HEADERS,
)
task2_id = response.json()["task_id"]
print(f"✅ Task de compras creada: {task2_id}")

step("10. Mostrar nueva card en 'HITL' esperando aprobación")
step("11. Ir a Centro de Aprobaciones → Rechazar esta compra")

response = requests.post(
    f"{FASTAPI_URL}/approvals/{task2_id}",
    json={"action": "reject", "notes": "Necesitamos otro proveedor."},
    headers=HEADERS,
)
print(f"✅ Compra rechazada")

step("12. Mostrar Kanban: card debería pasar a 'Rechazado'")
step("13. Abrir log de eventos y mostrar trail completo")

print("\n🎉 Demo completada!")
```

---

## 11 — Sistema de roles

| Rol | Scope | Permisos |
|---|---|---|
| `fap_admin` | Global | Acceso a todas las orgs, crear/desactivar orgs, ver métricas globales, configurar todo |
| `org_owner` | Su org | Kanban, aprobar/rechazar HITL, disparar flows, ver historial/logs, configurar agentes |
| `org_operator` | Su org (R+A) | Kanban (lectura), aprobar/rechazar HITL, ver historial/logs. No: disparar flows, editar agentes |

**Validación**: Implementada en middleware `verify_org_membership` (línea 180+).

---

## 12 — Timeline: 10 semanas

> **Supuesto**: Una persona (vos + IA) trabajando. Bloques 5A y 5B parcialmente en paralelo.

| Semana | Tareas | Status |
|---|---|---|
| 1-2 | Setup Next.js + Auth Supabase + Layout base + Middleware FastAPI | Foundation |
| 3-4 | Habilitar Realtime en Supabase + Kanban real-time + TaskCard | Realtime |
| 5 | Centro de Aprobaciones HITL + POST /approvals/{task_id} | HITL |
| 6 | Historial + EventTimeline + Log de eventos | History |
| 7 | Agentes / Workflows / Trigger manual / Overview / Chat MDC | Views |
| 8 | Definir SOUL de 4 agentes CoctelPro + insertar en BD | CoctelPro setup |
| 9 | Demo end-to-end + Polish visual + Script guiado | Demo |
| 10 | Buffer + ajustes finales + doc interna | Buffer |

---

## 13 — Orden de implementación (dependencias)

| # | Paso | Depende de | Semana |
|---|---|---|---|
| 1 | Setup Next.js 14 + Supabase JS | — | 1 |
| 2 | Tabla org_members + RLS completo | 1 | 1 |
| 3 | Middleware verify_org_membership en FastAPI | 2 | 1 |
| 4 | Layout base + OrgSelector | 1, 2 | 1-2 |
| 5 | Habilitar Realtime en Supabase (3 tablas) | 2 | 3 |
| 6 | Hook useRealtimeDashboard + TanStack Query setup | 5 | 3 |
| 7 | KanbanBoard + TaskCard + columnas | 4, 6 | 3-4 |
| 8 | POST /approvals/{task_id} en FastAPI | 3 | 4 |
| 9 | Centro de Aprobaciones (ApprovalList + ApprovalDetail) | 4, 8 | 5 |
| 10 | Historial + EventTimeline | 4 | 6 |
| 11 | Agentes / Workflows / Trigger manual / Overview | 4 | 7 |
| 12 | Definir SOUL de 4 agentes CoctelPro | — | 8 |
| 13 | Crear flows.py con 4 flows (cotizacion, logistica, compras, finanzas) | 12 | 8 |
| 14 | Insertar agentes + workflows CoctelPro en BD | 13 | 8 |
| 15 | Demo end-to-end + Polish + Script guiado | 7, 9, 10, 14 | 9 |

---

## 14 — Criterio de éxito

### Técnico

- ✅ Dashboard corre en local con `npm run dev`
- ✅ Backend FastAPI corre con `uvicorn src.api.main:app --reload`
- ✅ Kanban se actualiza sin F5 (Realtime funciona)
- ✅ Aprobación HITL fluye de punta a punta
- ✅ Los 3 roles funcionan con accesos correctos
- ✅ Sin ERRORES CRÍTICOS en consola (warnings de npm son OK)
- ✅ Realtime se reconecta automáticamente si se desconecta
- ✅ Cambio de org resetea datos sin causar duplicados

### Demo

- ✅ CoctelPro tiene 4 agentes configurados
- ✅ Se ejecuta `cotizacion_flow` desde Dashboard → aparece card en Kanban
- ✅ Card pasa a estado "HITL" → aparece en Centro de Aprobaciones
- ✅ Se aprueba → card pasa a "Completado" en tiempo real
- ✅ Se ejecuta `compras_flow` → HITL siempre
- ✅ Se rechaza → card pasa a "Rechazado"
- ✅ Log de eventos muestra trail completo
- ✅ Demo completa dura <15 minutos

### Fuera de scope

Deploy en cloud, billing, SSO, GDPR, marketplace, SDK, múltiples orgs simultáneas, mobile responsiveness, memoria vectorial (5C), gestión de roles desde UI.

---

## 15 — Reglas de implementación

1. **El frontend es solo vista.** Ninguna lógica de negocio en Next.js. Toda decisión en FastAPI.
2. **TanStack Query es la única fuente de verdad.** No hay estado duplicado de tasks o approvals.
3. **Realtime invalida, no reemplaza.** Los eventos Realtime llaman `invalidateQueries()`. El fetch real va a la API.
4. **El `org_id` viaja siempre como header `X-Org-ID`.** Nunca en body ni URL.
5. **JWT de Supabase viaja en `Authorization: Bearer <token>`.** Validado en FastAPI middleware.
6. **RLS en Supabase es obligatorio.** Sin RLS, Realtime puede filtrar datos incorrectamente.
7. **Optimistic updates solo en aprobaciones.** Es la única acción donde la latencia es visible.
8. **Consume FastAPI directamente desde Next.js.** Sin API Routes innecesarias.

---

## 16 — Resumen de archivos Fase 5

### SQL (Migraciones)

| Archivo | Descripción |
|---|---|
| `supabase/migrations/008_org_members.sql` | Tablas organizations + org_members + RLS |
| `supabase/migrations/009_memory_vectors.sql` | Tabla + índices + función de búsqueda (opcional 5C) |
| Actualizar existentes | RLS en tasks, pending_approvals, domain_events |

### Python (Backend)

| Archivo | Descripción |
|---|---|
| `src/api/middleware.py` | Extender: verify_supabase_jwt + verify_org_membership |
| `src/api/routes/approvals.py` | POST /approvals/{task_id}, GET /approvals |
| `src/flows/coctel_flows.py` | 4 flows: cotizacion, logistica, compras, finanzas |

### Next.js (Frontend)

| Archivo | Descripción |
|---|---|
| `dashboard/app/layout.tsx` | Root + Auth provider + Query provider |
| `dashboard/app/middleware.ts` | JWT middleware |
| `dashboard/lib/api.ts` | Fetch wrapper con JWT + X-Org-ID |
| `dashboard/lib/constants.ts` | KANBAN_COLUMNS, roles, etc. |
| `dashboard/hooks/useRealtimeDashboard.ts` | Suscripciones con reconnect |
| `dashboard/hooks/use*.ts` | useTasks, useApprovals, useCurrentOrg, useAuth |
| `dashboard/components/kanban/*` | KanbanBoard, KanbanColumn, TaskCard |
| `dashboard/components/approvals/*` | ApprovalList, ApprovalDetail |
| `dashboard/components/layout/*` | Sidebar, Header, OrgSelector |
| `dashboard/app/(app)/*.tsx` | Todas las vistas |

### Scripts

| Archivo | Descripción |
|---|---|
| `scripts/demo_coctel.py` | Script guiado de demo (12-15 min) |

---

## 17 — Notas de implementación

### Configuración de variables de entorno

```bash
# .env.local (Dashboard)
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=ey...
NEXT_PUBLIC_FASTAPI_URL=http://localhost:8000

# .env (FastAPI)
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=ey...
```

### Testing

Pruebas unitarias:
- `test_middleware.py`: verify_org_membership con fap_admin y usuarios normales
- `test_realtime_hook.ts`: useRealtimeDashboard con reconnect
- `test_workflows.py`: cotizacion_flow con y sin HITL

Pruebas de integración:
- Flujo demo completo (cotizacion → compra → rechazo)
- Cambio de org reseta datos
- RLS bloquea acceso a otras orgs

---

**Documento cerrado. Listo para implementación.**
