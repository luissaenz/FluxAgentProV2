# Análisis Paso 06 — Agent Playground (AGENTE: mm2.7)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `POST /agents/{role}/run` | `grep agents.py:251` | ✅ | `src/api/routes/agents.py:251-319` |
| 2 | Endpoint `GET /tasks/{task_id}` | `grep tasks.py:69` | ✅ | `src/api/routes/tasks.py:69-91` |
| 3 | Tabla `tasks` con columna `tokens_used` | `grep "tokens_used" 001_set_config_rpc.sql` | ⚠️ | No existe en migración 001. Probable migración posterior. |
| 4 | Tabla `tasks` con columna `tool_calls` | `grep "tool_calls" supabase/migrations/*.sql` | ❌ | NO EXISTE. No hay columna para tool calls. |
| 5 | `BaseCrew.get_last_tool_calls()` | `grep base_crew.py:206` | ✅ | `src/crews/base_crew.py:206-213` — retorna Dict, no se persiste |
| 6 | `TaskResponse.tokens_used` en backend | `grep tasks.py:33` | ✅ | `src/api/routes/tasks.py:33` — `tokens_used: int = 0` |
| 7 | `api.ts` client | `grep api.ts` | ✅ | `dashboard/lib/api.ts:54-77` — `api.get()`, `api.post()` |
| 8 | `BuilderLayout` existente | `grep BuilderLayout.tsx` | ✅ | `dashboard/components/builder/BuilderLayout.tsx:42-93` |
| 9 | `AgentForm` con `role` field | `grep AgentForm.tsx:31` | ✅ | `dashboard/components/builder/AgentForm.tsx:31` — `role: z.string()` |
| 10 | `RunAgentRequest` body | `grep agents.py:38` | ✅ | `src/api/routes/agents.py:38-41` — `input_data: Dict[str, Any]` |
| 11 | `RunAgentResponse` | `grep agents.py:44` | ✅ | `src/api/routes/agents.py:44-48` — `task_id: str, status: str` |
| 12 | `TaskResponse` status values | `grep types.ts:12` | ✅ | `dashboard/lib/types.ts:12-19` — pending/running/completed/failed |
| 13 | Componente `LoadingSpinner` | `grep LoadingSpinner` | ✅ | `dashboard/components/shared/LoadingSpinner.tsx` |
| 14 | Patrón de UI con `useQuery` + polling | `grep TanStack Query` | ✅ | `AgentForm.tsx:5` — `useQuery` de `@tanstack/react-query` |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | **Tabla `tasks` sin columna `tool_calls`**. `BaseCrew._last_tool_calls` no se persiste. El plan pide "mostrar tool calls con nombre y argumentos" pero no hay forma de получить esto. | **Agregar columna `tool_calls JSONB` a tabla `tasks`** via migración. Modificar `agents.py:299-306` para persistir `crew.get_last_tool_calls()` al completar. Alternativa: mostrar solo count de tools llamadas si no se quiere migración adicional. |
| D2 | **`tokens_used` en tabla `tasks`**: No vi migración que agregue esta columna (no existe en 001_set_config_rpc.sql:62-73). El código en `agents.py:304` la usa. | **Verificar que exista migración posterior** que agregue `tokens_used`. Si no existe, es discrepancia crítica. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema: Tabla `tasks`

**Estado actual (migración 001:62-73):**
```sql
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    flow_type       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    payload         JSONB DEFAULT '{}',
    result          JSONB,
    error           TEXT,
    correlation_id  TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

**Cambios necesarios:**
- ❌ **AGREGAR**: `tokens_used INTEGER DEFAULT 0` — existe en código (`agents.py:304`) pero NO en schema. Migración requerida.
- ❌ **AGREGAR**: `tool_calls JSONB DEFAULT '{}'` — para persistir tool calls por agente. Migración requerida.

### Integridad referencial
- `tasks.org_id` → `organizations.id` ✅ (ya existe)
- RLS en tasks: verificar que política permite a miembros de org leer sus propias tasks

### RLS Policies
- tasks usa `verify_org_membership` (no `require_org_id`) — extrae org_id del JWT claims
- policies en 001_set_config_rpc.sql:104-110 habilitan RLS en tasks

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componente nuevo: `AgentPlayground.tsx`

**Ubicación**: `dashboard/components/builder/AgentPlayground.tsx`

**Firma propuesta**:
```typescript
interface Message {
  id: string
  role: 'user' | 'agent'
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
}

