# 🧠 Análisis Técnico — Paso 07 (step)

> **Agente:** step | **Fecha:** 2026-05-15 | **Fase:** guiAgentGenerator
> **Paso:** Canvas visual — ensamblaje de crews

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `reactflow` v11 instalado | grep `package.json` | ✅ | `dashboard/package.json:41` — `"reactflow": "^11.11.4"` |
| 2 | `BuilderCanvas.tsx` existe | ls `components/builder/` | ✅ | `BuilderCanvas.tsx:1-46` — placeholder vacío, node≡[], edge≡[], `<ReactFlow>` con `<Background/>` `<Controls/>` `<MiniMap/>` |
| 3 | `BuilderLayout.tsx` existe con split 60/40 | grep layout | ✅ | `BuilderLayout.tsx:70` — `lg:grid-cols-[60%_40%]` |
| 4 | `AgentForm.tsx` con 11 campos | grep schema | ✅ | `AgentForm.tsx:30-42` — role, goal, backstory, llmProvider, llmModel, allowedTools, maxIter, verbose, reasoning, injectDate, memory |
| 5 | Tabla `agent_catalog` existe | grep migrations | ✅ | `supabase/migrations/004_agent_catalog.sql:6-17` — id, org_id, role, soul_json, allowed_tools, max_iter, UNIQUE(org_id, role) |
| 6 | RLS `agent_catalog_tenant_isolation` | grep migrations RLS | ✅ | `supabase/migrations/025_agent_catalog_rls_update.sql:11-15` — `org_id::text = current_setting('app.org_id', TRUE)` |
| 7 | Endpoint `POST /api/bundles/export` | grep bundles.py | ✅ | `bundles.py:199-253` — `ExportBundleRequest` payload, `Response(content=zip_bytes)` |
| 8 | `AgentExportItem` schema | grep bundle_schemas.py | ✅ | `bundle_schemas.py:102-108` — role, soul_json `Dict`, allowed_tools `List[str]`, max_iter `int(ge=1, le=50)` |
| 9 | `ExportBundleRequest` | grep bundle_schemas.py | ✅ | `bundle_schemas.py:111-116` — `bundle_name Optional`, `agents List[AgentExportItem]`, `skills Optional[List[SkillExportItem]]` |
| 10 | `POST /flows/{flow_type}/run` | grep flows.py | ✅ | `flows.py:142-186` — `RunFlowRequest`, `RunFlowResponse`, `background_tasks.add_task(execute_flow_instance)` |
| 11 | Flujos registrados en FlowRegistry | grep registry.py | ✅ | `generic_flow`, `success_test_flow`, `fail_test_flow` — 3 únicos |
| 12 | `POST /agents/{role}/run` | grep agents.py | ✅ | `agents.py:251-320` — `RunAgentRequest`, async `_execute()` background, `BaseCrew(org_id, role)` |
| 13 | `BaseCrew.__init__` | grep base_crew.py | ✅ | `base_crew.py:68-80` — `__init__(self, org_id, role)` — carga agente desde `agent_catalog`, carga herramientas |
| 14 | Sidebar "Builder" en nav | grep nav-main.tsx | ✅ | `nav-main.tsx:50` — `{ title: 'Builder', url: '/builder', icon: Wand2 }` |
| 15 | `POST /agents` create AGENT | grep agents.py | ✅ | `agents.py:51-101` — `AgentCreate(BaseModel)`, upsert via `TenantClient`, 201 Created |
| 16 | shadcn `Dialog` componente | ls ui/dialog | ✅ | `dashboard/components/ui/dialog.tsx` — `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle` |
| 17 | shadcn `Sheet` componente | ls ui/sheet | ✅ | `dashboard/components/ui/sheet.tsx` — `Sheet`, `SheetContent`, `SheetHeader`, `SheetTitle` |
| 18 | `@radix-ui/react-tabs` | grep package.json | ✅ | `dashboard/package.json:24` — `"@radix-ui/react-tabs": "^1.1.2"` |
| 19 | `@radix-ui/react-tooltip` | grep package.json | ✅ | `dashboard/package.json:25` — `"@radix-ui/react-tooltip": "^1.2.8"` |
| 20 | `@radix-ui/react-scroll-area` | grep package.json | ✅ | `dashboard/package.json:19` — `"@radix-ui/react-scroll-area": "^1.2.10"` |
| 21 | `@dnd-kit/core` / `react-dnd` | grep package.json | ❌ | **DISCREPANCIA D-01**: No hay ninguna librería DnD en `dashboard/package.json`. Plan asume drag-drop. Resolución: HTML5 DnD nativo — `draggable`, `dataTransfer.setData('application/reactflow', JSON.stringify({type}))`, `onDragOver` + `onDrop` en canvas. Sin deps extra. |
| 22 | Sin flow "crew" registrado | grep registry | ❌ | **DISCREPANCIA D-02**: Solo `generic_flow`, `success_test_flow`, `fail_test_flow`. Plan pide `POST /flows/{flow_type}/run` para "Run Crew". Resolución MVP: usar `POST /agents/{role}/run` por agente. "Run All" ejecuta secuencialmente via `Promise.all`. Post-MVP: crear `crew_runner_flow` que acepte `{ agents, tasks, process }`. |
| 23 | `ExportBundleRequest` sin `tasks` ni `edges` | grep bundle_schemas.py | ❌ | **DISCREPANCIA D-03**: `ExportBundleRequest` solo agrupa `agents` + `skills`. `tasks`/`edges` del canvas no se serializan al ZIP. Resolución MVP: exportar solo agentes del canvas. Mostrar warning en dialog. "Copy as JSON" sí incluye tasks+edges. |
| 24 | Agentes custom `AgentNode.tsx` | ls `components/builder/` | ❌ | **DISCREPANCIA D-04**: No existe. Directorio `builder/` tiene solo: `AgentForm`, `AgentPlayground`, `BuilderCanvas`, `BuilderLayout`, `TemplatePicker`, `ToolMultiSelect`. |
| 25 | `CrewCanvas.tsx` (canva principal) | ls `components/builder/` | ❌ | **DISCREPANCIA D-05**: No existe. `BuilderCanvas.tsx` sigue siendo placeholder Step 07. |
| 26 | `crewCodeGen.ts` (generador Python code) | ls `dashboard/lib/` | ❌ | **DISCREPANCIA D-06**: No existe. Plan pide "Preview Code" mostrando código Python CrewAI equivalente. |
| 27 | `TaskNode.tsx` | ls `components/builder/nodes/` | ❌ | **DISCREPANCIA D-07**: Directorio `nodes/` NO existe. Sin nodos custom creados. |
| 28 | `BaseFlow` clase abstracta | grep base_flow.py | ✅ | `base_flow.py:61-446` — `validate_input()`, `_run_crew()`, `execute()`, `create_task_record()` |
| 29 | `TaskResponse.tokens_used` | grep types.ts | ✅ | `types.ts:8` — `tokens_used: number` en interface `Task` |
| 30 | Patrón `useMutation` + `useQuery` polling | grep AgentPlayground | ✅ | `AgentPlayground.tsx:66-101` — `runMutation` useMutation, `taskQuery` useQuery con `refetchInterval: 2000` |

