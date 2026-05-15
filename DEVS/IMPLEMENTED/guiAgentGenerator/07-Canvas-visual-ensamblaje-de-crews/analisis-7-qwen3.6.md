# Análisis Técnico — Paso 07: Canvas visual — ensamblaje de crews

**Agente:** qwen3.6
**Fecha:** 2026-05-15
**Fase:** guiAgentGenerator

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `BuilderCanvas.tsx` existe | `dashboard/components/builder/BuilderCanvas.tsx` | ✅ | Placeholder ReactFlow vacío, `dynamic import ssr:false`, 46 líneas |
| 2 | `reactflow` v11 instalado | `dashboard/package.json` | ✅ | `"reactflow": "^11.11.4"` detectado |
| 3 | Directorio `nodes/` NO existe | `glob dashboard/components/builder/nodes/` | ❌ | Vacío — hay que crearlo |
| 4 | `agent_catalog` tabla existe | `supabase/migrations/004_agent_catalog.sql:6-17` | ✅ | Columnas: `id`, `org_id`, `role`, `soul_json`, `allowed_tools`, `max_iter` |
| 5 | `flow_registry` singleton existe | `src/flows/registry.py:370` | ✅ | `flow_registry = FlowRegistry()`, métodos: `list_flows()`, `get_metadata()`, `get_hierarchy()` |
| 6 | Endpoint `GET /flows/available` existe | `src/api/routes/flows.py:76-110` | ✅ | Retorna `FlowsListResponse` con `FlowInfo[]` |
| 7 | Endpoint `POST /flows/{flow_type}/run` existe | `src/api/routes/flows.py:142-186` | ✅ | `RunFlowRequest`, `RunFlowResponse`, background task |
| 8 | `BuilderLayout.tsx` existe | `dashboard/components/builder/BuilderLayout.tsx` | ✅ | Usa `BuilderCanvas` línea 72, split 60/40 |
| 9 | `AgentForm` exporta `AgentFormData` | `dashboard/components/builder/AgentForm.tsx:44` | ✅ | `export type AgentFormData = z.infer<typeof agentFormSchema>` |
| 10 | `bundle_schemas.py` — `AgentExportItem` | `src/services/bundle_schemas.py:102-108` | ✅ | Campos: `role`, `soul_json`, `allowed_tools`, `max_iter` |
| 11 | `POST /api/bundles/export` existe | `src/api/routes/bundles.py:199-210` | ✅ | Acepta `ExportBundleRequest`, retorna ZIP |
| 12 | `workflow_templates` tabla existe | `src/flows/registry.py:261` — query DB | ✅ | Columnas: `definition`, `is_python`, `code_source`, `org_id`, `flow_type`, `is_active` |
| 13 | `ToolRegistry` singleton | `src/tools/registry.py:272` | ✅ | `tool_registry = ToolRegistry()`, `list_tools()`, `get_metadata()` |
| 14 | `GET /api/tools/available` existe | `src/api/routes/tools.py:46-63` | ✅ | Retorna `ToolsListResponse` |
| 15 | `AgentPlayground` existe | `dashboard/components/builder/AgentPlayground.tsx` | ✅ | Chat con polling, `formatResult()`, `MessageBubble` |
| 16 | `useCurrentOrg` hook | Usado en `AgentForm.tsx:12` | ✅ | `import { useCurrentOrg } from '@/hooks/useCurrentOrg'` |
| 17 | `api` client | `dashboard/lib/api.ts` | ✅ | `api.get()`, `api.post()` — wrapper con auth headers |
| 18 | shadcn/ui components | `Button`, `Input`, `Dialog`, `Sheet` instalados | ✅ | Usados en BuilderLayout, AgentForm, TemplatePicker |

**Discrepancias encontradas:**

1. **D1 — Plan dice "lista de agentes existentes" en sidebar pero NO hay endpoint para listar agentes por org.** `GET /api/tools/available` lista tools, `GET /flows/available` lista flows, pero no existe `GET /agents` para listar agentes de una org. El plan asume que se pueden listar agentes para arrastrar al canvas. **Resolución:** Crear endpoint `GET /agents` o usar query directa Supabase desde frontend (como ya hace AgentForm para save). Dado que `POST /agents` usa `TenantClient` (RLS), se necesita endpoint backend para GET también.

