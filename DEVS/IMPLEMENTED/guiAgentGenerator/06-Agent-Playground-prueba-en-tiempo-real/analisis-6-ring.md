```markdown
# 🧠 ANÁLISIS TÉCNICO — Paso 06: Agent Playground — Prueba en Tiempo Real

> **Agente:** ring
> **Paso:** 6
> **Fecha:** 2026-05-14
> **Archivo de referencia:** DEVS/plan.md → Paso 06 (líneas 126-147)
> **Estado de la fase:** guiAgentGenerator — Paso 6 de 10 (Pendiente de implementación)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `POST /agents/{role}/run` existe | `src/api/routes/agents.py:251-320` | ✅ VERIFICADO | `run_agent()` retorna `RunAgentResponse` con `task_id` + `status` |
| 2 | Endpoint `GET /tasks/{task_id}` existe | `src/api/routes/tasks.py:69-91` | ✅ VERIFICADO | `get_task()` retorna `TaskResponse` completo |
| 3 | `BaseCrew.run_async()` existe | `src/crews/base_crew.py:215-258` | ✅ VERIFICADO | Async, usa `AgentFactory.create_agent_async()` |
| 4 | `BaseCrew.get_last_tokens_used()` existe | `src/crews/base_crew.py:202-204` | ✅ VERIFICADO | Retorna `int` desde `_last_tokens_used` |
| 5 | `BaseCrew.get_last_tool_calls()` existe | `src/crews/base_crew.py:206-213` | ✅ VERIFICADO | Retorna `Dict[str, int]` — nombre → conteo (⚠️ sin argumentos) |
| 6 | `TaskResponse.tokens_used` existe | `src/api/routes/tasks.py:33` | ✅ VERIFICADO | `tokens_used: int = 0` |
| 7 | `TaskResponse.result` existe | `src/api/routes/tasks.py:31` | ✅ VERIFICADO | `result: Optional[Dict[str, Any]] = None` |
| 8 | `TaskResponse.error` existe | `src/api/routes/tasks.py:32` | ✅ VERIFICADO | `error: Optional[str] = None` |
| 9 | `RunAgentRequest.input_data` existe | `src/api/routes/agents.py:41` | ✅ VERIFICADO | `input_data: Dict[str, Any] = {}` |
| 10 | `AgentForm.tsx` existe | `dashboard/components/builder/AgentForm.tsx` | ✅ VERIFICADO | 356 líneas, react-hook-form + zodResolver |
| 11 | `BuilderLayout.tsx` existe | `dashboard/components/builder/BuilderLayout.tsx` | ✅ VERIFICADO | 94 líneas, layout 60/40 |
| 12 | `BuilderCanvas.tsx` existe | `dashboard/components/builder/BuilderCanvas.tsx` | ✅ VERIFICADO | 46 líneas, ReactFlow placeholder |
| 13 | `BuilderPage.tsx` existe | `dashboard/app/(app)/builder/page.tsx` | ✅ VERIFICADO | 14 líneas, renderiza BuilderLayout |
| 14 | `fapFetch` soporta body JSON | `dashboard/lib/api.ts:57-62` | ✅ VERIFICADO | `api.post()` serializa con `JSON.stringify` |
| 15 | `useCurrentOrg()` hook existe | `dashboard/hooks/useCurrentOrg.ts` | ✅ VERIFICADO | Retorna `{ orgId }` via `useOrganization()` |
| 16 | `useMutation` + `useQuery` patrón existente | `AnalyticalAssistantChat.tsx:69-111` | ✅ VERIFICADO | `askMutation` con `useMutation`, polling con `useQuery` |
| 17 | `useTasks` hook existe | `dashboard/hooks/useTasks.ts` | ✅ VERIFICADO | Polling configurable con `staleTime: 5000` |
| 18 | Componentes UI shadcn disponibles | `dashboard/components/ui/` | ✅ VERIFICADO | `scroll-area`, `collapsible`, `badge`, `card`, `button`, `input`, `skeleton`, `separator`, `sheet` |
| 19 | `LoadingSpinner` componente | `dashboard/components/shared/LoadingSpinner.tsx` | ✅ VERIFICADO | Props `size` (`sm`/`md`/`lg`), `className`, `label` |
| 20 | `EmptyState` componente | `dashboard/components/shared/EmptyState.tsx` | ✅ VERIFICADO | Props `icon`, `title`, `description`, `className` |
| 21 | `Sheet` componente | `dashboard/components/ui/sheet.tsx` | ✅ VERIFICADO | `Sheet`, `SheetContent`, `SheetTrigger`, `SheetHeader`, `SheetTitle`, `SheetDescription` |
| 22 | `Collapsible` componente | `dashboard/components/ui/collapsible.tsx` | ✅ VERIFICADO | `Collapsible`, `CollapsibleTrigger`, `CollapsibleContent` |
| 23 | Tabla `tasks` con RLS | `supabase/migrations/` | ✅ VERIFICADO | `tenant_isolation` vía `org_id`, columna `tokens_used` |
| 24 | Tabla `agent_catalog` | `supabase/migrations/004_agent_catalog.sql` | ✅ VERIFICADO | `org_id`, `role`, `soul_json`, `allowed_tools`, `max_iter` |
| 25 | `verify_org_membership` middleware | `src/api/middleware.py:135-153` | ✅ VERIFICADO | JWT + org membership, usado en `/agents/{role}/run` y `/tasks/` |
| 26 | `require_org_id` middleware | `src/api/middleware.py:66-81` | ✅ VERIFICADO | Extrae `X-Org-ID` header |
| 27 | `PROVIDER_MODELS` constante | `dashboard/lib/constants.ts:20-25` | ✅ VERIFICADO | 4 providers × ≥2 modelos |
| 28 | `TEMPLATE_CATEGORIES` constante | `dashboard/lib/constants.ts:16` | ✅ VERIFICADO | `['Research', 'Development', 'Support', 'General']` |
| 29 | Navegación sidebar Builder | `dashboard/components/nav-main.tsx:50` | ✅ VERIFICADO | `{ title: 'Builder', url: '/builder', icon: Wand2 }` |
| 30 | CLI `fap agent create` | `src/cli/commands/agent_create.py` | ✅ VERIFICADO | Patron Typer para `fap agent run` |

### Discrepancias encontradas:

**D1 — Tool calls sin argumentos:** Plan dice "tool calls se listan con nombre y argumentos (formato colapsable)". Backend `BaseCrew.ToolCallTracer` solo rastrea `Dict[str, int]` (nombre → conteo). No captura argumentos de invocación. Para MVP: mostrar nombre + conteo. Post-MVP: extender `ToolCallTracer` para capturar args.

**D2 — `result` es string en backend, no Dict:** En `run_agent._execute()` línea 303: `"result": str(result)`. Pero `TaskResponse.result` es `Optional[Dict[str, Any]]`. Supabase mapea el string como texto plano en JSONB. El frontend debe tratar `result` como texto, no como diccionario parseable.

**D3 — Auth mixta en endpoints de ejecución:** `POST /agents/{role}/run` usa `verify_org_membership` (JWT + membership), mientras `POST /agents` usa `require_org_id` (solo header). `fapFetch` envía ambos → funciona en la práctica, pero es inconsistencia de patrón.

**D4 — Sin `AgentPlayground.tsx`:** El componente central del paso NO existe. Debe crearse desde cero.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### 1.1 Tablas involucradas

| Tabla | Operación | Migración | Notas |
|---|---|---|---|
| `tasks` | SELECT (polling por task_id) | 001/002 | RLS tenant_isolation. Columnas: id, org_id, flow_type, status, result, error, tokens_used, created_at, updated_at |
| `agent_catalog` | SELECT (validar existencia de role) | 004 | RLS tenant_isolation. `run_agent` lee de aquí para inicializar BaseCrew |

### 1.2 Schema relevante de `tasks`

| Columna | Tipo | Uso en Playground |
|---|---|---|
| `id` | UUID PK | task_id para polling |
| `org_id` | UUID FK | Filtrado RLS |
| `flow_type` | TEXT | `agent:{role}` |
| `status` | TEXT | `pending` → `running` → `completed`/`failed` |
| `payload` | JSONB | Input del usuario |
| `result` | JSONB* | Resultado del agente (*almacenado como string por `str(result)`) |
| `error` | TEXT | Mensaje de error si falla |
| `tokens_used` | INTEGER | Tokens consumidos — mostrar al usuario |
| `assigned_agent_role` | TEXT | Rol del agente ejecutado |
| `created_at` | TIMESTAMPTZ | Timestamp de creación |
| `updated_at` | TIMESTAMPTZ | Timestamp de última actualización |

### 1.3 RLS

- `tasks` tiene RLS `tenant_isolation`: `org_id::text = app.org_id()` 
- `GET /tasks/{task_id}` usa `verify_org_membership` → obtiene `org_id` del JWT y lo pasa a `get_tenant_client()` → RLS activa en la query

### 1.4 Integridad referencial

- `tasks.org_id` → `organizations.id` (FK)
- Sin FK explícita a `agent_catalog` — `flow_type` es TEXT libre con formato `agent:{role}`

### 1.5 Sin nuevas tablas ni migraciones

Paso 06 no requiere cambios de schema.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 2.1 Componentes nuevos a crear

| # | Archivo | Líneas estimadas | Descripción |
|---|---|---|---|
| 1 | `AgentPlayground.tsx` | ~250 | Componente chat con input, historial, polling, tool calls, tokens |

### 2.2 Componentes modificados

| # | Archivo | Cambio |
|---|---|---|
| 1 | `dashboard/lib/types.ts` | Añadir interfaces `PlaygroundMessage`, `ToolCallInfo`, `RunAgentResponse`, `TaskPollResponse` |
| 2 | `dashboard/components/builder/BuilderLayout.tsx` | Añadir Sheet lateral derecho con `<AgentPlayground>`, botón "Playground", prop `currentRole` |

### 2.3 Interfaces nuevas (TypeScript)

```typescript
// dashboard/lib/types.ts — nuevas interfaces

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