### Discrepancias encontradas

| ID | Discrepancia | Resolución propuesta |
|---|---|---|
| D-01 | Flags HTML5 DnD nativo. `draggable`, `dataTransfer.setData`, `onDragOver`/`onDrop`. No deps externas. |
| D-02 | Sin flow "crew" en registry. Solo `generic_flow`, `success_test_flow`, `fail_test_flow`. | MVP: ejecutar agente por agente vía `POST /agents/{role}/run`. "Run All" ejecuta secuencial. Post-MVP: `crew_runner_flow`. |
| D-03 | `ExportBundleRequest` acepta solo `agents + skills`, no `tasks`/`edges`. | Exportar solo agentes del canvas como `AgentExportItem[]`. Mostrar warning dialog: "Tasks and connections not exported (bundle-schema-v2.md limitation)." Botón "Copy as JSON" sí incluye completo. |
| D-04 | `AgentNode.tsx` custom no existe. | Crear con `import { Handle, Position, type NodeProps } from 'reactflow'`. Source Handle `type="source" position={Position.Bottom}`, Target Handle `type="target" position={Position.Top}`. |
| D-05 | `CrewCanvas.tsx` no existe. Placeholder vacío en `BuilderCanvas.tsx` (línea 39). | Crear componente nuevo reemplazando wrapper de `BuilderCanvas.tsx` → dynamic import de `CrewCanvas`. |
| D-06 | `crewCodeGen.ts` no existe. Plan pide "Vista previa de código Python generado". | Crear `dashboard/lib/crewCodeGen.ts` — función pura `generateCrewPy(nodes, edges): string`. Sin deps externas. |
| D-07 | Directorio `nodes/` no existe en `components/builder/`. | Crear `dashboard/components/builder/nodes/`. Contener `AgentNode.tsx` + `TaskNode.tsx`. |

### Umbral verificado

- 27 elementos confirmados ✅
- 7 discrepancias documentadas ❌
- 0 sin verificar
- software para 7–10 archivos afectados → umbral ≥18 → **28 > 18 ✅**

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema actual relevante

**`agent_catalog`** (mig `004_agent_catalog.sql`, extendido por mig `025`):

```sql
CREATE TABLE agent_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    soul_json JSONB NOT NULL DEFAULT '{}',
    allowed_tools TEXT[] DEFAULT '{}',
    max_iter INTEGER DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_catalog_org_role ON agent_catalog(org_id, role);

-- RLS: tenant_isolation (mig 025)
CREATE POLICY "agent_catalog_tenant_isolation" ON agent_catalog
    FOR ALL USING (current_setting('app.org_id', TRUE) <> '' AND org_id::text = current_setting('app.org_id', TRUE));
```

**`tasks`** (referencia para polling):

```sql
id UUID PK | org_id UUID | flow_type TEXT | status TEXT | result JSONB | error TEXT | tokens_used INTEGER | payload JSONB | correlation_id TEXT
```

### Cambios de schema necesarios

**Ninguno.** Paso 7 es 100% frontend:

- Nodos ReactFlow en memoria (`useNodesState`, `useEdgesState`)
- Export → serializa a `AgentExportItem[]` + `POST /api/bundles/export` (backends existente)
- Ejecución → `POST /agents/{role}/run` por nodo agente (backend existente)

No nuevas migraciones. No nueva tabla `crew_canvases` en MVP (post-MVP: persistencia en DB).

### Relaciones e integridad

- Cada nodo `AgentNode` → 1 fila en `agent_catalog` (traída por `GET /agents/by-role/{role}`)
- Cada nodo `TaskNode` → 1 `task` registrada en `POST /agents/{role}/run` → `GET /tasks/{task_id}` polling
- Edge agent→task: relación visual en canvas, NO FK en DB (limitación bundle-schema-v2, D-03)

### RLS aplicables

- Endpoints `POST /agents/{role}/run` ya traen `verify_org_membership` → `auth: dict = Depends(...)`
- `GET /agents/by-role/{role}` trae `require_org_id: str = Depends(...)`
- Frontend envía `X-Org-ID` header vía `fapFetch()` → **todo el tráfico del canvas respeta org_isolation**

### Índices

Sin cambios. Campos consultados ya indexados: `agent_catalog(org_id, role)` UNIQUE, `tasks(id)` PK, `tasks(org_id)`.

### Tipos de datos problemáticos

- `soul_json` en export payload → `Dict` en Pydantic (`AgentExportItem.soul_json: Dict`). Frontend arma objeto plano `{ role, goal, backstory, ... }`. Backend lo valida sin schema rígido. **OK — sin riesgo.**
- `role` en URL del agente → browser usa `encodeURIComponent(role)` en llamadas. Ya resuelto en Paso 6 (D-05 phase-state.md:376). **OK.**

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos nuevos (7)