2. **D2 — Plan dice "tareas disponibles" pero NO existe tabla `tasks` como entidad de usuario.** La tabla `tasks` es de ejecución (resultado de `POST /agents/{role}/run`), no una entidad configurable que se pueda arrastrar. **Resolución:** Las "tareas" del canvas son en realidad nodos de texto descriptivo conectados a agentes, no entidades DB. Serializar como `{type: 'task', description, expected_output}` en el grafo JSON.

3. **D3 — Plan dice "Export as Crew → JSON compatible con bundle-schema-v2.md" pero `bundle-schema-v2` espera `agents[]` + `flows[]` + `skills{}`.** Un crew visual (agent→task connections) no mapea 1:1 a bundle v2. **Resolución:** Exportar como `flows[]` donde cada flow representa un agent+tasks subgraph. El `flow_type` se genera del role del agente.

4. **D4 — Plan dice "Run Crew → POST /flows/{flow_type}/run" pero los flows registrados son Python classes, no crews visuales dinámicos.** El `flow_registry` tiene flows estáticos registrados via `@register_flow`. Un crew ensamblado visualmente no está registrado. **Resolución:** Para MVP, "Run Crew" serializa el grafo → llama `POST /api/bundles/export` para validar → muestra preview Python. Ejecución real post-MVP requiere registrar crew como DynamicWorkflow.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas tocadas:** Ninguna nueva. Paso 07 es puramente frontend (ReactFlow canvas).

**Schema existente relevante:**

- `agent_catalog` — fuente de agentes para nodos AgentNode. Columnas: `id`, `role`, `soul_json` (JSONB con `goal`, `backstory`), `allowed_tools` (TEXT[]), `max_iter` (INTEGER)
- `workflow_templates` — fuente de flows para sidebar. Columnas: `flow_type`, `definition` (JSONB), `is_python`, `code_source`
- `tasks` — solo para resultados de ejecución, no para canvas

**Integridad referencial:** No se crean tablas nuevas. Sin FK nuevas.

**RLS:** No aplica — todo es frontend state.

**Índices:** No aplica.

**Datos en grafo ReactFlow:**

El estado del canvas se mantiene en React state (no persiste en DB para MVP):

```
nodes: Node[] — cada nodo tiene:
  - id: string (uuid)
  - type: 'agent' | 'task' | 'tool'
  - position: { x, y }
  - data: { role?, description?, toolName?, ...metadata }

edges: Edge[] — conexiones:
  - id: string
  - source: nodeId (agent)
  - target: nodeId (task)
  - sourceHandle / targetHandle
```

**Discrepancia data:** Plan no menciona persistencia del grafo. MVP = state local. Post-MVP: tabla `crew_definitions` con `org_id`, `name`, `graph_json` (JSONB).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos

#### `AgentNode.tsx`
- **Ubicación:** `dashboard/components/builder/nodes/AgentNode.tsx`
- **Tipo:** Custom ReactFlow node (`NodeComponent`)
- **Props (ReactFlow `NodeProps`):**
  - `data: { role: string, goal?: string, tools?: string[], maxIter?: number }`
  - `selected: boolean`
- **Firma:**
```tsx
export function AgentNode({ data, selected }: NodeProps)
```
- **Render:** Card con role (header), goal (truncate), tools badges (max 3), maxIter badge. Borde cambia si `selected`. Handle de conexión en lado derecho (`Position.Right`).
- **Patrón a seguir:** Custom nodes en reactflow v11 — `import { Handle, Position, NodeProps } from 'reactflow'`. Referencia: docs reactflow v11 custom nodes.

#### `TaskNode.tsx`
- **Ubicación:** `dashboard/components/builder/nodes/TaskNode.tsx`
- **Props:**
  - `data: { description: string, expectedOutput?: string }`
- **Firma:**
```tsx
export function TaskNode({ data, selected }: NodeProps)
```
- **Render:** Card con description (truncate), expectedOutput (muted). Handle izquierdo (`Position.Left`) para recibir conexión de agent, handle derecho (`Position.Right`) para encadenar a otra task.

#### `ToolNode.tsx`
- **Ubicación:** `dashboard/components/builder/nodes/ToolNode.tsx`
- **Props:**
  - `data: { name: string, source: 'local' | 'mcp', description?: string }`