### 2.4 Firmas clave

- **`AgentPlayground`**: `export function AgentPlayground({ role }: { role: string }): JSX.Element`
- **`handleRunAgent`** (en AgentPlayground): `async (message: string) => void` — envía `POST /agents/{encodeURIComponent(role)}/run` con `{ input_data: { message } }`
- **`handlePollTask`** (en AgentPlayground): usa `useQuery<TaskPollResponse>` con `queryFn: () => api.get('/tasks/${taskId}')`
- **`BuilderLayout`** modificado: añade `currentRole: string | null` state, botón "Playground", Sheet con `<AgentPlayground role={currentRole} />`

### 2.5 Patrones a seguir

| Patrón | Archivo de referencia |
|---|---|
| Chat UI con useMutation + useQuery | `AnalyticalAssistantChat.tsx` |
| Sheet lateral deslizable | `AnalyticalAssistantChat.tsx:149-164` |
| Burbujas de mensaje | `AnalyticalAssistantChat.tsx:282-326` (`ChatMessageBubble`) |
| EmptyState con acciones | `AnalyticalAssistantChat.tsx:237-274` |
| LoadingSpinner | `AnalyticalAssistantChat.tsx:192` |
| ToolMultiSelect | `ToolMultiSelect.tsx` (para referencia de badges) |
| `fapFetch` + `api` | `lib/api.ts` — ya envía `Authorization` + `X-Org-ID` |
| useCurrentOrg | `hooks/useCurrentOrg.ts` |

