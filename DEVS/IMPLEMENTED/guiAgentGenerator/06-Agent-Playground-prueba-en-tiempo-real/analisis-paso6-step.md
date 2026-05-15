# Análisis Paso 06 — Agent Playground (step)
**Fecha:** 2026-05-14  
**Agente:** step  
**Fase:** guiAgentGenerator  
**Estado phase-state.md:** Paso 06 Pendiente  
**Criterios plan.md:** §126-147 (9 tareas + 6 criterios)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `POST /agents/{role}/run` existe | `src/api/routes/agents.py:251-320` | ✅ | `RunAgentResponse` + `BackgroundTasks` |
| 2 | `GET /tasks/{task_id}` existe | `src/api/routes/tasks.py:69-91` | ✅ | `TaskResponse` con `tokens_used` |
| 3 | Tabla `tasks` con `tokens_used` | `supabase/migrations/002_governance.sql:28` | ✅ | `ADD COLUMN ... tokens_used INTEGER DEFAULT 0` |
| 4 | Tabla `tasks` RLS policy | `supabase/migrations/001_set_config_rpc.sql:106-108` | ✅ | `USING (org_id::text = current_org_id())` |
| 5 | `api.post()` helper | `dashboard/lib/api.ts:54-62` | ✅ | `fapFetch` con headers JWT + X-Org-ID |
| 6 | `AgentForm` completo | `dashboard/components/builder/AgentForm.tsx` | ✅ | 11 campos + zod validación |
| 7 | `BuilderLayout` estructura | `dashboard/components/builder/BuilderLayout.tsx:56-79` | ✅ | Split 60% canvas / 40% form |
| 8 | Componentes UI existentes | `Card`, `CodeBlock`, `StatusLabel`, `LoadingSpinner` | ✅ | `components/ui/`, `components/shared/` |
| 9 | Pattern pollingUseQuery | `hooks/useApprovals.ts` | ✅ | React Query pattern en dashboard |
| 10 | Tipo `Task` | `dashboard/lib/types.ts:1-24` | ✅ | `TaskStatus` union + `result: Record | null` |

**Discrepancias encontradas:**

| ID | Descripción | Plan vs Realidad | Resolución |
|---|---|---|---|
| D1 | Plan menciona `TaskResponse.tokens_used` como campo obligatorio. Plan: ✓ coincide. Realidad: ✓ existe en tasks.py:34 pero types.ts NO incluye `tokens_used`. | `types.ts` desactualizado | Extender `Task` interface local en componente (no global) para evitar touches fuera de paso |
| D2 | Plan espera que `result` contenga tool calls detalladas. Realidad: `BaseCrew` guarda `_last_tool_calls` PERO NO se serializa en `tasks.result`. Solo `str(result)` se guarda. | `agents.py:303` guarda `str(result)`, tool calls No | Necesario modificar `BaseCrew` o `run_agent` para incluir tool calls en `result` JSON (nuevo campo `tool_calls` o persistir en tabla aparte). **DESVIACIÓN CRÍTICA** |
| D3 | Plan dice "Mostrar tool calls ejecutadas (con nombre y argumentos)". Argumentos de tools No están disponibles en `_last_tool_calls` (solo conteos). | BaseCrew only counts calls, No args | Requiere modificar `ToolCallTracer` para capturar arguments + serializarlos (breaking change Paso 04-05) |
| D4 | Plan menciona polling "a `GET /tasks/{task_id}`". Correcto, pero No especifica intervalo. Patrón existente: ReactQuery polling (useApprovals) o manual useEffect | No definido | Implementar manual con `setInterval` 2s, cleanup, max attempts (5min) |
| D5 | Plan no menciona dónde ubicar `AgentPlayground` dentro de BuilderLayout. BuilderLayout tiene split: left=Canvas, right=Form. | Sin hueco para Playground | Añadir como pestaña/tab en panel derecho (junto a AgentForm) o como panel colapsable inferior |

---

## 1️⃣ Análisis de DATOS (ETAPA 1)

### 1.1 Tablas Involucradas