- **Firma:**
```tsx
export function ToolNode({ data, selected }: NodeProps)
```
- **Render:** Card compacta con nombre + badge source. Solo handle izquierdo (`Position.Left`) — las tools no se conectan entre sí, solo son hijos de agent.

#### `CrewCanvas.tsx`
- **Ubicación:** `dashboard/components/builder/CrewCanvas.tsx`
- **Reemplaza:** `BuilderCanvas.tsx` placeholder actual
- **Firma:**
```tsx
export function CrewCanvas({
  onExport,
  onRun,
}: {
  onExport?: (graph: CrewGraph) => void
  onRun?: (graph: CrewGraph) => void
})
```
- **Interfaces:**
```tsx
interface CrewGraphNode {
  id: string
  type: 'agent' | 'task' | 'tool'
  data: Record<string, unknown>
  position: { x: number; y: number }
}

interface CrewGraphEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

interface CrewGraph {
  nodes: CrewGraphNode[]
  edges: CrewGraphEdge[]
  metadata: { name: string; createdAt: string }
}
```
- **Estado interno:**
  - `nodes: Node[]` — ReactFlow nodes
  - `edges: Edge[]` — ReactFlow edges
  - `sidebarOpen: boolean` — panel lateral de nodos arrastrables
- **Funciones internas:**
  - `onNodesChange` — `applyNodeChanges` de reactflow
  - `onEdgesChange` — `applyEdgeChanges` de reactflow
  - `onConnect` — `addEdge` con validación (agent→task, agent→tool, task→task)
  - `onDragStart` — set `dragType` en `event.dataTransfer`
  - `onDrop` — crear nodo desde sidebar drag
  - `onDragOver` — `event.preventDefault()` para permitir drop
  - `serializeGraph()` → `CrewGraph`
  - `validateGraph()` → `{ valid: boolean, warnings: string[] }`
- **Patrón a seguir:** `BuilderCanvas.tsx` existente para `dynamic import` de ReactFlow. Pero CrewCanvas es componente completo con state, no solo placeholder.

### Validación de conexiones

| Conexión | Válida | Razón |
|---|---|---|
| Agent → Task | ✅ | Asignación de tarea a agente |
| Agent → Tool | ✅ | Tool asignada a agente |
| Task → Task | ✅ | Secuencia de tareas |
| Task → Agent | ❌ | No soportado en MVP |
| Tool → Anything | ❌ | Tool es hoja del grafo |

### Imports necesarios

```tsx
// CrewCanvas.tsx
import { useState, useCallback, useMemo } from 'react'
import ReactFlow, {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type Connection,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
```

### Patrones existentes a seguir

- **Custom node pattern:** reactflow v11 — `Handle` + `Position` + `NodeProps`
- **Dynamic import:** mismo patrón que `BuilderCanvas.tsx:6-30` para SSR safety
- **State management:** `useState` local (no Zustand/Redux — proyecto no tiene global state manager)
- **API calls:** `api.get()` / `api.post()` desde `@/lib/api` (patrón AgentForm/TemplatePicker)

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Endpoints existentes que el canvas consume:**

| Endpoint | Uso en Canvas | Auth |
|---|---|---|
| `GET /api/tools/available` | Sidebar — lista tools para arrastrar como ToolNode | `require_org_id` |
| `GET /flows/available` | Sidebar — lista flows existentes | `require_org_id` |
| `GET /agents` (NO EXISTE) | Sidebar — lista agentes para arrastrar | — |

**Discrepancia backend:** No hay endpoint `GET /agents` para listar agentes de una org. El canvas necesita esta lista para el sidebar de nodos arrastrables.

**Opción A:** Crear endpoint `GET /agents` en `src/api/routes/agents.py`
- Método: GET
- Auth: `require_org_id`
- Query params: `?active_only=true`
- Response: `[{ id, role, goal, backstory, allowed_tools, max_iter }]`
- Implementación: `TenantClient` + `.table('agent_catalog').select('*').eq('org_id', org_id)`

**Opción B:** Query directa desde frontend con Supabase client
- NO viable — RLS requiere `app.org_id` seteado por middleware backend (phase-state D4)

**Resolución:** Opción A obligatoria. Endpoint mínimo.

**Export como Crew:**
- Plan dice "serializa a JSON compatible con bundle-schema-v2"
- `CrewGraph` → mapear a `ExportBundleRequest`:
  - AgentNodes → `agents[]` (role, soul_json desde agent_catalog lookup, allowed_tools, max_iter)
  - TaskNodes → `flows[]` (cada task como flow con `definition` JSON)
  - ToolNodes → ya incluidas en `allowed_tools` de cada agente