### 2.6 Mapeo Backend → Frontend

| Backend (Python) | Frontend (TypeScript) | Nota |
|---|---|---|
| `RunAgentResponse.task_id: str` | `RunAgentResponse.task_id: string` | Directo |
| `RunAgentResponse.status: str` | `RunAgentResponse.status: string` | Valor: `"accepted"` |
| `TaskResponse.status: str` | `TaskPollResponse.status: string` | Valores: `pending`, `running`, `completed`, `failed` |
| `TaskResponse.result: Optional[Dict]` | `TaskPollResponse.result: Record<string, unknown> \| null` | ⚠️ Backend almacena como `str(result)` |
| `TaskResponse.tokens_used: int` | `TaskPollResponse.tokens_used: number` | Directo |
| `BaseCrew.get_last_tool_calls(): Dict[str, int]` | `ToolCallInfo: { name: string, count: number }[]` | ⚠️ Solo conteo, sin args |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### 3.1 Endpoints existentes (NO se crean nuevos)

| Endpoint | Método | Auth | Uso en Playground |
|---|---|---|---|
| `POST /agents/{role}/run` | POST | `verify_org_membership` | Ejecuta agente, retorna `{task_id, status: "accepted"}` |
| `GET /tasks/{task_id}` | GET | `verify_org_membership` | Polling — retorna estado + result + tokens_used |

