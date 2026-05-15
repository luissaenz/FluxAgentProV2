# Análisis Técnico — Paso 06: Agent Playground — prueba en tiempo real

> **Agente:** glm5.1  
> **Paso:** 06 — Agent Playground  
> **Fecha:** 2026-05-14  
> **Referencia:** `DEVS/plan.md` líneas 126-147  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `POST /agents/{role}/run` existe | `verify_org_membership` + `BackgroundTasks` | ✅ | `agents.py:251-320` — endpoint funcional, retorna `{task_id, status}` |
| 2 | `GET /tasks/{task_id}` existe | `verify_org_membership`, retorna `TaskResponse` | ✅ | `tasks.py:69-91` — polling endpoint funcional |
| 3 | `TaskResponse.tokens_used` existe | Campo en Pydantic model | ✅ | `tasks.py:32` — `tokens_used: int = 0` |
| 4 | `RunAgentRequest.input_data` existe | Campo Pydantic | ✅ | `agents.py:41` — `input_data: Dict[str, Any] = {}` |
| 5 | `BaseCrew.run_async()` existe | Método async con token tracking | ✅ | `base_crew.py:215-258` — ejecuta agente async |
| 6 | `BaseCrew.get_last_tokens_used()` existe | Retorna tokens post-ejecución | ✅ | `base_crew.py:202-204` |
| 7 | `BaseCrew.get_last_tool_calls()` existe | Retorna dict `{tool_name: count}` | ✅ | `base_crew.py:206-213` |
| 8 | Tabla `tasks` con columna `tokens_used` | Migración 002 añade columna | ✅ | `002_governance.sql:28` — `tokens_used INTEGER DEFAULT 0` |
| 9 | `TaskResponse` incluye `result` | Campo `Optional[Dict[str, Any]]` | ✅ | `tasks.py:31` — `result: Optional[Dict[str, Any]] = None` |
| 10 | `TaskResponse` incluye `error` | Campo `Optional[str]` | ✅ | `tasks.py:32` — `error: Optional[str] = None` |
| 11 | `BuilderLayout.tsx` existe | Layout split 60/40 | ✅ | `BuilderLayout.tsx:56-93` — orquesta AgentForm + TemplatePicker |
| 12 | `AgentForm.tsx` existe | Formulario react-hook-form + zod | ✅ | Completamente implementado Paso 04 |
| 13 | `api.post()` soporta body JSON | `fapFetch` con JSON.stringify | ✅ | `api.ts:57-62` |
| 14 | `useCurrentOrg()` hook existe | Retorna `{ orgId }` | ✅ | `useCurrentOrg.ts` |
| 15 | Plan dice "tool calls ejecutadas con nombre y argumentos" | `_execute()` no guarda argumentos de tool calls, solo nombres + conteo | ❌ DISCREPANCIA | `base_crew.py:163` → `_last_tool_calls: Dict[str, int]` solo cuenta, no args |
| 16 | Plan dice "conectar con `POST /agents/{role}/run`" | El plan usa `/agents/{role}/run` pero el endpoint real usa `verify_org_membership` (no `require_org_id`) | ⚠️ NO VERIFICABLE en frontend | `agents.py:256` — auth distinta a otros endpoints |
| 17 | `tasks` tabla tiene `status` con valores `pending/running/completed/failed` | Status intermediosTEXT | ✅ | `001_set_config_rpc.sql:66`, backend los usa |
| 18 | `fapFetch` maneja errores con `Error` | Lanza `Error` con message | ✅ | `api.ts:38-49` |
| 19 | `useMutation` usado en dashboard | Patrón establecido en AnalyticalChat + useTickets | ✅ | `AnalyticalAssistantChat.tsx:69-111`, `useTickets.ts` |
| 20 | Componentes UI disponibles: `scroll-area`, `collapsible`, `badge`, `card`, `button`, `input`, `skeleton`, `separator`, `accordion` | shadcn/ui instalados | ✅ | `dashboard/components/ui/` |
| 21 | Plan dice "historial local de mensajes durante la sesión (no persiste)" | No hay endpoint de historial de chat por agente — correcto, es local | ✅ | Decisión de diseño: solo en memoria |
| 22 | `GET /tasks/{task_id}` usa `verify_org_membership` | Requiere JWT válido + org membership | ✅ | `tasks.py:72` |
| 23 | `_execute()` en `run_agent` es async pero se via `BackgroundTasks` | FastAPI `BackgroundTasks.add_task()` requiere sync callable, pero `_execute` es `async def` | ❌ DISCREPANCIA | `agents.py:282-318` — `_execute` es `async def` + `background_tasks.add_task()`. FastAPI no maneja async en background tasks correctamente sin `asyncio` |
| 24 | `ScrollArea` componente disponible | shadcn/ui | ✅ | `dashboard/components/ui/scroll-area.tsx` |
| 25 | `Collapsible` componente disponible | shadcn/ui | ✅ | `dashboard/components/ui/collapsible.tsx` |