**`tasks`** (migración 001 + extensiones 002):
```sql
-- Campos críticos para Paso 06
id              UUID PRIMARY KEY
org_id          UUID NOT NULL (FK organizations)
flow_type       TEXT NOT NULL        -- Para Paso 06: "agent:{role}"
status          TEXT NOT NULL         -- 'pending','running','completed','failed',...
payload         JSONB DEFAULT '{}'    -- input_data del usuario
result          JSONB                 -- resultado CrewAI (str + metadata futuro)
error           TEXT
tokens_used     INTEGER DEFAULT 0    -- extraído por BaseCrew
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
-- (002) assigned_agent_role TEXT, approval_* cols, idempotency_key...
```

**Relaciones:**
- `tasks.org_id` → `organizations.id` (FK implícito)
- `tasks.assigned_agent_role` → `agent_catalog.role` (no FK formal)
- No FK declarada para `assigned_agent_role` (verificación: `001_set_config_rpc.sql:62-73` solo FK org_id)

### 1.2 Integridad Referencial

- **org_id:** sí tiene FK → organizations. RLS garantiza belongness.
- **assigned_agent_role:** sin FK → riesgo: se borra agente, tareas quedan huérfanas. Mitigación: RLS + soft-filter por `is_active` en queries.
- **flow_type:** texto libre. Valor para Paso 06: `agent:{role}` (agents.py:274).

### 1.3 RLS Policies

`tasks_org_access` (`001_set_config_rpc.sql:106-108`):
```sql
CREATE POLICY tasks_org_access ON tasks
  FOR ALL USING (org_id::text = current_org_id());
```
- Org isolation garantizada.
- `GET /tasks/{task_id}` usa `verify_org_membership` + `get_tenant_client(org_id)` → RLS aplica.
- **Nota:** `current_org_id()` es función definida en `001_set_config_rpc.sql:32-45`. No confundir con `app.org_id` (variable de sesión).

### 1.4 Índices Relevantes

```sql
CREATE INDEX IF NOT EXISTS idx_tasks_org_id ON tasks(org_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_correlation ON tasks(correlation_id);
```
- Polling por `task_id` usa PK → O(1).
- Filtro por `org_id` + `status` para lists → index cubre.

### 1.5 Gaps de Datos Críticos

| Campo | Origen plan | Estado real | Impacto |
|---|---|---|---|
| `tool_calls` (detalle) | "Mostrar tool calls con nombre y argumentos" | **No existe en tabla** | No se pueden mostrar argumentos sin cambio en BaseCrew |
| `tokens_used` | "Mostrar tokens consumidos" | ✅ En tabla (002) | OK |
| `result` (estructurado) | "Ver respuesta del agente" | `str(result)` plano | Serializable pero no estructurado |

---

## 2️⃣ Análisis de CÓDIGO (ETAPA 2)

### 2.1 Componente Nuevo: `AgentPlayground.tsx`

**Ruta:** `dashboard/components/builder/AgentPlayground.tsx`  
**Tipo:** Client Component (`'use client'`)  
**Estado local requerido:**
```ts
type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: Array<{name: string, count: number, args?: any[]}> // ←_limitado
  tokensUsed?: number
  timestamp: Date
}
state: messages: Message[]
state: isLoading: boolean
state: error: string | null
state: pollingInterval: NodeJS.Timeout | null
```

**Patrón a seguir:**  
Similar a `BuilderLayout` (split panel) + `useApprovals` hook pattern (polling manual).  
NO usar React Query polling (no aplica: task_id único, Marcelo indica manual).  
Referencia: `hooks/useApprovals.ts` (estado local) + `ApprovalsPage` (render).

### 2.2 Funciones/Clases Modificadas

**NINGUNA.**  
Paso 06 es frontend-only (según plan). Backend endpoints ya existen.

### 2.3 Imports Requeridos

```tsx
'use client'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import type { Task } from '@/lib/types'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Send, Bot, User, Tool } from 'lucide-react'
```

### 2.4 Patrones Existentes a Reutilizar

| Patrón | Archivo Referencia | Uso en AgentPlayground |
|---|---|---|
| Estado loading + error | `ApprovalsPage` (lines 12-30) | `isLoading`, `error` |
| Polling manual | `hooks/useApprovals.ts` NO USA polling;buscar ejemplo en flujos | Implementar `setInterval` 2s, cleanup en unmount |
| Render Tool Calls | `CodeBlock` shared component | Mostrar `{tool: name, count}` como JSON compacto |
- Status badges | `StatusLabel.tsx` | Mapear: pending→info, running→warning, completed→success, failed→destructive |
| Card layout | `Card`, `CardHeader`, `CardContent` | Contenedor mensajes + panel de tools |
| Scroll automático | `ScrollArea` con `ref={scrollRef}` + `scrollToBottom` | Mantener chat scrolled to bottom |