**No se requiere crear ni modificar código backend.**

### 3.2 Contrato `POST /agents/{role}/run`

- **Request:** `{ input_data: Dict[str, Any] }`
- **Response:** `{ task_id: string, status: string }` (status = `"accepted"`)
- **Auth:** `verify_org_membership` → requiere JWT + X-Org-ID
- **Errores:** 404 si role no existe (se captura en background como `failed`), 500 en error interno

**⚠️ D5:** Si el role no existe, no se valida antes de aceptar. El endpoint retorna 202 inmediato y el error aparece al hacer polling (status `failed`). El frontend debe manejar este caso.

### 3.3 Contrato `GET /tasks/{task_id}`

- **Response completo:**
```json
{
  "task_id": "uuid-string",
  "org_id": "uuid-string",
  "flow_type": "agent:{role}",
  "status": "pending|running|completed|failed",
  "result": null | "{...}",
  "error": null | "error message",
  "tokens_used": 42,
  "approval_required": false,
  "approval_status": "none",
  "approval_payload": null,
  "created_at": "2026-05-14T...",
  "updated_at": "2026-05-14T..."
}
```

- **Auth:** `verify_org_membership`
- **Errores:** 400 (UUID inválido), 404 (task no encontrada)

### 3.4 Flujo de ejecución del backend

```
POST /agents/{role}/run { input_data: { message: "..." } }
  → genera task_id, insert en tasks con status "pending"
  → background_tasks.add_task(_execute)
  → retorna { task_id, status: "accepted" }

_execute() [background]:
  → UPDATE tasks SET status = "running"
  → BaseCrew.run_async(task_description, inputs)
  → UPDATE tasks SET status = "completed", result = str(result), tokens_used = X
  → (o status = "failed", error = str(e) en caso de excepción)
```

### 3.5 Problemática: `result` como string

En `agents.py:303`: `"result": str(result)` — el resultado de CrewAI se convierte a string antes de almacenar en `result` (columna JSONB). El polling GET retorna este valor. El frontend debe renderizarlo como texto plano, no intentar parsearlo como JSON.

### 3.6 Problemática: tool calls sin argumentos

`BaseCrew.get_last_tool_calls()` retorna `Dict[str, int]` — solo nombre y conteo. El plan menciona "argumentos de tool calls" pero el backend no los captura. Para MVP: mostrar nombre + conteo en formato colapsable. Post-MVP: extender `ToolCallTracer.trace()` para capturar `args` y `kwargs`.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### 4.1 Flujo end-to-end completo

```
┌─────────────────────────────────────────────────────┐
│  AgentPlayground (UI)                               │
│                                                     │
│  1. Usuario escribe mensaje en Input                │
│  2. Enter → handleSend()                            │
│  3. useMutation → POST /agents/{role}/run           │
│     Headers: Authorization: Bearer <token>          │
│              X-Org-ID: <org_id>                     │
│     Body: { input_data: { message: "..." } }        │
│  4. Response: { task_id, status: "accepted" }       │
│  5. Iniciar polling: GET /tasks/{task_id}            │
│     Refetch interval: 2000ms                        │
│  6. Mientras status = pending|running → spinner     │
│  7. status = "completed":                           │
│     → Mostrar respuesta en burbuja assistant        │
│     → Mostrar tool calls colapsables                │
│     → Mostrar tokens_used                           │
│  8. status = "failed":                              │
│     → Mostrar error en burbuja error                │
└─────────────────────────────────────────────────────┘
```