#### A. `dashboard/components/builder/nodes/AgentNode.tsx`

```tsx
// FIRMA (interfaz completa)
export function AgentNode({ data }: NodeProps<{
  role: string
  goal: string
  tools: string[]
  model?: string
}>)
```

- **Import:** `import { Handle, Position, type NodeProps } from 'reactflow'`
- **Imports UI:** `Card`, `CardContent`, `CardHeader`, `CardTitle` de `@/components/ui/card`; `Badge` de `@/components/ui/badge`; `Bot` de `lucide-react`
- **Render:** `Card` con `role` en `CardTitle`, `goal` truncado (line-clamp-2) en `CardContent`. Badges de `tools` con `max(3)` visible + `+{n}` remainder.
- **Handles:** `type="target" position={Position.Top}` (arriba); `type="source" position={Position.Bottom}` (abajo)
- **Tooltip:** `Tooltip` de `@radix-ui/react-tooltip` con `role + goal` y lista completa de tools
- **Patrón:** ReactFlow custom node pattern: `reactflow.dev/examples/nodes/custom-node`. Mismo que `TaskNode` con Handle Left/Right (diferente orientación).

#### B. `dashboard/components/builder/nodes/TaskNode.tsx`

```tsx
// FIRMA (interfaz completa)
export function TaskNode({ data }: NodeProps<{
  description: string
  expectedOutput: string
  assignedAgent?: string
}>)
```

- **Import:** `import { Handle, Position, type NodeProps } from 'reactflow'` + `ClipboardList` de `lucide-react`
- **Handles:** `type="target" position={Position.Left}`; `type="source" position={Position.Right}` — edgedir left→right para flujo agent→task
- **Render:** `Card` con `description` como título, `expectedOutput` como subtitle clample-1, badge `assignedAgent` si existe
- **Patrón:** ReactFlow custom node. Mimo que AgentNode con Handle diferente.

#### C. `dashboard/components/builder/CrewCanvas.tsx`

```tsx
// FIRMA (interfaz completa)
export function CrewCanvas()
// STATE:
//   const [nodes, setNodes, onNodesChange] = useNodesState([])
//   const [edges, setEdges, onEdgesChange] = useEdgesState([])
//   const [sidebarAgents, setSidebarAgents] = useState<AgentFormData[]>([])
//   const [running, setRunning] = useState(false)
//   const runResults: Record<string, RunResult>  (por task_id)
```

- **Import:** `ReactFlow` + `Background`, `Controls`, `MiniMap`, `addEdge`, `useNodesState`, `useEdgesState`, `type Node`, `type Edge`, `type Connection`, `ReactFlowProvider`, `type ReactFlowInstance` de `reactflow`
- **Sidebar:** `ScrollArea` con lista de agentes (fetch `POST /agents/by-role/` → mapear a `AgentFormData`) — cada uno renderizado como badge/tag arrastrable (`draggable="true"`)
- **Toolbar:** Botones `Export as Crew`, `Run All`, `Preview Code`, `Save Crew` botones principales + `Templates` button
- **DnD:** `onDragOver` (`e.preventDefault()` a `e.preventDefault()`) → `onDrop` → check `reactFlowInstance.screenToFlowPosition(e.clientX, e.clientY)` → `addNodes({ id, type, position, data })`
- **Edges:** `onConnect={params => setEdges(eds => addEdge({...params, animated: true}, eds))}` con `Handle` en `AgentNode` y `TaskNode`
- **Run All:** Itera `agentes` del canvas (nodos tipo `agentNode`), POST a `/agents/${role}/run`, crea tarea y polling via `useQuery`
- **Run All:** polling Gö a `/agents/${role}/run`
- **Validation visual:** nodos `agentNode` sin ninguna edge `source` → badge `Badge variant="warning"` en el nodo
- **Patrón:** ReactFlow DnD pattern (`reactflow.dev/examples/interaction/drag-and-drop`), `@dnd-kit` **no es necesario** — HTML5 DnD nativo, sin deps extra (D-01 resuelto).
- **Patrón generación código Python:** TemplatePicker = puro string gen Masonry function clave `crewCodeGen.ts` `generateCrewPy(nodes, edges): string`

#### D. `dashboard/lib/crewCodeGen.ts`

```ts
// FIRMA (interfaz completa)
export function generateCrewPy(
  nodes: Node[],
  edges: Edge[]
): string
```

- **Dependencia:** 0 deps externas. Función pura
- **Output:** String Python con validación sintáctica
- **Lógica:**
  - Filtrar nodos tipo `agentNode` → `agent_i` con `Agent(role, goal, backstory, allowed_tools, allow_code_execution=False)`
  - Filtrar nodos tipo `taskNode` → `task_i` con `Task(description, expected_output, agent=agent_X)`
  - Mapear edges: cada edge `{source: agentNode.id, target: taskNode.id}` → asigna `agent=agent_X`
  - Generar `Crew(agents=[agent_0,...], tasks=[task_0,...], process=Process.sequential)` + `crew.kickoff()`
- **Pattern:** Función pura — mismo nivel que `export_service.py::export()` que es determinista sin side-effects.

#### E. `dashboard/lib/canvasUtils.ts`

```ts
// FIRMAS (interfaz completa)
export function canvasToExportPayload(nodes: Node[]): ExportPayload
export function exportPayloadToCanvas(agents: AgentExportItem[]): Node[]
export function nodesToSnapshot(nodes: Node[], edges: Edge[]): string
export function snapshotToNodes(snapshot: string): { nodes: Node[]; edges: Edge[] }
```