### 2.5 Complejidad Ciclomática Estimada

- `AgentPlayground`: Baja (3-4 if branches: loading, error, empty, status handling)
- Polling logic: Media (timeout logic, max retries, stop on completed/failed)

---

## 3️⃣ Análisis de BACKEND (ETAPA 3)

### 3.1 Endpoints Utilizados

**`POST /agents/{role}/run`** (`src/api/routes/agents.py:251-320`):
- **Input:** `{ "input_data": { ... } }` (dict arbitrary)
- **Auth:** `verify_org_membership` (JWT + org membership check)
- **Respuesta OK:** `201 Created` `{ "task_id": "uuid", "status": "accepted" }`
- **Procesamiento:** Background task crea `BaseCrew`, ejecuta `crew.run_async()`, actualiza `tasks` row.
- **Campos actualizados en tasks:**
  - `status`: `pending` → `running` → `completed`/`failed`
  - `result`: `str(result)` (convierte `CrewOutput` a string)
  - `tokens_used`: `crew.get_last_tokens_used()`
  - **NO se guarda tool_calls detalle** (solo en memoria BaseCrew)→ **ver pérdida**

**`GET /tasks/{task_id}`** (`src/api/routes/tasks.py:69-91`):
- **Auth:** `verify_org_membership`
- **Respuesta:** `TaskResponse` serializado (todos los campos de tasks row).
- **Campos relevantes para Playground:**
  - `task_id`, `status` (pending/running/completed/failed)
  - `result` (string o null)
  - `error` (string o null)
  - `tokens_used` (int)
  - `created_at`, `updated_at`

### 3.2 Flujo de Datos Backend → Frontend

```mermaid
sequenceDiagram
  participant UI as AgentPlayground (TSX)
  participant AG as POST /agents/{role}/run
  participant BG as BackgroundTask (FastAPI)
  participant BC as BaseCrew
  participant DB as Supabase tasks
  participant POLL as GET /tasks/{task_id} (repeat)
  
  UI->>AG: POST {role="analyst", input_data: {query:"..."}}
  AG->>BG: enqueue _execute()
  BG->>DB: INSERT task (status=pending)
  AG-->>UI: {task_id, status:"accepted"}
  loop polling every 2s
    UI->>POLL: GET /tasks/{task_id}
    POLL->>DB: SELECT * WHERE id=task_id
    DB-->>POLL: row {status, result, tokens_used...}
    POLL-->>UI: TaskResponse
    alt status == completed
      UI->>UI: render result + tokens + tool_calls (if available)
      break
    else if status == failed
      UI->>UI: render error
      break
    end
  end
```

### 3.3 Middleware/Auth Involucrados

- `verify_org_membership` (`src/api/middleware.py`): verifica JWT + membership en org.
- `get_tenant_client(org_id)`: setea RLS context → `current_org_id()` en SQL.
- **Frontend:** `fapFetch` agrega `Authorization: Bearer <token>` + `X-Org-ID` desde localStorage.

### 3.4 Problemas de Contrato Detectados

| Problema | Línea Backend | Impacto Frontend | Solución |
|---|---|---|---|
| `result` es string plano, no JSON estructurado con tool_calls | `agents.py:303` `status="completed", result=str(result)` | Playground NO puede mostrar tool args, solo raw string string | Modificar `BaseCrew._extract_token_usage` → también extraer `tool_calls` con `get_last_tool_calls()`, guardar en columna separada `tool_calls JSONB` o en `result` como JSON anidado |
| `tokens_used` disponible, pero `assigned_agent_role` maybe NULL si flow_type no sigue patrón `agent:{role}` | `agents.py:274` `flow_type = f"agent:{role}"` | OK, consistente | None |
| Timeout < 500ms: **Plan** lo pide para Paso 01, no aplica a polling. | — | Polling 2s interval OK | None |

**Conclusión:** Contrato POST/GET funciona, pero información de tool calls **no persistida**. Playground solo mostrará texto plano del resultado + conteo de tokens.

---