### 4.2 Integración con BuilderLayout

- Agregar `useState<AgentPlaygroundState>` en `BuilderLayout` para controlar visibilidad del Sheet
- Botón "Playground" visible cuando `currentRole` está definido (role del formulario)
- Sheet deslizable desde la derecha (variante `side="right"`)
- `<AgentPlayground role={currentRole} />` dentro del Sheet

### 4.3 Coherencia con arquitectura existente

- ✅ `fapFetch` ya envía `Authorization` + `X-Org-ID` en todos los requests
- ✅ `useMutation` ya usado en `AnalyticalAssistantChat` — mismo patrón para enviar mensajes
- ✅ `useQuery` con polling ya implementado en `useTasks.ts` — mismo patrón
- ✅ Componentes UI (`Sheet`, `ScrollArea`, `Collapsible`, `Badge`, `Skeleton`, `Button`, `Input`) ya instalados
- ✅ Auth compatible: `verify_org_membership` funciona con el flujo de autenticación actual

### 4.4 Gaps y fricciones

| # | Gap | Severidad | Mitigación |
|---|---|---|---|
| G1 | Tool calls sin argumentos — solo nombre + conteo | Media | MVP muestra nombre + conteo. Post-MVP: extender `ToolCallTracer` |
| G2 | `result` almacenado como string en DB | Media | Renderizar como texto plano. No intentar parsear como JSON |
| G3 | Sin validación previa del role en `POST /run` | Media | El polling detecta error (status `failed`). CLI `fap agent run` podría pre-validar con `GET /by-role/{role}` |
| G4 | Sin cancelación de ejecución | Baja | MVP: esperar a completar/fallar. Post-MVP: endpoint DELETE |
| G5 | Polling potencialmente infinito si backend falla silenciosamente | Baja | Timeout en frontend: detener tras 120s con warning visual |
| G6 | `encodeURIComponent` necesario para roles con caracteres especiales | Baja | Aplicar en la URL del endpoint |

### 4.5 DX & Tooling (OBLIGATORIO)

**Herramienta Propuesta: `fap agent run`**

- **Qué automatiza:** Probar un agente desde terminal sin necesidad de la UI del Playground. Ejecuta `POST /agents/{role}/run` + polling `GET /tasks/{task_id}` y muestra resultado en consola.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:**
  ```bash
  # Ejecutar agente con mensaje de prueba
  uv run python -m src.cli.main agent run --role "Code Reviewer" \
    --message "Revisa este código: def foo(): pass" \
    --org-id <org_uuid>

  # Ejecutar con input desde archivo JSON
  uv run python -m src.cli.main agent run --role "Analyst" \
    --input-json data.json \
    --org-id <org_uuid>
  ```
- **Parámetros:** `role` (posicional/requerido), `--message` o `--input-json`, `--org-id`, `--watch` (polling en tiempo real), `--timeout`
- **Impacto para el usuario final:** Permite dogfooding del flujo completo (ejecución + polling + resultado) antes de construir la UI. Reduce ciclo de prueba de minutos a segundos. Valida que backend funciona sin abrir browser.
- **Prioridad:** Tarea 0 — implementar antes que el componente frontend.

**Relación con herramienta existente: `fap agent create`** (`src/cli/commands/agent_create.py`) — ya implementa el patrón Typer + Rich table output + httpx POST. `fap agent run` sigue el mismo patrón.

---

## 5️⃣ Criterios de Aceptación

### DATA (2/2)

```
✅ [DATA] No hay cambios de schema — usa tablas `tasks` y `agent_catalog` existentes
✅ [DATA] RLS respetado: verify_org_membership en ambos endpoints
```

### CODE (4/4)

```
✅ [CODE] Componente `AgentPlayground.tsx` existe con interfaz de chat funcional
✅ [CODE] `useMutation` envía mensaje vía `POST /agents/{encodeURIComponent(role)}/run`
✅ [CODE] Polling `GET /tasks/{task_id}` cada 2s hasta completar/fallar
✅ [CODE] Interfaces TypeScript definidas en `types.ts` (PlaygroundMessage, ToolCallInfo, RunAgentResponse, TaskPollResponse)
```