interface ToolCall {
  name: string
  arguments: Record<string, unknown>
  status: 'pending' | 'success' | 'error'
}

interface AgentPlaygroundProps {
  agentRole: string  // rol del agente actual del formulario
  agentConfig?: AgentFormData  // optional: para validar que existe agente antes de enviar
}
```

**Patrones a seguir**:
- `AgentForm.tsx:59` — `useForm<AgentFormData>` para obtener `role` del formulario
- `TemplatePicker.tsx:88-89` — `useQuery` con `api.get()`
- `AgentForm.tsx:131-171` — `api.post()` con manejo de errores y `toast`

### Funciones/Clases nuevas

| Función | Archivo | Firma | Descripción |
|---|---|---|---|
| `AgentPlayground` | `AgentPlayground.tsx` | `(props: AgentPlaygroundProps) => JSX.Element` | Panel de chat con historial local |
| `sendMessage` | `AgentPlayground.tsx` | `(content: string) => Promise<void>` | Envía input a `POST /agents/{role}/run` |
| `pollTask` | `AgentPlayground.tsx` | `(taskId: string) => Promise<void>` | Polling a `GET /tasks/{task_id}` con interval |
| `ChatMessage` | `AgentPlayground.tsx` | `(msg: Message) => JSX.Element` | Renderiza un mensaje con tool calls colapsables |

### Imports necesarios
```typescript
import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { toast } from 'sonner'
import { ChevronDown, ChevronRight, Play } from 'lucide-react'
```

### Patrones existentes a copiar
- **`AgentForm.tsx:112-121`**: `useQuery` para cargar datos asíncronos
- **`AgentForm.tsx:131-171`**: `api.post()` con try/catch y `toast.error()`
- **`TemplatePicker.tsx:224-225`**: `LoadingSpinner` durante fetch

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints usados

**`POST /agents/{role}/run`** (`src/api/routes/agents.py:251-319`)
- Auth: `verify_org_membership` (JWT claims)
- Input: `RunAgentRequest(input_data: Dict[str, Any] = {})`
- Output: `RunAgentResponse(task_id: str, status: str)`
- Flujo: Crea task "pending" → background task ejecuta `BaseCrew.run_async()` → actualiza a "completed" con result y tokens_used o "failed" con error

**`GET /tasks/{task_id}`** (`src/api/routes/tasks.py:69-91`)
- Auth: `verify_org_membership`
- Input: `task_id` (UUID string)
- Output: `TaskResponse(task_id, org_id, flow_type, status, result, error, tokens_used, approval_required, approval_status, approval_payload, created_at, updated_at)`

### Contratos

**RunAgentRequest**:
```python
class RunAgentRequest(BaseModel):
    input_data: Dict[str, Any] = {}
```

**RunAgentResponse**:
```python
class RunAgentResponse(BaseModel):
    task_id: str
    status: str  # siempre "accepted"
```

**TaskResponse** (para polling):
```python
class TaskResponse(BaseModel):
    task_id: str
    org_id: str
    flow_type: str
    status: str  # pending | running | completed | failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0
    approval_required: bool = False
    approval_status: str = "none"
    approval_payload: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str
```

### Error handling

| Escenario | Backend responde | Frontend debe mostrar |
|---|---|---|
| Agent no existe | 404 "Agent '{role}' not found" | toast.error + deshabilitar playground |
| Task no existe (polling) | 404 "Task not found" | toast.error + stop polling |
| Task failed | status="failed", error=str(e) | Mostrar error en mensaje del agente |
| Timeout (no existe en backend) | — | Frontend: timeout 60s, then stop polling + toast |
| Auth fallida | 401/403 | redirect a login |

### Problema: `tool_calls` no disponibles

El `BaseCrew.get_last_tool_calls()` retorna `Dict[str, int]` (nombre → count), pero:
1. No se persiste a la tabla `tasks`
2. `TaskResponse` no incluye `tool_calls`
3. El plan pide "mostrar tool calls con nombre y argumentos"

**Solución requerida**: Nueva migración para agregar columna `tool_calls JSONB` a `tasks`. Modificar `agents.py:299-306` para guardar `crew.get_last_tool_calls()`.

**Alternativa simple**: Si no hay tiempo para migración, mostrar solo "X tool calls ejecutadas" sin detalle de argumentos.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

```
[User typed message]
       ↓