## 4️⃣ Análisis de FULLSTACK + DX

### 4.1 Flujo Completo: DB → Backend → Frontend → UX

```mermaid
flowchart TD
    A[Usuario escribe mensaje] --> B[UI: enqueue POST /agents/{role}/run]
    B --> C[Backend: create task pending]
    C --> D[BackgroundTask: BaseCrew.run_async]
    D --> E[AgentFactory resolve tools]
    E --> F[CrewAI kickoff_async]
    F --> G[ToolCallTracer wraps tools]
    G --> H[Update task: status=running]
    H --> I[Ejecución tools + LLM]
    I --> J[Update task: status=completed<br/>result=str()<br/>tokens_used=...]
    J --> K[UI polling GET /tasks/{task_id}]
    K --> L[Render: mensaje + resultado + tokens]
```

### 4.2 Coherencia End-to-End

| Capa | Decisión | Validación |
|---|---|---|
| Data (DB) | `tasks.result` string plano | ❌ Inadecuado para tool args |
| Backend | No serializa tool_calls | ❌ Loss of UX fidelity |
| Frontend | Espera tool_calls con nombre+args (plan) | ❌ No disponible |

**Conclusión:** Plan promete "tool calls ejecutadas (con nombre y argumentos)" — **no realizable con backend actual**. O:
1. (MVP) Playground muestra solo resultado + tokens (sin args) → ajustar plan
2. (Fix) Modificar `BaseCrew` para persistir tool_calls detalle → impacto Pasos 04-05

### 4.3 Gaps de UX

- **Tool calls solo conteo disponible** → UI mostrará `{tool: "fetch_url", count: 2}` sin argumentos.
- **Resultado como string plano** → puede ser JSON o texto. Necesita highlight/format simple.
- **No stream** → usuario espera hasta completar (CrewAI sync execution). Aceptable para MVP.
- **Estado intermedio "running"** → no muestra progreso parcial (CrewAI no expone streaming por defecto).

### 4.4 DX & Tooling (OBLIGATORIO)

### Herramienta Propuesta: **`fap agent test` CLI command**

- **Qué automatiza:** Probar un agente desde terminal sin abrir dashboard. Envia mensaje de prueba a `POST /agents/{role}/run` y espera resultado completo (polling). Muestra output + tokens + tool calls count.
- **Tipo:** sub-comando Typer en `src/cli/commands/agent_test.py`
- **Cómo se usa:**
  ```bash
  fap agent test --role analyst --message "Analyze sales data Q1" --org-id <uuid>
  # Salida:
  # [⏳] Task pending... (2s)
  # [✅] Completed in 8.2s | Tokens: 1240
  # Result: <texto resultado>
  # Tools called:
  #   - fetch_url (2 calls)
  #   - search_db (1 call)
  ```
- **Impacto para el usuario final:** Devs/testers pueden depurar agentes rapidamente sin UI. Dogfooding valida backend + UX antes de builder.
- **Prioridad:** **Tarea 0** — implementar ANTES de AgentPlayground para validar contrato tool_calls.
- **Archivo:** `src/cli/commands/agent_test.py` (nuevo)
- **Registro:** `src/cli/main.py` → `agent_app.add_typer(test_app, name="test")` o `agent_app.command("test")`