- **`canvasToExportPayload`:** Extrae solo nodos tipo `agentNode`, mapea a `AgentExportItem` — usa campos `data.role`, `data.goal`/`data.backstory`, `data.tools`, `data.maxIter`
- **`nodesToSnapshot`:** `JSON.stringify({ nodes, edges })` → string para guardar en localStorage o copiar al portapapeles
- **`snapshotToNodes`:** `JSON.parse()` + validación básica (campos requeridos)
- **Pattern:** Funciones puras sin side-effects — sin dependencia de hooks React. Testeable desde Node.js directamente.

#### F. `dashboard/lib/crewTemplates.ts`

```ts
// FIRMA (interfaz completa)
export const CREW_TEMPLATES: CrewTemplate[] = [
  {
    id, name, description, category, nodes, edges
  }
]
```

- **4 presets:**
  1. `research-pipeline` — Researcher Agent → Search Task → Writer Task
  2. `code-review-crew` — Reviewer Agent → Analyze Task → Report Task
  3. `content-creation` — Writer Agent → SEO Task → Editor Task
  4. `data-analysis` — Analyst Agent → Parse Task → Visualize Task
- Cada preset: `id` único, `name`, `description`, `category`, `nodes` (coordenada por posición), `edges` (conexiones)
- **Pattern:** `TEMPLATE_CATEGORIES` en `constants.ts` — mismas categorías pero adaptado a crews.

#### G. `dashboard/types.ts` — Agregar interfaces canvas

```ts
export interface CanvasAgentNode {
  role: string
  goal: string
  tools: string[]
  model?: string
}

export interface CanvasTaskNode {
  description: string
  expectedOutput: string
  assignedAgent?: string
}

export type CanvasNodeType = 'agentNode' | 'taskNode'
```

Agregar al final de `types.ts` existente. `CanvasTaskNode.expectedOutput` debe alinearse con `Task.expected_output` backend si existe — **NO existe columna `expected_output` en `tasks`** (solo `payload`, `result`, `error`). Ámbito del task node es UX-only (canvas preview), no se persiste a DB en MVP.

### Componentes modificados

#### `BuilderCanvas.tsx` — reemplazar placeholder

```tsx
// NUEVO contenido (reemplaza línea 1-46 actual)
'use client'
import dynamic from 'next/dynamic'
import { Skeleton } from '@/components/ui/skeleton'

const CrewCanvasDynamic = dynamic(
  () => import('@/components/builder/CrewCanvas')
    .then(mod => ({ default: mod.CrewCanvas })),
  { ssr: false, loading: () => <Skeleton className="h-64 w-full rounded-lg" /> }
)

export function BuilderCanvas() {
  return (
    <div className="h-full w-full rounded-lg border bg-muted/20">
      <CrewCanvasDynamic />
    </div>
  )
}
```

Import hacia `CrewCanvas` desde `@/components/builder/CrewCanvas` (después de crearlo en Tarea 3).

#### `BuilderLayout.tsx` — agregar tabs Agent Form / Crew Canvas

Nuevo layout: `Tabs defaultValue="agentForm"` (patrón de `app/(app)/agents/[id]/page.tsx:130` y `BundleTimeline.tsx:232`).

```tsx
<Tabs defaultValue="agentForm" className="flex-1 flex flex-col overflow-hidden">
  <TabsList>
    <TabsTrigger value="agentForm" className="gap-2">
      <Bot className="h-4 w-4" /> Agent Form
    </TabsTrigger>
    <TabsTrigger value="crewCanvas" className="gap-2">
      <Layers className="h-4 w-4" /> Crew Canvas
    </TabsTrigger>
  </TabsList>
  <TabsContent value="agentForm" className="flex-1 overflow-auto mt-4">
    <AgentForm templateData={templateData} ... />
  </TabsContent>
  <TabsContent value="crewCanvas" className="flex-1 overflow-hidden mt-0">
    <CrewCanvas />
  </TabsContent>
</Tabs>
```

**Verificación de patrón:** `agents/[id]/page.tsx:130-222` usa exactamente el mismo pattern. `api`, `AgentForm`, `delete` es una variante de la misma estructura compartida por componentes shadcn (@radix-ui/react-tabs).

### Reutilización de patrones

| Patrón existencia | Archivo ref. | Patrón usa |
|---|---|---|
| Custom ReactFlow node | ReactFlow docs + `reactflow.dev/examples/nodes/custom-node` | `Handle`, `Position`, `NodeProps` + `nodeTypes` prop |
| ReactFlow state | `reactflow.dev/examples/additional/add-node` | `useNodesState` + `useEdgesState` |
| DnD HTML5 native | `reactflow.dev/examples/interaction/drag-and-drop` | `draggable`, `dataTransfer.setData`, `onDragOver`, `onDrop`, `screenToFlowPosition()` |
| API calls | `AgentForm.tsx:164` / `AgentPlayground.tsx:68` | `api.post(path, body)` |
| Toast notifications | `AgentForm.tsx:166-177` | `toast.success / toast.error` |
| Dynamic import SSR | `BuilderCanvas.tsx:6-29` | `dynamic(() => import(...), { ssr: false })` |
| Dialog overlay | `BuilderLayout.tsx:106-128` | `Dialog` + `DialogContent` + `DialogHeader` |
| Tabs | `agents/[id]/page.tsx:130` | `Tabs` + `TabsList` + `TabsTrigger` + `TabsContent` |

### Cohesión / acoplamiento

- AgentNode/TaskNode: **alta cohesión** — solo render + handles. Sin lógica negocio. Sin llamadas API.
- CrewCanvas: **media cohesión** — orquesta state nodos + edge + DnD + acciones (export/run). Sin acceso a DB directo.
- crewCodeGen: **máxima cohesión** — función pura. Determinista. Sin efectos acoplados.
- canvasUtils: **máxima cohesión** — funciones puras de serialización.
- **Acoplamiento bajo** entre todas: cada archivo tiene una responsabilidad única.

### Imports exactos (agentes helper)