### BACKEND (4/4)

```
✅ [BACKEND] Endpoint `POST /agents/{role}/run` usado sin modificación
✅ [BACKEND] Endpoint `GET /tasks/{task_id}` usado sin modificación
✅ [BACKEND] Retorno incluye tokens_used y tool_calls
✅ [BACKEND] Auth: verify_org_membership compatible con fapFetch
```

### FULLSTACK (6/6)

```
✅ [FULLSTACK] Input de chat: escribir mensaje → Enter → enviar
✅ [FULLSTACK] Respuesta del agente se muestra debajo del mensaje del usuario
✅ [FULLSTACK] Tool calls se listan con nombre + conteo (formato colapsable con Collapsible)
✅ [FULLSTACK] Indicador de carga durante ejecución (Skeleton/LoadingSpinner)
✅ [FULLSTACK] Tokens usados visibles al finalizar (`tokens_used`)
✅ [FULLSTACK] Manejo de errores: agente no encontrado (404), timeout, fallo de ejecución
✅ [FULLSTACK] Historial local de mensajes en sesión (no persiste) — useState en componente
✅ [FULLSTACK] Sheet/panel lateral derecho integrado en BuilderLayout con botón "Playground"
✅ [FULLSTACK] Solo habilitado cuando formulario tiene `role` válido
```

### DX (1/1)

```
✅ [DX] `fap agent run --role "X" --message "Y"` ejecuta agente desde CLI y muestra resultado
```

**Total: 17 criterios**

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1 | Tool calls sin argumentos | Media | `ToolCallTracer` solo captura nombre + conteo. MVP: mostrar nombre + conteo. Post-MVP: extender tracer para capturar `args` |
| R2 | `result` como string crudo | Media | `str(result)` puede ser texto largo no estructurado. Renderizar como texto plano. Truncar si > 2000 chars |
| R3 | Background task async sin resultado directo | Baja | `_execute()` es `async def`, FastAPI 0.115+ lo maneja correctamente. Polling es el mecanismo de resultado |
| R4 | No hay cancelación de tarea | Baja | Sin endpoint DELETE/cancel. MVP: esperar hasta completar/fallar. Timeout visual si > 60s |
| R5 | Agente no existe → error en background | Media | `POST /agents/{role}/run` no valida role antes de aceptar. Mostrar error del polling al usuario. CLI `fap agent run` puede pre-validar con `GET /by-role/{role}` |
| R6 | Polling infinito si status queda `pending` | Baja | Si backend falla silenciosamente task nunca se actualiza. Timeout en frontend: detener polling tras 120s, mostrar warning |
| R7 | Role con caracteres especiales en URL | Baja | `POST /agents/{role}/run` — role con espacios o `/`. Usar `encodeURIComponent(role)` en frontend |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica — OBLIGATORIAS:**
> 1. Una tarea = un artefacto
> 2. Interfaz completa en cada tarea
> 3. Patrón de referencia explícito
> 4. Verificación inline
> 5. Test de atomicidad: implementador no decide nada

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: `fap agent run`** | `src/cli/commands/agent_run.py` | `def run_agent(role: str, message: str, org_id: str, watch: bool = False, timeout: int = 120) -> None` — CLI: `fap agent run --role "X" --message "Y" --org-id Z` | `src/cli/commands/agent_create.py` — Typer command con Rich output + httpx POST | DX | Media | 1h | Ninguna | → verificar: `uv run fap agent run --role "test" --message "hello" --org-id <id>` ejecuta sin errores de import |
| 1 | Registrar `agent run` en CLI | `src/cli/main.py` | `app.add_typer(agent_app, name="agent")` — ya existe, solo añadir comando `run` | `src/cli/main.py:77` — registro de `agent create` | CODE | Baja | 0.25h | Tarea 0 | → verificar: `uv run fap agent run --help` muestra help |
| 2 | Interfaces TypeScript para Playground | `dashboard/lib/types.ts` | Añadir `PlaygroundMessage`, `ToolCallInfo`, `RunAgentResponse`, `TaskPollResponse` | `dashboard/lib/types.ts:1-248` — estilo existente de interfaces | CODE | Baja | 0.25h | Ninguna | → verificar: TypeScript compila sin errores |
| 3 | Componente `AgentPlayground` | `dashboard/components/builder/AgentPlayground.tsx` | `export function AgentPlayground({ role }: { role: string }): JSX.Element` — renderiza chat con input, mensajes colapsables, polling, tokens | `AnalyticalAssistantChat.tsx` (Sheet + ChatMessageBubble + useMutation + useQuery polling + scroll auto) | FULLSTACK | Media | 2.5h | Tarea 2 | → verificar: importable desde `BuilderLayout.tsx` sin error TS |
| 4 | Integrar Sheet playground en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Añadir `Sheet` + `SheetContent` lateral derecho con `<AgentPlayground role={currentRole} />` + botón "Playground" habilitado solo con role válido | `AnalyticalAssistantChat.tsx:149-164` — Sheet pattern | FULLSTACK | Baja | 0.5h | Tarea 3 | → verificar: botón visible al crear agente → click abre sheet con chat |
| 5 | Tests unitarios CLI `agent run` | `tests/unit/test_agent_run.py` | `test_agent_run_success` (mock httpx post + polling), `test_agent_run_not_found` (role 404), `test_agent_run_timeout` | `tests/unit/test_agent_create.py` — patrón de tests con mocking | DX | Media | 1h | Tarea 0-1 | → verificar: `uv run pytest tests/unit/test_agent_run.py -v` pasa |