**Argumento:** Dogfooding critical para verificar que `BaseCrew` captura tool calls de manera reutilizable. Si CLI funciona, Playground copia su lógica de polling.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `tasks` existe con columnas: id, org_id, status, result, tokens_used, assigned_agent_role (mig 001, 002)
✅ [CODE] Componente `AgentPlayground.tsx` creado en `dashboard/components/builder/` con interfaz: messages[], onSubmit, polling useEffect
✅ [BACKEND] Endpoint `POST /agents/{role}/run` retorna task_id (verificado agents.py:251)
✅ [BACKEND] Endpoint `GET /tasks/{task_id}` retorna status, result, tokens_used (verificado tasks.py:69)
✅ [FULLSTACK] Usuario puede escribir mensaje → ver respuesta del agente en UI (end-to-end validate)
✅ [FULLSTACK] Tool calls mostradas como: nombre + count (limitado por datos disponibles)
✅ [FULLSTACK] Tokens consumidos mostrados al finalizar
✅ [FULLSTACK] Estados: loading (spinner), error (mensaje), empty (placeholder)
✅ [DX] CLI `fap agent test` ejecuta sin errores, muestra resultado + tokens
✅ [DX] CLI valida polling logic reutilizable en AgentPlayground
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **Tool calls sin argumentos** | **Alta** | `BaseCrew` solo guarda conteos en `_last_tool_calls`, no args | Ajustar expectativas UX: mostrar solo "Tool X ejecutada N veces". Futuro: modificar `ToolCallTracer` para capturar kwargs |
| **`str(result)` pérdida de estructura** | Media | CrewAI `CrewOutput` no se serializa a JSON automáticamente | Convertir `result` a string con `result.raw` si disponible; investigar `result.json()` en CrewAI v1 |
| **Polling过快 → rate limit DB** | Media | Interval 2s + múltiples usuarios concurrentes | Exponencial backoff en frontend; cache server-side con Redis futuro |
| **Timeout largos (>30s) rompen UX** | Media | CrewAI ejecución puede tardar | Show progress indicator "Agent is working..." + cancel button (opcional post-MVP) |
| **Agent no existe → 404** | Baja | role inválido o agente inactivo | Frontend valida contra lista de agentes existentes (desde AgentForm) antes de enviar |
| **RLS falla si X-Org-ID mal** | Baja | localStorage corrupto | Error handling en `fapFetch`: limpiar sesión + redirect a login |

**Riesgo discoverDurante análisis:**  
ToolCallTracer No captura arguments → límite UX severo. **Acción:** Añadir Campo `tool_calls JSONB` a tabla `tasks` en migración futura, modificar `BaseCrew.run_async()` para serializar `tracer._calls` con argumentos (requiere wrapper que capture `*args, **kwargs`).

---

## 7️⃣ Plan de Implementación

**Reglas atómicas:** 1 tarea = 1 archivo. Patrón explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX Tooling:** CLI `fap agent test` | `src/cli/commands/agent_test.py` | `def test_agent(role: str, message: str, org_id: str):` | `src/cli/commands/agent_create.py` (patrón CLI Typer) + `BaseCrew` usage | DX | Media | 2h | Ninguna | `fap agent test --role analyst --message "test" --org-id xxx` ejecuta sin traceback y muestra resultado |
| 1 | Crear `AgentPlayground` componente vacío | `dashboard/components/builder/AgentPlayground.tsx` | `export function AgentPlayground({role, allowedTools})` | `BuilderLayout.tsx` (función export default) | CODE | Baja | 0.5h | Tarea 0 (validar API) | Componente se importa sin error en `BuilderLayout.tsx` |
| 2 | Implementar estado mensajes + input UI | `AgentPlayground.tsx` (modificar) | `messages: Message[]`, `input: string`, `onSubmit()` | `ApprovalsPage` patterns (useState + loading) | CODE | Media | 1h | Tarea 1 | Input + Send button render, texto se captura |
| 3 | Implementar POST a `/agents/{role}/run` | `AgentPlayground.tsx` (modificar) | `const response = await api.post(`/agents/${role}/run`, {input_data: {message: input}})` | `AgentForm.tsx:150-155` (api.post pattern) | BACKEND | Baja | 0.5h | Tarea 2 | task_id recibido, messages append user msg |
| 4 | Implementar polling con `setInterval` | `AgentPlayground.tsx` (modificar) | `useEffect(() => { if(taskId) interval = setInterval(poll, 2000); return cleanup },[taskId])` | Manual (sin hook externo) | BACKEND | Media | 1h | Tarea 3 | status se actualiza en UI cada 2s |
| 5 | Renderizar mensajes + tool calls | `AgentPlayground.tsx` (modificar) | `messages.map(msg => <Card>...</Card>)` | `CodeBlock` + `StatusLabel` patterns | FULLSTACK | Media | 1.5h | Tarea 4 | Mensaje assistant muestra texto + tool calls como JSON collapsed |
| 6 | Mostrar tokens usados | `AgentPlayground.tsx` (modificar) | Al completar: `tokens_used: task.tokens_used` en mensaje final | `StatusLabel` badge + texto pequeño | FULLSTACK | Baja | 0.5h | Tarea 5 | Tokens visibles debajo del resultado |
| 7 | Manejo de errores + empty states | `AgentPlayground.tsx` (modificar) | Si error: mostrar `ErrorLabel`; si sin mensajes: `EmptyState` | `ApprovalsPage` error handling (try/catch + toast) | FULLSTACK | Baja | 0.5h | Tarea 6 | Error muestra mensaje amigable, no crash |
| 8 | Integrar en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Añadir `<AgentPlayground role={formValues.role} />` como 3ra pestaña o panel colapsable | `Tabs` component UI (si existe) o Estado dialog | FULLSTACK | Media | 1h | Tarea 7 | BuilderLayout muestra Playground accesible desde formulario |