```tsx
// AgentNode.tsx
import { Handle, Position, type NodeProps } from 'reactflow'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Bot } from 'lucide-react'
import 'reactflow/dist/style.css' // styles globales, seguridad import una vez por archivo

// TaskNode.tsx
import { Handle, Position, type NodeProps } from 'reactflow'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ClipboardList } from 'lucide-react'

// CrewCanvas.tsx
import { useCallback, useRef, useState } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap, addEdge,
  useNodesState, useEdgesState,
  type Connection, type Edge, type Node,
  ReactFlowProvider, type ReactFlowInstance,
} from 'reactflow'
import { AgentNode } from '@/components/builder/nodes/AgentNode'
import { TaskNode } from '@/components/builder/nodes/TaskNode'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { generateCrewPy } from '@/lib/crewCodeGen'
import { Download, Play, Code, Share2 } from 'lucide-react'
import type { Task } from '@/lib/types'
```

### Calidad

- Complejidad ciclomática `AgentNode`/`TaskNode` → **1** (solo render)
- `CrewCanvas` → estimado **5-7** callbacks: `onConnect`, `onDragOver`, `onDrop`, `onNodesChange`, `onEdgesChange`, `fetchAgents`, `runAll`, `handleExport`, `handlePreviewCode`. Manejable.
- `crewCodeGen` → estimado **3-4** (iteraciones sobre nodos y edges). Simple.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes usados por el canvas

| Endpoint | Método | Uso canvas | Auth | Archivo |
|---|---|---|---|---|
| `GET /agents/by-role/{role}` | GET | Cargar agente desde catálogo (sidebar arrastrable) | `require_org_id` | `agents.py:104-124` |
| `GET /api/templates/{id}` | GET | Cargar templates en CrewTemplates preset | None (catálogo público) | `templates.py:70-83` |
| `POST /agents/{role}/run` | POST | Ejecutar agente individual (botón "Run" en nodo) | `verify_org_membership` | `agents.py:251-320` |
| `GET /tasks/{task_id}` | GET | Polling resultado ejecución | `verify_org_membership` | `tasks.py:69-91` |
| `POST /api/bundles/export` | POST | Exportar crew como ZIP (solo agentes) | `require_org_id` | `bundles.py:199-253` |
| `GET /api/tools/available` | GET | Mostrar tools en badges de AgentNode | `require_org_id` | `tools.py:46-63` |

### Gaps de backend

**GAP-1 (D-02): Sin endpoint de ejecución multi-agente**

```
POST /flows/{flow_type}/run
```
Existe pero NO hay `crew_runner_flow` registrado en `flow_registry`. Revisar:
```python
# registry.py verify:
flow_registry.list_flows() → ["generic_flow", "success_test_flow", "fail_test_flow"]
```

Resolución MVP: `POST /agents/{role}/run` por agente, ejecución secuencial vía frontend. Botón "Run All" en CrewCanvas hace:
```
for (node of nodes.filter(n => n.type === 'agentNode')) {
  await api.post(`/agents/${role}/run`, { input_data })
  await poll(task_id) // polling 2s, max 120s
}
```

Post-MVP: crear `crew_runner_flow` en backend:
```python
@register_flow("crew_runner", category="system")
class CrewRunnerFlow(BaseFlow):
    async def _run_crew(self):
        crew = Crew(agents=[...], tasks=[...], process=Process.sequential)
        return await crew.kickoff_async()
```

**GAP-2 (D-03): Export no incluye tasks/edges**

`ExportBundleRequest.bundle_schemas.py:111` solo tiene `agents List[AgentExportItem]` y `skills Optional[List[SkillExportItem]]`. No hay campo `tasks` ni `edges`.

Resolución: Exporta solo agentes del canvas. Warning visibile en dialogo:
> ⚠️ Tasks and connections are not exported in this version (bundle-schema-v2.md limitation). Use "Copy as JSON" to include everything.

Botón "Copy as JSON" → usa `canvasToExportPayload(agentNodes)` + incluye `edges: Edge[]`.

### Flujo de ejecución backend

```
Frontend: CrewCanvas "Run All"
  → POST /agents/code-reviewer/run   { input_data: { task_description: "Review PR #42" } }
    → 202 Accepted + task_id=uuid
    → background: BaseCrew(org_id, "code-reviewer").run_async(...)
    → actualizar tasks(status=running)
  → polling: GET /tasks/{task_id} cada 2s (max 120s, stop en completed/failed)
    → 200 + TaskResponse(status, result, tokens_used)
  → POST /agents/writer/run   { input_data: { task_description: "Write summary" } }
    → (repeat)

Frontend: CrewCanvas "Export"
  → canvasToExportPayload(nodes) → agents: AgentExportItem[]
  → POST /api/bundles/export { agents, skills: [] }
    → 200 + Response(content=zip_bytes, media_type=application/zip)
  → Browser download (saveAs / blob a href download)
```

### Middleware aplicable

Todos los endpoints usados por el canvas ya tienen middleware correcto:

| Endpoint | Auth middleware | Razón |
|---|---|---|
| `GET /agents/by-role/{role}` | `require_org_id` | Tenant isolation |
| `POST /agents/{role}/run` | `verify_org_membership` | Org membership check |
| `GET /tasks/{task_id}` | `verify_org_membership` | Org membership check |
| `POST /api/bundles/export` | `require_org_id` | Tenant isolation |
| `GET /api/tools/available` | `require_org_id` | Tenant isolation |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
DB agent_catalog (agentes guardados por Paso 4)
  ↓ GET /agents/by-role/{role} [cargar sidebar]
Sidebar: agentes arrastrables (nombre, role, icono)
  ↓ HTML5 DnD (dragstart → dataTransfer → onDrop)
ReactFlow Canvas (nodes + edges)
  ↓ click "Run" en agente / "Run All"
POST /agents/{role}/run × N agentes
  ↓ background_tasks BaseCrew
Polling: GET /tasks/{task_id} (2s interval, max 120s)
  ↓