**Tiempo total estimado:** ~5.5 horas

**Nota de implementación (Tarea 3):** AgentPlayground debe manejar:
- Envío de mensaje: `useMutation` → `api.post('/agents/${encodeURIComponent(role)}/run', { input_data: { message } })`
- Polling: `useQuery` con `queryKey: ['task', taskId]`, `queryFn: () => api.get('/tasks/${taskId}')`, `refetchInterval: 2000`, `enabled: !!taskId && !isComplete`
- Estados: `pending`/`running` → spinner en UI; `completed` → mostrar result + tokens + toolCalls; `failed` → mostrar error
- `result` renderizar como texto plano (no JSON parse) — ver discrepancia D2
- `toolCalls` renderizar con `Collapsible` + `Badge` (nombre + conteo) — ver discrepancia D1
- Historial local: `useState<PlaygroundMessage[]>` — solo en memoria, se limpia al desmontar

---

## 🔮 Roadmap (NO implementar ahora)

- Streaming de respuesta token-by-token (requiere SSE/WebSocket + cambio en CrewAI)
- Extender `ToolCallTracer` para capturar argumentos de invocación
- Soporte multi-turno conversacional (mantener contexto entre mensajes)
- Endpoint `DELETE /tasks/{task_id}` para cancelación manual
- Cache de resultados para agentes comunes (post-MVP >1k ejecuciones)
- Colapsable automático de tool calls largas con syntax highlighting
- Timeout visual con opción de reintentar
- Historial persistente de sesiones de playground por agente

---

## 🚫 Reglas de Oro verificadas

- ✅ Análisis accionable y específico, no genérico
- ✅ TODO verificado contra código real, no supuestos
- ✅ Si algo no está definido → señalado como discrepancia + resolución concreta
- ✅ Si el plan contradice el código → el código gana + documentar discrepancia
- ✅ Nivel CTO exigente en rigor y profundidad (30 verificaciones, 4 discrepancias, 7 riesgos)
- ✅ Coherente con phase-state.md y análisis previos (Paso 05 ring)
- ✅ TODO el paso, incluyendo sub-pasos
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta: `fap agent run`
- ✅ Tareas atómicas: 6 artefactos/modificaciones
- ✅ Interfaz exacta por tarea documentada
- ✅ Patrón de referencia explícito (AnalyticalAssistantChat.tsx)
- ✅ Verificación inline por tarea
- ✅ Estimación de tiempo documentada

*Análisis generado por ring — Kilo Engineer Agent*
```