[AgentPlayground.sendMessage()]
       ↓
[POST /agents/{role}/run] → backend
       ↓ (202 Accepted)
[Task created: status="pending"]
       ↓
[BaseCrew.run_async() en background]
       ↓ (task status: running)
[Poolling: GET /tasks/{task_id} cada 2s]
       ↓
[Task completed: result + tokens_used]
       ↓
[Mostrar respuesta + tool calls + tokens]
```

### Integración en BuilderLayout

`AgentPlayground` debe integrarse como **tab** o **panel expandable** en el lado derecho (donde сейчас está `AgentForm`).

Opciones de UX:
1. **Tabs**: AgentForm | Playground (requires cambiar BuilderLayout a tabs)
2. **Panel expandible**: Botón "Test Agent" que abre Playground como Sheet/Dialog
3. **Split view**: Playground abajo del formulario (como consola integrada)

**Recomendación**: Opción 3 — split vertical en el panel derecho. Playground ocupa bottom 40%, AgentForm top 60%. Consistente con patrón de IDE/chat.

### Gaps encontrados

| Gap | Severity | Resolución |
|---|---|---|
| `tool_calls` no se persisten | Alta | Nueva migración + modificar agents.py |
| No hay columna `tokens_used` verificada en migrations | Media | Verificar/migrar |
| Timeout de polling no implementado | Baja | Agregar setTimeout 60s en frontend |
| No hay estado "agent no encontrado" en UI | Media | Verificar `role` existe antes de mostrar Playground |

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: FAP Agent Playground CLI
- **Qué automatiza:** Testing de agentes desde terminal sin UI
- **Tipo:** CLI command
- **Cómo se usa:** `fap agent test --role "CodeReviewer" --input "Review PR #123"`
- **Impacto para el usuario final:** No necesita abrir dashboard para probar agente rápido
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `tasks` tiene columna `tokens_used` (verificar migración existe)
✅ [DATA] Tabla `tasks` tiene columna `tool_calls JSONB` (nueva migración requerida)
✅ [CODE] `AgentPlayground.tsx` existe con interfaz: props `agentRole`, estado `messages[]`, handlers `sendMessage`, `pollTask`
✅ [CODE] `sendMessage()` llama `POST /agents/{role}/run` con `{input_data: {input: message}}`
✅ [CODE] `pollTask()` hace polling a `GET /tasks/{task_id}` cada 2s hasta status completed/failed/timeout
✅ [CODE] `ChatMessage` renderiza mensajes de usuario y agente con styling diferenciado
✅ [CODE] Tool calls se muestran colapsables (nombre + argumentos) si están disponibles
✅ [BACKEND] Endpoint `POST /agents/{role}/run` aceita `{input_data: {input: "..."}}`
✅ [BACKEND] Endpoint `GET /tasks/{task_id}` retorna `TaskResponse` con `tokens_used`
✅ [FULLSTACK] Playground integrado en BuilderLayout (sugerencia: split bottom 40%)
✅ [FULLSTACK] Indicador de loading mientras agent procesa (spinner + "Agent is thinking...")
✅ [FULLSTACK] Tokens consumidos visibles al finalizar (tomar de `TaskResponse.tokens_used`)
✅ [FULLSTACK] Historial local de mensajes durante sesión (useState, no persiste en DB)
✅ [FULLSTACK] Manejo de errores: agent no encontrado → toast + disabled playground
✅ [FULLSTACK] Timeout 60s en polling con feedback de expiración
✅ [DX] CLI `fap agent test` permite probar agente desde terminal
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `tokens_used` no existe en tabla tasks (migración faltante) | **Alta** | Migración 001 no tiene columna. Código la usa pero schema no la declara. | Verificar/migrar antes de implementar. Si no existe, crear migración. |
| `tool_calls` no disponibles en `TaskResponse` | **Alta** | Schema `tasks` no tiene columna. `BaseCrew._last_tool_calls` no se persiste. | Agregar columna `tool_calls JSONB` + modificar `agents.py` para persistir. Alternativa: mostrar solo count. |
| Polling infinito si agent se queda colgado | **Media** | Background task no responde. | Timeout 60s. Max 30 polls. Mostrar error si se excede. |
| Auth conflict: `verify_org_membership` vs `X-Org-ID` header | **Baja** | Endpoint usa JWT claims, no header. `api.ts` pasa ambos. | Funciona porque JWT contiene org_id. No acción requerida. |
| `result` es `str(result)` no JSON parseable | **Media** | `agents.py:303` hace `str(result)` — convierte CrewOutput a string | Post-MVP: persistir como JSON. MVP: mostrar como texto plano. |
| Tool calls con credenciales sensibles en logs | **Alta** | `str(result)` puede incluir tool arguments con secrets | No loguear tool args completos. Truncar en UI. |

---

## 7️⃣ Plan de Implementación

> [!CRITICAL]
> **Reglas de segmentación atómica — OBLIGATORIAS:**
> 1. **Una tarea = un artefacto**: un archivo, una función, una migración, un endpoint.
> 2. **Interfaz completa en la tarea**: cada tarea incluye la firma exacta.
> 3. **Patrón de referencia explícito**: indicar archivo concreto a copiar.
> 4. **Verificación inline**: cada tarea tiene `→ verificar:` con comando concreto.
> 5. **Test de atomicidad**: si implementador debe inferir algo → tarea incompleta.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: CLI `fap agent test` | `src/cli/commands/agent_test.py` | `def agent_test(role: str, input: str, org_id: str):` | `src/cli/commands/agent_create.py:30-134` | DX | Media | 1h | Ninguna | → verificar: `fap agent test --help` ejecuta sin errores |
| 1 | Migración: agregar `tokens_used` a tasks | `supabase/migrations/XXX_tasks_tokens_used.sql` | columna: `tokens_used INTEGER DEFAULT 0` | `supabase/migrations/004_agent_catalog.sql` | DATA | Baja | 0.5h | Ninguna | → verificar: `\d tasks` en Supabase SQL Editor muestra columna |
| 2 | Migración: agregar `tool_calls` a tasks | `supabase/migrations/XXX_tasks_tool_calls.sql` | columna: `tool_calls JSONB DEFAULT '{}'` | `supabase/migrations/004_agent_catalog.sql` | DATA | Baja | 0.5h | Tarea 1 | → verificar: `\d tasks` muestra columna tool_calls |
| 3 | Modificar `agents.py`: persistir tool_calls | `src/api/routes/agents.py` | En `agents.py:299-306`, agregar `tool_calls=crew.get_last_tool_calls()` al update | `src/api/routes/agents.py:299-306` | CODE | Baja | 0.5h | Tarea 2 | → verificar: `uv run ruff check src/api/routes/agents.py` sin errores |
| 4 | Crear `AgentPlayground.tsx` | `dashboard/components/builder/AgentPlayground.tsx` | `export function AgentPlayground({ agentRole }: { agentRole: string }): JSX.Element` | `dashboard/components/builder/AgentForm.tsx` (patrón useState + api.post) | CODE | Alta | 3h | Tareas 1-3 | → verificar: `npm run lint -- dashboard/components/builder/AgentPlayground.tsx` sin errores |
| 5 | Integrar Playground en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Agregar estado `activeTab: 'config' \| 'playground'` + renderizado condicional | `dashboard/components/builder/BuilderLayout.tsx:42-93` | FULLSTACK | Media | 1h | Tarea 4 | → verificar: `/builder` carga sin errores de render |
| 6 | Validar flujo end-to-end | — | — | — | FULLSTACK | Media | 1h | Tareas 1-5 | → verificar: Crear agente → enviar mensaje → ver respuesta + tokens |

**Tiempo total estimado:** 7.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- SSE/websocket para streaming de respuestas en vivo (en vez de polling)
- Persistir historial de chat en Supabase (`conversations` table ya existe — migración 007)
- Soporte para múltiples agentes en Playground (crew testing)
- Exportar conversación como markdown

---

## 🚫 Reglas de Oro (verificación)

- ✅ Análisis cubra TODO el paso (sub-pasos incluidos)
- ✅ ≥ 1 herramienta DX propuesta (`fap agent test` CLI)
- ✅ Discrepancias identificadas (D1: tool_calls, D2: tokens_used)
- ✅ Tareas atómicas (1 artefacto por tarea = 6 tareas)
- ✅ Interfaz exacta por tarea (firmas incluidas)
- ✅ Patrón de referencia explícito por tarea
- ✅ Verificación inline por tarea (comandos concretos)
- ⚠️ Suposiciones no verificadas: D2 (tokens_used migration) necesita verificarse contra Supabase real