### Discrepancias encontradas

**D1 — Tool calls sin argumentos:** Plan dice "tool calls se listan con nombre y argumentos (formato colapsable)". Backend `BaseCrew.ToolCallTracer` solo rastrea `Dict[str, int]` (nombre → conteo). No existen argumentos de invocación. Necesario: extender `ToolCallTracer` para capturar argumentos O limitar UI a mostrar solo nombre + conteo (MVP).

**D2 — Background async task:** `_execute()` en `agents.py:282` es `async def` pero se añade vía `background_tasks.add_task(_execute)` (sin `await`). FastAPI 0.115+ soporta async background tasks vía `add_task`, pero no espera el resultado — correcto para nuestro caso (polling vía `GET /tasks/{task_id}`). Verificado: Pydantic v2 + FastAPI 0.115+ maneja `async def` en background correctamente.

**D3 — `verify_org_membership` vs `require_org_id`:** Endpoint `POST /agents/{role}/run` usa `verify_org_membership` (requiere JWT + org membership completo), mientras `POST /agents` usa `require_org_id` (solo header). Frontend `fapFetch` ya envía `Authorization: Bearer` + `X-Org-ID` → ambos funcionan. Sin discrepancia real, solo estilos de auth distintos.

**D4 — `result` campo es `str` en backend, no `Dict`:** En `run_agent._execute()` línea 303: `"result": str(result)`. Pero `TaskResponse.result` es `Optional[Dict[str, Any]]`. Si la ejecución completa, se guarda `str(result)` — que Supabase mapea como texto plano en JSONB. El polling GET retorna este valor como `result`. El frontend debe parsear `result` que puede ser string, no diccionario.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema: Sin cambios necesarios

Paso 06 no crea tablas nuevas ni modifica migraciones. Usa:
- `tasks` — ya existe (mig 001 + 002)
- `agent_catalog` — ya existe (mig 004)

### Columnas relevantes de `tasks`

| Columna | Tipo | Uso en Playground |
|---|---|---|
| `id` | UUID PK | task_id para polling |
| `org_id` | UUID FK | Filtrado RLS |
| `flow_type` | TEXT | Será `agent:{role}` |
| `status` | TEXT | `pending` → `running` → `completed`/`failed` |
| `payload` | JSONB | Input del usuario (`input_data`) |
| `result` | JSONB | String del resultado del agente (⚠️ ver D4) |
| `error` | TEXT | Mensaje de error si falla |
| `tokens_used` | INTEGER | Tokens consumidos — mostrar al usuario |
| `assigned_agent_role` | TEXT | Rol del agente asignado |
| `correlation_id` | TEXT | ID de correlación |
| `created_at` | TIMESTAMPTZ | Timestamp de creación |
| `updated_at` | TIMESTAMPTZ | Timestamp de última actualización |

### RLS
- `tasks` tiene RLS `tenant_isolation` (ver mig 001/004) → requiere `app.org_id` seteado vía `TenantClient`.
- `GET /tasks/{task_id}` usa `verify_org_membership` que no usa `TenantClient` sino `get_tenant_client` con `execute_with_retry` (línea 84-86) → RLS activa.