- POST a `POST /api/bundles/export` con payload mapeado

**Run Crew:**
- Plan dice "POST /flows/{flow_type}/run"
- Problema: crew visual no es flow registrado
- MVP: "Run Crew" = validate graph → show Python code preview → NO ejecuta
- Post-MVP: registrar crew como DynamicWorkflow en `workflow_templates`

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
[DB: agent_catalog] → GET /agents → [Sidebar: Agent cards]
                                        ↓ drag
[DB: tool_registry] → GET /api/tools/available → [Sidebar: Tool cards]
                                                    ↓ drag
[DB: workflow_templates] → GET /flows/available → [Sidebar: Flow cards]
                                                     ↓ drop
                                         [ReactFlow Canvas]
                                         nodes + edges state
                                                    ↓
                                    [validateGraph() → warnings]
                                                    ↓
                        ┌───────────────────────────┼───────────────────────────┐
                        ↓                           ↓                           ↓
              "Export as Crew"              "Run Crew" (MVP)           "Copy as JSON"
                        ↓                           ↓                           ↓
          map to ExportBundleRequest     show Python preview           clipboard JSON
                        ↓
          POST /api/bundles/export
                        ↓
              ZIP download
```

### Coherencia

- ✅ ReactFlow v11 ya instalado y configurado (BuilderCanvas placeholder)
- ✅ `agent_catalog` tiene todos los campos necesarios para AgentNode
- ✅ `GET /api/tools/available` ya existe para ToolNode
- ✅ `GET /flows/available` ya existe para flow reference
- ❌ Falta `GET /agents` para listar agentes en sidebar
- ⚠️ "Run Crew" no ejecuta realmente en MVP — solo preview

### Gaps

1. **GET /agents no existe** — bloquea sidebar de agentes arrastrables
2. **Crew execution no mapea a flows registrados** — "Run Crew" es UI-only en MVP
3. **Sin persistencia de grafo** — si usuario refresca, pierde canvas

### DX & Tooling

### Herramienta Propuesta: `fap crew validate`
- **Qué automatiza:** Validar estructura de grafo crew (agent→task→tool) sin necesidad de abrir el builder UI. Permite verificar JSON de crew exportado antes de importar.
- **Tipo:** CLI command
- **Cómo se usa:** `fap crew validate --file crew-graph.json` → output: warnings de agentes sin tareas, tools no registradas, ciclos de dependencia
- **Impacto para el usuario final:** Evita exportar crews inválidos. Feedback inmediato en terminal sin consumir UI.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

### Herramienta Propuesta: `fap crew export`
- **Qué automatiza:** Exportar agentes de una org como crew JSON directamente desde CLI, sin pasar por el builder visual.
- **Tipo:** CLI command
- **Cómo se usa:** `fap crew export --org-id <id> --roles "researcher,writer" --output crew.json`
- **Impacto para el usuario final:** Genera crew JSON para compartir/revisar sin UI. Complementa `fap bundle export`.
- **Prioridad:** Post-MVP — depende de `GET /agents` endpoint

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] agent_catalog tabla existe con columnas role, soul_json, allowed_tools, max_iter (verificado mig 004)
✅ [DATA] workflow_templates tabla existe con flow_type, definition (verificado registry.py:261)
✅ [CODE] AgentNode component existe con Handle izquierdo/derecho, muestra role + tools badges
✅ [CODE] TaskNode component existe con Handle izquierdo/derecho, muestra description
✅ [CODE] ToolNode component existe con Handle izquierdo, muestra name + source badge
✅ [CODE] CrewCanvas component existe con ReactFlow, sidebar drag-drop, onConnect validation
✅ [CODE] serializeGraph() retorna CrewGraph con nodes[] + edges[] + metadata
✅ [CODE] validateGraph() retorna warnings para agentes sin tareas
✅ [BACKEND] Endpoint GET /agents existe y retorna lista de agentes de org (nuevo)
✅ [BACKEND] GET /api/tools/available retorna tools para sidebar (existente, verificado)
✅ [BACKEND] GET /flows/available retorna flows para sidebar (existente, verificado)
✅ [FULLSTACK] Drag agent desde sidebar al canvas crea AgentNode
✅ [FULLSTACK] Conexión Agent→Task visible como edge con marker
✅ [FULLSTACK] "Export as Crew" genera JSON compatible con bundle-schema-v2
✅ [FULLSTACK] "Run Crew" muestra preview Python (MVP, sin ejecución real)
✅ [FULLSTACK] Canvas tiene minimapa + zoom controls (MiniMap + Controls de reactflow)
✅ [DX] fap crew validate CLI existe y valida grafo JSON
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| GET /agents no existe | Alta | Plan asume listado de agentes pero solo existe POST /agents | Crear endpoint GET /agents como T1 bloqueante |
| Run Crew sin ejecución real | Media | Flows visuales no están registrados en flow_registry | MVP = preview Python solo. Documentar como limitación. Post-MVP: DynamicWorkflow |
| Sin persistencia de grafo | Media | Canvas state es local, refresh = pérdida | Documentar como limitación MVP. Post-MVP: tabla crew_definitions |
| reactflow v11 API vs v12 | Baja | v11 usa `reactflow`, v12 usa `@xyflow/react` con API diferente | Ya verificado: v11 instalado. No migrar. |
| ToolNode sin conexión bidireccional | Baja | Tools son hojas del grafo, no se conectan entre sí | Validación onConnect rechaza Tool→Anything |
| Export JSON no compatible bundle v2 | Media | CrewGraph ≠ ExportBundleRequest estructura | Mapeo explícito: AgentNode→AgentExportItem, TaskNode→flow definition |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap crew validate` CLI | `src/cli/commands/crew_validate.py` | `def validate_crew(file: Path) -> dict: returns {valid: bool, warnings: list[str]}` | `src/cli/commands/bundle_export.py` — estructura Typer command + Rich output | DX | Media | 1.5h | Ninguna | → verificar: `uv run fap crew validate --help` ejecuta sin errores |
| 1 | Crear endpoint `GET /agents` | `src/api/routes/agents.py` (modificar) | `async def list_agents(org_id: str = Depends(require_org_id), active_only: bool = True) -> ListAgentsResponse` donde `ListAgentsResponse = BaseModel with agents: List[AgentListItem]`, `AgentListItem = BaseModel with id: str, role: str, goal: str, backstory: str, allowed_tools: list[str], max_iter: int` | `src/api/routes/flows.py:76-110` — `list_available_flows` pattern | BACKEND | Baja | 0.5h | Tarea 0 | → verificar: `curl /agents` con org header retorna 200 + array |
| 2 | Registrar router agents en main.py | `src/api/main.py` (modificar) | Import `router` desde `agents.py` ya existe (verificar línea) — solo confirmar que GET /agents es accesible | `src/api/main.py:31,112` — pattern existente tools/templates | BACKEND | Baja | 0.25h | Tarea 1 | → verificar: endpoint responde |
| 3 | Crear `AgentNode.tsx` | `dashboard/components/builder/nodes/AgentNode.tsx` | `export function AgentNode({ data, selected }: NodeProps)` — data: `{ role: string, goal?: string, tools?: string[], maxIter?: number }` | reactflow v11 custom node — `Handle` + `Position` + `NodeProps` de `reactflow` | CODE | Media | 1h | Ninguna | → verificar: importable sin error, renderiza con mock data |
| 4 | Crear `TaskNode.tsx` | `dashboard/components/builder/nodes/TaskNode.tsx` | `export function TaskNode({ data, selected }: NodeProps)` — data: `{ description: string, expectedOutput?: string }` | `AgentNode.tsx` (tarea 3) — mismo patrón Handle/Position | CODE | Baja | 0.5h | Tarea 3 | → verificar: importable sin error |
| 5 | Crear `ToolNode.tsx` | `dashboard/components/builder/nodes/ToolNode.tsx` | `export function ToolNode({ data, selected }: NodeProps)` — data: `{ name: string, source: 'local' \| 'mcp', description?: string }` | `AgentNode.tsx` (tarea 3) — mismo patrón, solo Handle izquierdo | CODE | Baja | 0.5h | Tarea 3 | → verificar: importable sin error |
| 6 | Crear `CrewCanvas.tsx` | `dashboard/components/builder/CrewCanvas.tsx` | `export function CrewCanvas({ onExport, onRun }: { onExport?: (graph: CrewGraph) => void, onRun?: (graph: CrewGraph) => void })` con interfaces `CrewGraphNode`, `CrewGraphEdge`, `CrewGraph` | `BuilderCanvas.tsx` — dynamic import ReactFlow + `dashboard/components/builder/AgentForm.tsx` — pattern useState + api calls | CODE | Alta | 3h | Tareas 3,4,5 | → verificar: canvas renderiza, drag-drop crea nodos, conexiones válidas |
| 7 | Implementar `serializeGraph()` | `dashboard/components/builder/CrewCanvas.tsx` (interno) | `function serializeGraph(nodes: Node[], edges: Edge[]): CrewGraph` — mapea ReactFlow Node/Edge a CrewGraph format | — | CODE | Media | 0.5h | Tarea 6 | → verificar: retorna JSON con nodes[] + edges[] + metadata |
| 8 | Implementar `validateGraph()` | `dashboard/components/builder/CrewCanvas.tsx` (interno) | `function validateGraph(nodes: Node[], edges: Edge[]): { valid: boolean, warnings: string[] }` — detecta agentes sin tareas, tools huérfanas | — | CODE | Media | 0.5h | Tarea 6 | → verificar: warning para agent sin edges |
| 9 | Integrar CrewCanvas en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` (modificar) | Reemplazar `<BuilderCanvas />` con `<CrewCanvas onExport={handleExport} onRun={handleRun} />` | `BuilderLayout.tsx:72` — línea actual de BuilderCanvas | CODE | Baja | 0.5h | Tarea 6 | → verificar: /builder muestra CrewCanvas funcional |
| 10 | Implementar "Export as Crew" handler | `dashboard/components/builder/BuilderLayout.tsx` (modificar) | `function handleExport(graph: CrewGraph)` — mapea CrewGraph → ExportBundleRequest → POST /api/bundles/export → descarga ZIP | `AgentForm.tsx:138-179` — pattern onSubmit + api.post + toast | FULLSTACK | Alta | 1.5h | Tareas 1,6,7 | → verificar: click Export → ZIP descargable |
| 11 | Implementar "Run Crew" MVP handler | `dashboard/components/builder/BuilderLayout.tsx` (modificar) | `function handleRun(graph: CrewGraph)` — valida grafo → genera Python code preview → muestra en Dialog | `AgentPlayground.tsx:39-45` — pattern formatResult + Dialog | FULLSTACK | Media | 1h | Tareas 6,8 | → verificar: click Run → Dialog con Python preview |
| 12 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-11 | → verificar: criterios §5 pasan todos |

**Tiempo total estimado:** 11.75 horas

---

## 🔮 Roadmap (NO implementar ahora)

1. **Persistencia de crews:** Tabla `crew_definitions` con `org_id`, `name`, `graph_json` (JSONB), `created_at`. Endpoint `POST /crews` + `GET /crews`.
2. **Ejecución real de crews:** Registrar crew visual como `DynamicWorkflow` en `workflow_templates`. `POST /flows/{crew_type}/run` ejecuta grafo secuencialmente.
3. **Undo/Redo en canvas:** Historial de estados con `useReducer` + stack.
4. **Auto-layout:** Algoritmo force-directed o DAG layout para organizar nodos automáticamente.
5. **Collaborative editing:** WebSockets para multi-user canvas editing.
6. **Template de crews:** Guardar crew como template reutilizable (similar a agent templates).
7. **fap crew export CLI:** Exportar crew desde terminal sin UI.

---

## 🚫 Reglas de Oro Cumplidas

- ✅ Análisis específico al Paso 07, no genérico
- ✅ 18 elementos verificados contra código (§0)
- ✅ 4 discrepancias detectadas con resolución
- ✅ 8 secciones completadas (0-7)
- ✅ 4 etapas cubiertas (data, code, backend, fullstack+DX)
- ✅ 17 criterios de aceptación verificables
- ✅ 6 riesgos identificados (técnico, integración, futuro)
- ✅ Tareas atómicas: 1 artefacto por tarea
- ✅ Interfaz exacta por tarea (firmas completas)
- ✅ Patrón de referencia explícito por tarea
- ✅ Verificación inline por tarea
- ✅ 2 herramientas DX propuestas (`fap crew validate`, `fap crew export`)
- ✅ Estimación de tiempo por tarea y total