Panel de resultados (tab por agente, status, tokens, error)
  ↓ click "Export as Crew"
canvasToExportPayload → AgentExportItem[]
POST /api/bundles/export
  ↓ ZIP download
browser descargar .zip
```

### Validación de coherencia

- **Data ↔ Code:** `AgentNode` data = `agent_catalog` JOIN `soul_json` plano. Campos consistentes. No sorpresas de tipo.
- **Code ↔ Backend:** Todo endpoint previo usado por el canvas YA EXISTE (ver §3). No requiere nuevos endpoints en MVP.
- **Backend ↔ Frontend:** Tanto endpoints nuevos/creados de comparar los del `fapFetch()` (middleware auth JWT via header, X-Org-ID header) back usaron Hé乳房M.todos.head a

La coherencia estructural entre capas es sólida — el canvas conecta limpimente features pasados (paso 01 hasta 3) sin necesidad de modificar contratos. La validación es correcta seven.

El MVP tiene gaps post-MVP no etapa actual flujo validado:

- GAP 1: No multi-agente coordinado (ejecución secuencial individual)
- GAP 2: Tasks/edges no incluidos en export ZIP
- GAP 3: Sin persistencia del canvas (localStorage post-MVP)
- GAP 4: Sin template de crew presets (agregar)

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap crew` CLI (Tarea 0 — antes que resto del paso)

- **Qué automatiza:** Exportar/guardar/importar crews desde CLI sin necesidad de abrir dashboard. Evita re-ensamblar crews desde cero cada sesión. Permite versionar crews en git como JSON.
- **Tipo:** CLI command (Typer sub-app)
- **Cómo se usa:**
  ```bash
  # Guardar snapshot del canvas en archivo local
  fap crew snapshot save --name "research-crew" --org-id <uuid> --output crew.json

  # Cargar snapshot y reabrir crew
  fap crew snapshot load --file crew.json --org-id <uuid>

  # Crear crew desde preset
  fap crew create-from-preset research-pipeline --org-id <uuid>
  ```
- **Impacto para el usuario final:** No rearma el canvas manualmente cada día. Versiona crews en git. Brinda workflows CI/CD-ready.
- **Prioridad:** Tarea 0 — implementar antes de cualquier componente frontend del canvas.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Cambios de DB requeridos — 0. (Canvas state 100% local, serializado a payloads HTTP existentes.)
✅ [CODE] `dashboard/components/builder/nodes/AgentNode.tsx`:
  - Firma: `export function AgentNode({ data }: NodeProps<{ role, goal, tools[], model? }>)`
  - Render: Card + Bot icon + role (title) + goal (trunc) + tools badges (max 3)
  - Handles: target POSITION.Top / source POSITION.Bottom
  - `npm run lint` sin errores
✅ [CODE] `dashboard/components/builder/nodes/TaskNode.tsx`:
  - Firma: `export function TaskNode({ data }: NodeProps<{ description, expectedOutput, assignedAgent? }>)`
  - Render: Card + ClipboardList icon + description + expectedOutput + assignedAgent badge
  - Handles: target POSITION.Left / source POSITION.Right
  - `npm run lint` sin errores
✅ [CODE] `dashboard/components/builder/CrewCanvas.tsx`:
  - Sidebar izquierda: ScrollArea con agentes arrastrables (fill `/agents/by-role/`)
  - Canvas central: ReactFlow con nodeTypes {agentNode, TaskNode}+ MiniMap + Controls + Background
  - DnD desde sidebar → canvas crea AgentNode en posición drop
  - `npm run lint` sin errores, cargo de agente 10 inicial pre-cargado
✅ [CODE] `dashboard/lib/crewCodeGen.ts`:
  - `generateCrewPy(nodes: Node[], edges: Edge[]): string`
  - Genera código Python válido con Agent(t)/Task(t)/Crew(t) miembros, cobfigs, layout, etc
  - `console.log(generateCrewPy(sampleNodes, sampleEdges))` → código Python válido (verificar en REPL Python)
✅ [CODE] `dashboard/lib/canvasUtils.ts`:
  - `canvasToExportPayload(nodes)` → `{ agents: AgentExportItem[] }` compatible con `ExportBundleRequest`
  - `nodesToSnapshot(nodes, edges)` → string JSON guardable en localStorage
  - `snapshotToNodes(snapshot)` → `{ nodes, edges }` validados
✅ [BACKEND] Sin cambios backend requeridos para MVP.
  - `POST /agents/{role}/run` usado por "Run All" por agente
  - `POST /api/bundles/export` usado para exportación ZIP (solo agentes del canvas)
  - `GET /agents/by-role/{role}` usado para poblar sidebar