### Integridad referencial
- `tasks.org_id` → `organizations.id` (FK)
- Sin FK a `agent_catalog` — `assigned_agent_role` es TEXT libre.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos

#### `AgentPlayground.tsx`
- **Tipo:** Componente React `'use client'`
- **Dependencias:** `useMutation`, `useQuery`, `useState`, `useRef`, `useEffect` de React + `@tanstack/react-query`
- **Props sugeridas:** Ninguna (integra con `AgentForm` vía `BuilderLayout`)
- **Estado local:**
  - `messages: PlaygroundMessage[]` — historial de chat
  - `input: string` — texto del input
  - `currentTaskId: string | null` — task en ejecución

- **Interfaces nuevas:**

```typescript
interface PlaygroundMessage {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  toolCalls?: ToolCallInfo[]
  tokensUsed?: number
  timestamp: Date
}

interface ToolCallInfo {
  name: string
  count: number
}

interface RunAgentResponse {
  task_id: string
  status: string
}

interface TaskPollResponse {
  task_id: string
  org_id: string
  flow_type: string
  status: string
  result: Record<string, unknown> | null
  error: string | null
  tokens_used: number
  approval_required: boolean
  approval_status: string
  approval_payload: Record<string, unknown> | null
  created_at: string
  updated_at: string
}
```

- **Patrón a seguir:** `AnalyticalAssistantChat.tsx` — chat UI con `useMutation` + polling + mensajes locales + scroll automático.

### Patrón de polling

```typescript
// Polling: cada 2s mientras status sea 'pending' o 'running'
const { data: taskData } = useQuery<TaskPollResponse>({
  queryKey: ['task', currentTaskId],
  queryFn: () => api.get(`/tasks/${currentTaskId}`),
  enabled: !!currentTaskId && !isComplete,
  refetchInterval: isComplete ? false : 2000,
})
```

### Integración con `BuilderLayout`

El plan dice "Añadir panel de chat" — pero no especifica dónde. Dos opciones:

1. **Dentro de `BuilderLayout`** como reemplazo del canvas cuando se prueba un agente (tab/panel lateral)
2. **Como Sheet/Dialog** que aparece encima del builder

Decisión de MVP: **Sheet lateral derecho** (similar a AnalyticalAssistantChat) — consistente con patrón existente. Se integra en `BuilderLayout` con botón "Playground" junto a "Templates".

### Función `handleRunAgent`

Flujo:
1. Usuario escribe mensaje en input
2. `useMutation` llama `POST /agents/{role}/run` con `{ input_data: { message: "..." } }`
3. Recibe `{ task_id, status }` → iniciar polling
4. Polling `GET /tasks/{task_id}` cada 2s
5. Cuando `status === 'completed'` → agregar respuesta al chat, mostrar tokens_used
6. Cuando `status === 'failed'` → mostrar error

### TypeScript types necesarios

Extender `types.ts` con las interfaces `PlaygroundMessage`, `ToolCallInfo`, `RunAgentResponse`, `TaskPollResponse` — o definir inline en AgentPlayground.tsx (decisión: inline para MVP, migrar a `types.ts` post-MVP).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes (NO se crean nuevos)

| Endpoint | Método | Auth | Uso |
|---|---|---|---|
| `POST /agents/{role}/run` | POST | `verify_org_membership` | Ejecutar agente, recibe `task_id` |
| `GET /tasks/{task_id}` | GET | `verify_org_membership` | Polling de estado y resultado |

**No se requiere crear endpoints nuevos.** El backend ya tiene todo lo necesario.

### Contrato `POST /agents/{role}/run`

- **Request:** `{ input_data: Dict[str, Any] }` — plan dice "enviar mensaje al agente"
- **Response:** `{ task_id: string, status: string }` — status siempre `"accepted"`
- **Errores:** 404 si role no existe (implícito en `BaseCrew._load_agent_config()` → `CrewConfigError` no capturado resulta en 500)

⚠️ **D5 — Error handling en `run_agent`:** Si `role` no existe en `agent_catalog`, `CrewConfigError` se lanza dentro de `_execute()` (background) → se captura como error genérico en `except Exception` → status `failed` con error message. **Pero** el endpoint `POST /agents/{role}/run` retorna 202 inmediatamente sin validar que el role exista. El usuario ve "accepted" y luego descubre por polling que falló.