**Tiempo total estimado:** 7.5 horas (≈ 1 día)

**Dependencias críticas:**
- Tarea 0 (CLI) → valida contrato POST/GET antes de UI
- Tarea 3 → requiere rol válido existente en DB (desde AgentForm ya guardado)

---

## 8️⃣ Suposiciones No Verificadas (⚠️)

| Suposición | Razón No-Verificada | Sugerencia |
|---|---|---|
| `result` de CrewAI contiene texto legible | No ejecuté crew localmente, solo leo código | Validar con `fap agent test` (Tarea 0) |
| ToolCallTracer captura al menos nombres de tools | Código `base_crew.py:35-45` sí lo hace | OK, pero args No →울 |
| Polling 2s es suficiente para latencia | No medido en prod | Ajustar a 1s si es lento, 3s si DB carga |
| `ScrollArea` soporta auto-scroll | Asumo por uso común en Radix | Verificar con `ref.current.scrollTo(0, height)` |

---

## 9️⃣ Roadmap (NO implementar ahora)

**Optimizaciones post-MVP:**
- Streaming de chunks desde CrewAI (si crewai >=0.100 soporta `stream=True`)
- Tool calls con argumentos → modificar `ToolCallTracer` para capturar `*args, **kwargs` en wrapper
- Persistir tool_calls en tabla `task_tool_invocations` para histórico + replay
- Exportar conversación del playground junto con bundle
- Soporte multimodal: subir archivos al chat (adjuntar a `input_data`)
- Rate limiting por usuario en playground (evitar spam de tasks)

---

## 🔚 Conclusión

Paso 06 (Agent Playground) es **factible** con el backend existente, pero **limitado**:
- No hay argumentos de tool calls → UX degrade vs plan original.
- `tokens_used` y completion status OK.
- Implementación frontend atómica en 1 componente nuevo.
- DX CLI `fap agent test` es **obligatorio** para dogfooding y debugging.

**Desviación crítica:**  
El plan promete "tool calls (con nombre y argumentos)". **Argumentos NO están disponibles** sin modificar `BaseCrew` y esquema de persistencia. Dos caminos:
1. **MVP ajustado:** Playground muestra solo "Tool X ejecutada N veces" (conteo).
2. **Fix previo:** Añadir columna `tool_calls JSONB` a `tasks`, modificar `BaseCrew._extract_token_usage` para serializar argumentos (impacto Paso 04, 05).

**Recomendación:**  
Implementar Paso 06 con **conteo de tools solamente** (como está hoy BaseCrew), marcar como limitación documentada. Abrir ticket para "Persistir tool call arguments en tasks" como mejora Post-MVP. Si el product owner exige argumentos, bloquear Paso 06 hasta modificar BaseCrew.

---

**Métricas de Calidad (checklist):**
- ✅ proy-config.json leído (rutas validadas)
- ✅ ≥ 10 elementos verificados (umbral ≥8 para 3-5 archivos afectados)
- ✅ 2 discrepancias detectadas (D1 types.ts, D2/D3 tool args)
- ✅ 9 secciones completadas (0-8)
- ✅ 4 etapas cubiertas (data, code, backend, fullstack+DX)
- ✅ 10 criterios de aceptación binarios
- ✅ 6 riesgos identificados (técnico x3, integración x2, futuro x1)
- ✅ 8 tareas atómicas (1 artefacto cada una)
- ✅ Interfaz exacta por tarea (firmas especificadas)
- ✅ Patrón de referencia explícito por tarea (AgentCreate pattern, useApprovals pattern)
- ✅ Verificación inline por tarea (comandos concretos)
- ✅ 1 herramienta DX propuesta (fap agent test)
- ✅ Estimación de tiempo por tarea + total

**Estado:** Listo para implementación (con desviación documentada).