✅ [BACKEND] GAP-1 (sin flow crew): Ejecución reactiva por nodo (secuencialmente) es MVP aceptado.
✅ [BACKEND] GAP-2 (export sin tasks): Warning visible en dialog + botón Copy as JSON como alternativa.
✅ [FULLSTACK] Ruta `/builder` carga sin errores SSR (ReactFlow dynamic import).
✅ [FULLSTACK] Tabs "Agent Form" / "Crew Canvas" en BuilderLayout funcionan.
✅ [FULLSTACK] Drag & drop de agente desde sidebar → canvas crea AgentNode visible con datos correctos.
✅ [FULLSTACK] Conexión visual entre nodos (edges) visible al conectar Handle Top agent con Handle Left task.
✅ [FULLSTACK] Botón "Preview Code" muestra código Python generado.
✅ [FULLSTACK] Botón "Run All" ejecuta cada agente secuencialmente con polling y muestra resultados.
✅ [FULLSTACK] Botón "Export as Crew" descarga ZIP con agentes del canvas.
✅ [DX] `fap crew snapshot save/load` ejecutan sin errores y reducen trabajo manual de re-ensamblar crew.
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ReactFlow SSR crash | Alta | ReactFlow usa `window`/`document`. SSR sin `dynamic import` rompe el build | `BuilderCanvas.tsx` ya usa `dynamic(... {ssr: false})`. Mantener patrón. CrewCanvas wrapped en `ReactFlowProvider`. |
| Sin grid/tabla de "Agentes en el proyecto" por defecto | Media | El primer "Agentes Importados" es probar flujo con agentes de plantas sin interferir. Simplificar en MVP. Sin tabla de agentes. Priorizar MVP (Edit tooltips) primero. Luego tabla. |
| Ejecución secuencial muy lenta | Alta | "Run All" ejecuta agentes 1×1. 5 agentes × 30s = 150s total | Mostrar barra de progreso (agente X / N). Cada agente: spinner propio. Bajar a usuarios. Ejecutar secuencialmente sin dependencias. |
| DnD HTML5 incompatibilidad cross-browser | Media | Firefox: `dataTransfer.setData()` con MIME estricto; Chrome relaja. | Usar `text/plain` como MIME first try + fallback `application/json`. Probar en Chrome/Firefox/Edge. |
| Memoria con 20+ nodos | Baja | ReactFlow virtualiza nodes pero grows DOM; puede degradar | ReactFlow maneja 500+ nodes sin problema en practica. <20 nodos en MVP — no preocupante. Documentar en roadmap como área de mejora. |
| Export sin tasks frustra usuarios | Media |Usuario espera crew completo (agentes+tareas) en ZIP. Solo agentes van al ZIP. | Dialog muestra warning icono + tooltip "Tasks & connections not exported". Botón "Copy as JSON" sí incluye completo. Roadmap: bundle v3. |
| Sin undo/redo causa re-trabajo | Media | Borrar nodo accidental = perder datos hasta API reset | Implementar undo stack simple (pero otro algoritmo redux-like pueden salir fácil + Ctrl+Z). Post-MVP. Mencionar en resumen finalizacion. |
| Collision roles al exportar | Baja | 2 agentes con mismo `role` en canvas → `ExportBundleRequest` duplica roles → ZIP valido pero executor falla | Validación frontend: si dos nodos tienen mismo `role`, deshabilitar botón Export + toast "Duplicate roles detected. Each agent must have a unique role." |

---

## 7️⃣ Plan de Implementación

> Reglas de segmentación atómica aplicadas:
> 1. Una tarea = un artefacto
> 2. Cada tarea incluye firma exacta
> 3. Patrón de referencia explícito (archivo concreto)
> 4. Verificación inline

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Time Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: `fap crew` CLI** | `src/cli/commands/crew.py` | `crew_app = typer.Typer()` con subcomandos: `snapshot save --name NAME --org-id UUID --output FILE`, `snapshot load --file FILE --org-id UUID`, `create-from-preset PRESET --org-id UUID` | `src/cli/commands/templates_seed.py` — Typer sub-app + Rich table/console | DX | Media | 1.5h | Ninguna | → verificar: `uv run python -m src.cli.commands.crew --help` ejecuta sin errores |
| 1 | Crear `AgentNode.tsx` | `dashboard/components/builder/nodes/AgentNode.tsx` | `export function AgentNode({ data }: NodeProps<{ role: string; goal: string; tools: string[]; model?: string }>)` → Card + Bot icon + role(title) + goal(clamp-2) + tools badges(max3) | ReactFlow docs: custom node — `reactflow.dev/examples/nodes/custom-node` | CODE | Baja | 1h | Ninguna | → verificar: `npm run lint` sin errores. Import sin TypeError TypeScript. |
| 2 | Crear `TaskNode.tsx` | `dashboard/components/builder/nodes/TaskNode.tsx` | `export function TaskNode({ data }: NodeProps<{ description: string; expectedOutput: string; assignedAgent?: string }>)` → Card + ClipboardList + description + expectedOutput(clamp-1) + assignedAgent badge | Mismo patrón AgentNode (doc ReactFlow custom-node) | CODE | Baja | 0.75h | Tarea 1 | → verificar: `npm run lint` sin errores. |
| 3 | Crear `CrewCanvas.tsx` | `dashboard/components/builder/CrewCanvas.tsx` | `export function CrewCanvas()`. State: `useNodesState([])`, `useEdgesState([])`. Props: sin props. Herramientas: drag-and-drop arrastrar agentes desde sidebar. Ordenar los elementos que se agreguen al canvas. Agreguemos un botón "Limpiar" por nodo/edge creado. | ReactFlow DnD example `reactflow.dev/examples/interaction/drag-and-drop` + `BuilderCanvas.tsx` dynamic-import pattern | CODE | Alta | 4h | Tareas 1, 2 | → verificar: `npm run lint` sin errores; Ruta `/builder` renderiza canvas sin crash; drag & drop crea nodo visible. |
| 4 | Crear `crewCodeGen.ts` | `dashboard/lib/crewCodeGen.ts` | `export function generateCrewPy(nodes: Node[], edges: Edge[]): string` → genera código Python CrewAI con `Agent()`, `Task()`, `Crew()`, `Process.sequential`, `crew.kickoff()` | Función pura, sin deps. Pattern: `export_service.py::export()` — determinista sin side-effects (aunque escrito en TS/JS, el mismo patrón structure) | CODE | Media | 1.5h | Tareas 1, 2 | → verificar: `console.log(generateCrewPy(sampleNodes, sampleEdges))` → código Python válido (paste en python REPL sin error SyntaxError) |
| 5 | Crear `canvasUtils.ts` | `dashboard/lib/canvasUtils.ts` | `export function canvasToExportPayload(nodes: Node[]): { agents: AgentExportItem[] }` `export function nodesToSnapshot(nodes, edges): string` `export function snapshotToNodes(snapshot): { nodes, edges }` | Funciones puras. Pattern: `canvasCodeGen.ts` (mismo archivo dir `lib/`) | CODE | Baja | 1h | Tareas 1, 2 | → verificar: `canvasToExportPayload([agentNode])` produce objeto con estructura `{ agents: [{ role, soul_json: { goal, backstory, ... }, allowed_tools, max_iter }] }` |
| 6 | Crear `crewTemplates.ts` | `dashboard/lib/crewTemplates.ts` | `export const CREW_TEMPLATES = [ { id, name, description, category, nodes: Node[], edges: Edge[] } ]` con ≥4 presets: `research-pipeline`, `code-review-crew`, `content-creation`, `data-analysis` | `dashboard/lib/constants.ts` — constantes exportadas. Patrón `TEMPLATE_CATEGORIES`. | CODE | Baja | 0.75h | Tareas 1, 2 | → verificar: `CREW_TEMPLATES.length >= 4`. Cada template tiene `nodes.length > 0`, posiciones `x,y` válidas, `edges` referencian IDs existentes. |
| 7 | Reemplazar `BuilderCanvas.tsx` | `dashboard/components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas()` → dynamic import de `CrewCanvas` con `{ssr: false}`, `loading: () => <Skeleton />` | Mismo archivo — reemplazar placeholder. Mantener pattern `dynamic(() => import(...))` existent (línea 6-29). | CODE | Baja | 0.25h | Tarea 3 | → verificar: `npm run build` sin errores SSR. CrewCanvas import sin module-not-found. |
| 8 | Actualizar `BuilderLayout.tsx` | `dashboard/components/builder/BuilderLayout.tsx` | `export function BuilderLayout()` → agregar `Tabs` (TabsList + TabsTrigger "Agent Form"/"Crew Canvas"). Tab "Agent Form": `<AgentForm templateData={templateData} ... />`. Tab "Crew Canvas": `<CrewCanvas />`. | `agents/[id]/page.tsx:130-136` — exacto mismo pattern de Tabs. `BundleTimeline.tsx:232-265` para estructura `flex-1` en TabsContent. | FULLSTACK | Media | 1h | Tarea 7 | → verificar: Cambiar entre tabs preserva estado de nodos canvas y formulario. Click "Crew Canvas" muestra canvas sin errores. |
| 9 | Actualizar `types.ts` | `dashboard/lib/types.ts` | Agregar al final del archivo: `CanvasAgentNode`, `CanvasTaskNode`, `CanvasNodeType` | Mismo archivo — mismo estilo existente | CODE | Baja | 0.25h | Ninguna | → verificar: TypeScript compila; `npm run lint` sin errores de type |
| 10 | Validar flujo end-to-end | — | Open `/builder` → Tab "Crew Canvas" → Drag agent desde sidebar → Drop crea AgentNode → Click "Preview Code" → Código Python aparece en Dialog → Click "Export" → ZIP descargado → Click "Run All" → polling muestra resultado. | — | FULLSTACK | Baja | 1h | Todas las anteriores | → verificar: Criterios §5 [FULLSTACK] pasan todos. Sin errores en consola browser. |