### Contrato `GET /tasks/{task_id}`

- **Response:** `TaskResponse` con todos los campos
- **Auth:** `verify_org_membership` — JWT + org membership
- **Errores:** 400 (invalid UUID), 404 (task not found)

### Flujo de datos completo

```
Frontend (AgentPlayground)
  → POST /agents/{role}/run { input_data: { message: "..." } }
  → { task_id: "...", status: "accepted" }
  → Polling GET /tasks/{task_id} (cada 2s)
  → { status: "running", ... }
  → ... polling ...
  → { status: "completed", result: "...", tokens_used: 42 }
  → Mostrar resultado al usuario
```

### Problemática: `input_data` del agente

El `BaseCrew.run_async()` recibe `task_description` + `inputs`. El endpoint `POST /agents/{role}/run` pasa `request.input_data` como `inputs` y hardcodea `task_description="Execute assigned task"` (línea 295).

Para un playground conversacional, necesitamos al menos pasar el mensaje del usuario como `inputs`. El endpoint ya lo soporta: `input_data` es un dict libre que se pasa como `inputs` a `crew.kickoff_async()`.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
Usuario escribe mensaje → AgentPlayground
  → POST /agents/{encodeURIComponent(role)}/run
    Headers: Authorization + X-Org-ID
    Body: { input_data: { message: "..." } }
  → Recibe task_id
  → Polling GET /tasks/{task_id} cada 2s
  → status === "completed":
    → Extraer result, tokens_used
    → Mostrar en chat
  → status === "failed":
    → Mostrar error