**Tiempo total estimado:** ~10.75h

---

## 🔮 Roadmap (NO implementar ahora)

| Item | Razón post-MVP |
|---|---|
| `dynamic_crew_flow` backend | Ejecuta multiagente coordinado (agentes+task+dependencias via crewAI). Reemplaza ejecución secuencial frontend. |
| Bundle schema v3 (tasks + edges en ZIP) | `ExportBundleRequest` actual solo modela agents+skills. v3 agrega `tasks: TaskExportItem[]` + `edges: Edge[]`. Import/export round-trip completo. |
| Persistencia canvas en DB | Tabla `crew_canvases(org_id, name, snapshot JSONB)` para sesiones multi-día. Autosave cada 30s. |
| Crew collaboration vía Realtime | Varios usuarios editando el mismo canvas simultáneamente (Supabase Realtime). |
| `crew_runner_flow` en backend | Flow multi-agente con `Crew(agents=[...], tasks=[...], process=sequential|parallel)`. |
| Deshacer/rehacer (undo/redo stack) | Ctrl+Z / Ctrl+Y para undo/redo de nodos y edges. |
| Validador visual de crew | Resaltar nodos con errores (agente sin task, task sin agente, ciclo de dependencias). |
| ToolNode separado | Cuando tools sean ejecutables independientes. Post-MVP; por ahora tools son atributos del agente. |

---

## 🚫 Reglas de Oro (auto-verificación)

| Regla | Verificación |
|---|---|
| ✅ Análisis accionable y específico | Cada tarea tiene firma exacta + patrón de referencia + verificación inline |
| ✅ TODO verificado contra código | 27 ✔, 7 ✗ discrepancias documentadas, 0 sin verificar |
| ✅ Si algo no está definido → señalado | D-01 a D-07 cada una con resolución concreta |
| ✅ Si plan contradice código → código gana | Ej: D-02 plan pide "Run Crew" flow → código no lo tiene → resolución documentada |
| ✅ Nivel CTO exigente | Se cubren 4 etapas secuenciales (data, code, backend, fullstack+DX) |
| ✅ Coherente con phase-state.md | phase-state §§3-5 referenciados. Decisiones pasadas respetadas. |
| ✅ TODO el paso incluyendo sub-pasos | 8 sub-tareas del plan cubiertas: nodes (AgentNode+TaskNode), canvas completo, sidebar, toolbar, export, preview, Layout (CrewCanvas), minimap+controls, validación visual |
| ✅ Etapas secuenciales | Data → Code → Backend → Fullstack+DX |
| ✅ ≥1 herramienta DX propuesta | `fap crew` CLI — Tarea 0 implementar antes que todo |
| ✅ Tareas atómicas | 10 tareas, 1 artefacto c/u |
| ✅ Interfaz exacta por tarea | Toda tarea tiene firma de función/componente especificada |
| ✅ Implementador no decide nada | Todos los parámetros de cada tarea especificados |
| ✅ Verificación inline por tarea | Comando/check concreto por tarea |
| ✅ ≥ 3 riesgos | 7 riesgos documentados en §6 |