```

### Coherencia con arquitectura existente

- ✅ `fapFetch` ya envía `Authorization` + `X-Org-ID`
- ✅ `useMutation` ya usado en AnalyticalChat — mismo patrón
- ✅ `useQuery` con polling estándar — `refetchInterval`
- ✅ Componentes UI disponibles: `ScrollArea`, `Collapsible`, `Badge`, `Input`, `Button`, `Skeleton`
- ✅ Auth compatible: `verify_org_membership` funciona con `fapFetch`

### Gaps

1. **Tool calls sin argumentos** — `BaseCrew.get_last_tool_calls()` retorna `{name: count}`, no args. El plan dice "nombre y argumentos (formato colapsable)". Para MVP: mostrar solo nombre + conteo. Post-MVP: extender `ToolCallTracer` para capturar args.

2. **`result` como string** — `str(result)` puede ser texto largo del agente. Parsear como texto plano, no como JSON.

3. **Role del agente dinámicamente** — El playground necesita saber qué agente se está probando. El `AgentForm` ya tiene el campo `role`. Integración: al guardar el agente (o al tener un `role` válido en el formulario), habilitar el botón "Playground".

4. **Cancelar ejecución** — No existe endpoint `DELETE /tasks/{task_id}` ni `POST /tasks/{task_id}/cancel`. Para MVP: polling hasta completar o fallar. Post-MVP: cancelación manual.

5. **Accesibilidad del playground** — El plan dice "panel de chat para probar un agente". No especifica SIEMPRE está visible o se abre bajo demanda. Decisión: Sheet deslizable desde la derecha (como AnalyticalChat), activado por botón "Playground" en BuilderLayout.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: `fap agent run`
- **Qué automatiza:** Probar un agente desde terminal sin UI. Dogfooding del endpoint POST /agents/{role}/run + polling GET /tasks/{task_id}.
- **Tipo:** CLI command
- **Cómo se usa:** `fap agent run --role "Code Reviewer" --message "Review this code" --org-id <org_id>`
- **Impacto para el usuario final:** Valida que el flujo run→poll→result funciona antes de construir UI. debugging rápido sin abrir browser.
- **Prioridad:** Tarea 0 — implementar antes que el componente frontend.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Sin cambios de schema — usa `tasks` y `agent_catalog` existentes
✅ [CODE] Componente `AgentPlayground.tsx` existe con interfaz de chat funcional
✅ [CODE] `useMutation` envía mensaje vía `POST /agents/{role}/run`
✅ [CODE] Polling `GET /tasks/{task_id}` cada 2s hasta completar/fallar
✅ [BACKEND] Endpoint `POST /agents/{role}/run` usado sin modificación
✅ [BACKEND] Endpoint `GET /tasks/{task_id}` usado sin modificación
✅ [FULLSTACK] Input de chat: escribir mensaje → Enter → enviar
✅ [FULLSTACK] Respuesta del agente se muestra debajo del mensaje del usuario
✅ [FULLSTACK] Tool calls se listan con nombre + conteo (formato colapsable)
✅ [FULLSTACK] Indicador de carga durante ejecución (spinner/skeleton)
✅ [FULLSTACK] Tokens usados visibles al finalizar (`tokens_used`)
✅ [FULLSTACK] Manejo de errores: agente no encontrado, timeout, fallo
✅ [FULLSTACK] Historial local de mensajes en sesión (no persiste)
✅ [FULLSTACK] Sheet/panel integrado en BuilderLayout con botón "Playground"
✅ [FULLSTACK] Solo habilitado cuando formulario tiene `role` válido
✅ [DX] `fap agent run` ejecuta agente desde CLI y muestra resultado
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tool calls sin argumentos | Media | `ToolCallTracer` solo captura nombre+conteo, no args | MVP: mostrar nombre + conteo. Post-MVP: extender tracer |
| `result` es string crudo | Media | `str(result)` en `run_agent._execute()` puede ser texto largo no estructurado | Parsear como texto plano en frontend. Truncar si > 2000 chars |
| Background task async | Baja | `_execute()` es `async def` en `BackgroundTasks.add_task()` | FastAPI 0.115+ lo maneja correctamente (verificado) |
| No hay cancelación de tarea | Baja | Sin endpoint DELETE/cancel | MVP: esperar hasta completar. Timeout visual si > 60s |
| Agente no existe → error en background | Media | `POST /agents/{role}/run` no valida role antes de aceptar | Mostrar error del polling al usuario. CLI `fap agent run` valida primero |
| Polling infinito | Baja | Si status queda en `pending` por bug del backend | Timeout en frontend: detener polling tras 120s, mostrar warning |
| Role con caracteres especiales en URL | Baja | `POST /agents/{role}/run` — role con espacios o `/` | `encodeURIComponent(role)` en frontend |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: `fap agent run`** | `src/cli/commands/agent_run.py` | `def run_agent(role: str, message: str, org_id: str) -> None` — CLI: `fap agent run --role "X" --message "Y" --org-id Z` | `src/cli/commands/agent_create.py` — Typer command con Rich output | DX | Media | 1h | Ninguna | → verificar: `uv run fap agent run --role "test" --message "hello" --org-id <id>` ejecuta sin errores de import |
| 1 | Registrar `agent run` en CLI | `src/cli/main.py` | `app.add_typer(agent_app, name="agent")` — ya existe, solo añadir comando `run` | `src/cli/main.py:77` — registro de `agent create` | CODE | Baja | 0.25h | Tarea 0 | → verificar: `uv run fap agent run --help` muestra help |
| 2 | Crear interfaz `PlaygroundMessage` | `dashboard/components/builder/AgentPlayground.tsx` (inline types) | `interface PlaygroundMessage { id: string; role: 'user' \| 'assistant' \| 'error'; content: string; toolCalls?: { name: string; count: number }[]; tokensUsed?: number; timestamp: Date; }` | `dashboard/components/analytical/AnalyticalAssistantChat.tsx:32-38` — `ChatMessage` interface | CODE | Baja | 0.25h | Ninguna | → verificar: TypeScript compila sin errores |
| 3 | Componente `AgentPlayground` — chat UI | `dashboard/components/builder/AgentPlayground.tsx` | `export function AgentPlayground({ role }: { role: string }): JSX.Element` — renderiza chat con input, mensajes, y polling | `dashboard/components/analytical/AnalyticalAssistantChat.tsx` — Sheet + chat UI + useMutation + scroll | CODE | Media | 2h | Tarea 2 | → verificar: importable desde `BuilderLayout.tsx` sin error TS |
| 4 | Integrar `Sheet` en `BuilderLayout` | `dashboard/components/builder/BuilderLayout.tsx` | Añadir `Sheet` + `SheetContent` lateral derecho con `<AgentPlayground role={currentRole} />` + botón "Playground" | `AnalyticalAssistantChat.tsx:149-164` — Sheet pattern | CODE | Baja | 0.5h | Tarea 3 | → verificar: botón "Playground" visible en Builder → click abre sheet con chat |
| 5 | Lógica de envío `POST /agents/{role}/run` | `dashboard/components/builder/AgentPlayground.tsx` | `useMutation({ mutationFn: (msg: string) => api.post(\`/agents/${encodeURIComponent(role)}/run\`, { input_data: { message: msg } }) })` | `AnalyticalAssistantChat.tsx:69-111` — `askMutation` pattern | BACKEND | Media | 1h | Tarea 3 | → verificar: enviar mensaje → recibe `{ task_id, status }` sin error |
| 6 | Lógica de polling `GET /tasks/{task_id}` | `dashboard/components/builder/AgentPlayground.tsx` | `useQuery<TaskPollResponse>({ queryKey: ['task', taskId], queryFn: () => api.get(\`/tasks/${taskId}\`), enabled: !!taskId && !isComplete, refetchInterval: 2000 })` | `dashboard/hooks/useTasks.ts` — `useQuery` con `staleTime` | BACKEND | Media | 0.5h | Tarea 5 | → verificar: polling retorna status `completed` o `failed` correctamente |
| 7 | Renderizado de mensajes + tool calls + tokens | `dashboard/components/builder/AgentPlayground.tsx` | Función `renderMessage(msg: PlaygroundMessage)` → devuelve JSX con bubbles, tool calls colapsables (Collapsible), badge de tokens | `AnalyticalAssistantChat.tsx:282-326` — `ChatMessageBubble` | FULLSTACK | Media | 1h | Tarea 6 | → verificar: mensaje del usuario se muestra como bubble, respuesta con tool calls colapsable y tokens |
| 8 | Manejo de errores + estados vacíos + loading | `dashboard/components/builder/AgentPlayground.tsx` | Loading: `<LoadingSpinner />` durante polling. Error: bubble rojo con mensaje. Vacío: `<EmptyState />` con texto "Send a message to test your agent" | `AnalyticalAssistantChat.tsx:237-274` — `EmptyState` + error handling | FULLSTACK | Baja | 0.5h | Tarea 7 | → verificar: estados loading/error/empty renderizan correctamente |
| 9 | Validación: role requerido para habilitar Playground | `dashboard/components/builder/BuilderLayout.tsx` | Botón "Playground" `disabled={!currentRole}` — role viene de `AgentForm` | `AgentForm.tsx:132-170` — validación existente | FULLSTACK | Baja | 0.25h | Tarea 4 | → verificar: sin role → botón deshabilitado con tooltip |
| 10 | Tests unitarios CLI `agent run` | `tests/unit/test_agent_run.py` | Test: `test_agent_run_success` (mock `api.post` + polling), `test_agent_run_not_found` (role inexistente), `test_agent_run_timeout` | `tests/unit/test_bundle_export.py` — patrón de tests con mocking | FULLSTACK | Media | 1h | Tarea 0-1 | → verificar: `uv run pytest tests/unit/test_agent_run.py -v` pasa |

**Tiempo total estimado:** 8 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Extender `ToolCallTracer`** para capturar argumentos de invocación → mostrar en Playground
- **Endpoint `DELETE /tasks/{task_id}`** para cancelación manual de tareas en ejecución
- **WebSockets/SSE** para reemplazar polling → latencia reducida
- **Historial persistente** de sesiones de playground por agente
- **Streaming de respuesta** token-by-token (requiere cambio en CrewAI/BaseCrew)
- **Soporte multi-turno** conversacional (mantener contexto entre mensajes)
- **Colapsable automático** de tool calls largas con syntax highlighting
- **Timeout visual** con opción de reintentar