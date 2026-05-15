# 🧠 Análisis Técnico — Paso 07 (dsp)

> **Agente:** dsp | **Fecha:** 2026-05-15 | **Fase:** guiAgentGenerator
> **Paso:** Canvas visual — ensamblaje de crews

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `reactflow` v11 instalado | grep `package.json` | ✅ | `dashboard/package.json:41` — `"reactflow": "^11.11.4"` |
| 2 | `BuilderCanvas.tsx` existe | ls `dashboard/components/builder/` | ✅ | `BuilderCanvas.tsx:1-46` — placeholder vacío, node≡[], edge≡[] |
| 3 | `BuilderLayout.tsx` split 60/40 | grep layout | ✅ | `BuilderLayout.tsx:70` — `lg:grid-cols-[60%_40%]` |
| 4 | `AgentForm.tsx` existe con 11 campos | grep form | ✅ | `AgentForm.tsx:30-41` — zod schema con role/goal/backstory/llmProvider/llmModel/allowedTools/maxIter/verbose/reasoning/injectDate/memory |
| 5 | `agent_catalog` tabla existe | grep migrations | ✅ | `supabase/migrations/004_agent_catalog.sql:6-17` — schema con id, org_id, role, soul_json, allowed_tools, max_iter |
| 6 | RLS `agent_catalog_tenant_isolation` | grep RLS | ✅ | `supabase/migrations/025_agent_catalog_rls_update.sql:11-15` — service_role OR org_id::text = current_org_id() |
| 7 | `POST /api/bundles/export` existe | grep bundles.py | ✅ | `bundles.py:199-253` — `ExportBundleRequest` con `agents: List[AgentExportItem]` |
| 8 | `AgentExportItem` schema | grep bundle_schemas.py | ✅ | `bundle_schemas.py:102-108` — role, soul_json, allowed_tools, max_iter |
| 9 | `POST /flows/{flow_type}/run` existe | grep flows.py | ✅ | `flows.py:142-186` — `RunFlowRequest` + `RunFlowResponse` + background_tasks |
| 10 | `POST /agents/{role}/run` existe | grep agents.py | ✅ | `agents.py:251-320` — `RunAgentRequest` + `_execute()` background |
| 11 | `BaseCrew` existe con multi-agent soporte | grep base_crew.py | ✅ | `base_crew.py:56-265` — `__init__(org_id, role)`, `run()`, `run_async()` |
| 12 | Sidebar "Builder" en nav | grep nav-main.tsx | ✅ | `nav-main.tsx:50` — `{ title: 'Builder', url: '/builder', icon: Wand2 }` |
| 13 | `POST /agents` endpoint (save) | grep agents.py | ✅ | `agents.py:51-101` — `AgentCreate` + upsert via TenantClient |
| 14 | shadcn/ui `Dialog` component | ls ui/ | ✅ | `dashboard/components/ui/dialog.tsx` — `DialogContent`, `DialogHeader`, `DialogTitle` |
| 15 | shadcn/ui `Sheet` component | ls ui/ | ✅ | `dashboard/components/ui/sheet.tsx` — `SheetContent`, `SheetHeader`, `SheetTitle` |
| 16 | `@dnd-kit/core` o `react-dnd` instalado | grep package.json | ❌ | **DISCREPANCIA**: Ninguno en `dashboard/package.json`. Plan asume drag-drop sin verificar. |
| 17 | Flow tipo "crew" registrado | grep flows registry | ❌ | **DISCREPANCIA**: Solo `generic_flow`, `success_test_flow`, `fail_test_flow`. No hay flow multi-agente. Plan dice "Run Crew vía POST /flows/{flow_type}/run" — flow_type no existe. |
| 18 | Custom node ReactFlow (AgentNode, TaskNode, ToolNode) | grep builder/ | ❌ | **DISCREPANCIA**: No existen. Directorio `builder/` solo tiene `AgentForm`, `AgentPlayground`, `BuilderCanvas`, `BuilderLayout`, `TemplatePicker`, `ToolMultiSelect`. |
| 19 | Sidebar con items arrastrables | grep sidebar | ❌ | **DISCREPANCIA**: `app-sidebar.tsx` + `nav-main.tsx` son nav estática. Sin draggable items. |
| 20 | `@radix-ui/react-popover` | grep package.json | ❌ | **NO INSTALADO**. Tooltip sí (v1.2.8) pero popover no. Para tooltips en nodos se puede usar tooltip existente. |
| 21 | `Tasks` table en DB | grep migrations | ✅ | `001_set_config_rpc.sql` onw — tasks existe con id, org_id, flow_type, status, result, error, tokens_used |
| 22 | `BaseFlow` clase abstracta | grep base_flow.py | ✅ | `base_flow.py:61-446` — `validate_input()`, `_run_crew()`, `execute()`, `create_task_record()` |
| 23 | `FlowRegistry` singleton | grep registry.py | ✅ | `registry.py:370` — `flow_registry = FlowRegistry()` |
| 24 | Generador Python code | grep codebase | ❌ | **DISCREPANCIA**: No existe. Plan pide "Vista previa de código Python generado" — requiere generador nuevo. |
| 25 | `MiniMap` + `Controls` de ReactFlow | grep BuilderCanvas | ✅ | `BuilderCanvas.tsx:14-16` — `Background`, `Controls`, `MiniMap` usados en placeholder |
| 26 | `zod` v4 instalado | grep package.json | ✅ | `dashboard/package.json:46` — `"zod": "^4.4.3"` |
| 27 | `api.get()` y `api.post()` pattern | grep api.ts | ✅ | `dashboard/lib/api.ts:54-76` — `fapFetch()` con auth JWT + X-Org-ID header |
| 28 | `ExportBundleRequest` sin tasks/edges | grep bundle_schemas.py | ❌ | **DISCREPANCIA**: `ExportBundleRequest` solo acepta `agents` + `skills`. No hay campo para `tasks` ni `edges`. Bundle schema v2 no modela relaciones agent↔task. |
| 29 | `TaskResponse` con `tokens_used` | grep types.ts | ✅ | `dashboard/lib/types.ts:8` — `tokens_used: number` en interface Task |
| 30 | `useMutation` + `useQuery` polling pattern | grep AgentPlayground | ✅ | `AgentPlayground.tsx:66-101` — `runMutation` + `taskQuery` refetchInterval 2s |

### Discrepancias encontradas

| ID | Discrepancia | Resolución |
|---|---|---|
| D1 | Sin librería drag-and-drop (`@dnd-kit`, `react-dnd`). Plan asume sidebar con items arrastrables. | ReactFlow v11 soporta HTML5 DnD nativo (`draggable`, `onDragStart`, `onDragOver`, `onDrop`). No instalar deps externas. Implementar sidebar con `draggable="true"` + `data-drag-type` attribute. |
| D2 | Sin flow "crew" en FlowRegistry. Plan dice "Run Crew vía POST /flows/{flow_type}/run". No hay flow multi-agente registrado. | MVP: Ejecutar agentes individualmente vía `POST /agents/{role}/run`. Botón "Run All" ejecuta cada agente secuencialmente con su task. Post-MVP: crear `dynamic_crew_flow`. |
| D3 | `ExportBundleRequest` no incluye `tasks` ni `edges`. Bundle schema v2 solo modela agents + skills. | Exportar solo agentes del canvas como `AgentExportItem[]`. Tasks/edges perdidos en export (limitación bundle v2). Documentar en UI con tooltip "Tasks and connections are not exported in this version". |
| D4 | Sin generador de código Python. Plan pide "Vista previa de código Python generado". | Implementar `generateCrewPy()` función `utils/crewCodeGen.ts` — genera string Python con Agent/Task/Crew de CrewAI. Puro frontend, sin backend. |
| D5 | Sin custom ReactFlow nodes (`AgentNode.tsx`, `TaskNode.tsx`, `ToolNode.tsx`). | Crear nodos custom usando `Handle` + `NodeProps` de reactflow v11. Patrón documentado en docs reactflow: `nodeTypes` prop en `<ReactFlow>`. |
| D6 | ToolNode mencionado en plan pero no definido. Herramientas son atributo de agente, no nodo independiente. | No crear ToolNode separado. Mostrar tools como badge/chip dentro de AgentNode. Redundante tener nodo tool. |
| D7 | `@radix-ui/react-popover` no instalado (para mostrar tooltips/details en nodos). | Usar `@radix-ui/react-tooltip` v1.2.8 ya instalado para tooltips simples. Usar `@radix-ui/react-dialog` para edición inline de nodo. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema actual relevante

**`agent_catalog`** (mig 004 + 025):
```sql
id UUID PK DEFAULT gen_random_uuid()
org_id UUID FK→organizations(id) ON DELETE CASCADE
role TEXT NOT NULL
is_active BOOLEAN DEFAULT TRUE
soul_json JSONB NOT NULL DEFAULT '{}'
allowed_tools TEXT[] DEFAULT '{}'
max_iter INTEGER DEFAULT 5
created_at TIMESTAMPTZ DEFAULT now()
updated_at TIMESTAMPTZ DEFAULT now()
UNIQUE(org_id, role)
```

**`tasks`** (schema existente):
```sql
id UUID PK
org_id UUID
flow_type TEXT
status TEXT  -- pending|running|completed|failed|awaiting_approval|rejected|cancelled
result JSONB
error TEXT
tokens_used INTEGER
payload JSONB
correlation_id TEXT
```

### Cambios de schema necesarios

**Ninguno.** Canvas state es completamente local (ReactFlow `useNodesState` + `useEdgesState`). Al exportar/ejecutar se serializa a payloads HTTP existentes (`AgentExportItem` → `POST /api/bundles/export`, `RunAgentRequest` → `POST /agents/{role}/run`).

### Tipos de datos

Todos los campos usados ya existen en schemas de backend Pydantic:
- `AgentExportItem` (`bundle_schemas.py:102-108`): role, soul_json, allowed_tools, max_iter
- `RunAgentRequest` (`agents.py:38-41`): input_data: Dict
- `ExportBundleRequest` (`bundle_schemas.py:111-116`): agents, skills, bundle_name

### Índices

No nuevos necesarios. Canvas state es efímero (local).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos (4 archivos)

#### A. `AgentNode.tsx`
- **Firma:** `export function AgentNode({ data }: NodeProps)`
- **ReactFlow import:** `import { Handle, Position, type NodeProps } from 'reactflow'`
- **Props data:** `{ role: string, goal: string, tools: string[], model?: string, onEdit?: () => void }`
- **Render:** Card con `role` (title), `goal` (truncated subtitle), `tools` (badges). Source Handle bottom, Target Handle top.
- **Patrón referencia:** ReactFlow docs: custom node with `Handle` component. Similar a [reactflow.dev examples custom-node](https://reactflow.dev/examples/nodes/custom-node).
- **Ejemplo uso:**
```tsx
import { AgentNode } from '@/components/builder/nodes/AgentNode'

const nodeTypes = { agentNode: AgentNode }
<ReactFlow nodeTypes={nodeTypes} nodes={nodes} edges={edges} />
```

#### B. `TaskNode.tsx`
- **Firma:** `export function TaskNode({ data }: NodeProps)`
- **ReactFlow import:** `import { Handle, Position, type NodeProps } from 'reactflow'`
- **Props data:** `{ description: string, expectedOutput: string, assignedAgent?: string }`
- **Render:** Card con `description` (title), `expectedOutput` (truncated), badge del agente asignado. Source Handle right, Target Handle left (para conexión agent→task).
- **Patrón referencia:** Mismo que AgentNode.
- **Ejemplo uso:** Igual, agregar `taskNode: TaskNode` a `nodeTypes`.

#### C. `ToolNode.tsx`
- **SUPRIMIDO** (D6): Las tools son atributo del agente, no nodo independiente. Mostrar como badges dentro de AgentNode.
- No crear este archivo.

#### D. `CrewCanvas.tsx`
- **Firma:** `export function CrewCanvas()`
- **State:** `useNodesState([])`, `useEdgesState([])`, `onConnect`, `onDragOver`, `onDrop`
- **Integración:** Reemplaza `BuilderCanvas` placeholder. Sidebar izquierda con agentes arrastrables. Canvas central ReactFlow con nodeTypes: `{ agentNode: AgentNode, taskNode: TaskNode }`.
- **Props sidebar data:** `agents: AgentFormData[]` (de `agent_catalog`), permite crear nuevas tareas inline.
- **Botones:** "Export as Crew" → serializa grafo + llama `api.post('/api/bundles/export')`. "Run All" → ejecuta cada agente vía `api.post('/agents/${role}/run')`. "Preview Code" → `generateCrewPy()`.
- **Drag-and-drop:** HTML5 nativo. Sidebar items con `draggable="true"`, `onDragStart={e => e.dataTransfer.setData('application/reactflow', type)}`. Canvas con `onDragOver`, `onDrop` → `addNodes`.
- **Patrón referencia:** ReactFlow DnD example: https://reactflow.dev/examples/interaction/drag-and-drop
- **Ejemplo uso:**
```tsx
<CrewCanvas />
```

### Componente modificado: `BuilderCanvas.tsx`

De placeholder vacío a:
```tsx
'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from '@/components/ui/skeleton'

const CrewCanvasDynamic = dynamic(
  () => import('@/components/builder/CrewCanvas').then(mod => ({ default: mod.CrewCanvas })),
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

### Componente modificado: `BuilderLayout.tsx`

- Reemplazar `BuilderCanvas` import: de `@/components/builder/BuilderCanvas` a `@/components/builder/CrewCanvas`
- Agregar header al panel derecho con tabs: "Agent Form" | "Crew Canvas" (tabs @radix-ui/react-tabs ya instalado v1.1.2)

### Utilidad nueva: `crewCodeGen.ts`

- **Firma:** `export function generateCrewPy(nodes: Node[], edges: Edge[]): string`
- **Output:** String con código Python válido CrewAI.
- **Lógica:** Itera nodos tipo `agentNode` → genera `Agent(...)`. Itera nodos tipo `taskNode` → genera `Task(...)`. Edges → asigna `agent=` en Task.
- **Ejemplo output:**
```python
from crewai import Agent, Task, Crew, Process

agent_0 = Agent(
    role="Code Reviewer",
    goal="Review pull requests for security issues",
    backstory="Senior security engineer with 10 years experience",
    allow_code_execution=False,
)

task_0 = Task(
    description="Review the code",
    expected_output="Security report",
    agent=agent_0,
)

crew = Crew(agents=[agent_0], tasks=[task_0], process=Process.sequential)
result = crew.kickoff()
```

### Utilidad nueva: `canvasUtils.ts`

- **Firma:** `export function canvasToExportPayload(nodes: Node[]): ExportBundleRequest`
- **Firma:** `export function exportPayloadToCanvas(agents: AgentExportItem[]): Node[]`
- Convierte entre estado ReactFlow y payloads de API.

### Types nuevos (`types.ts`)

Agregar:
```typescript
export interface CanvasAgentNode {
  role: string
  goal: string
  backstory: string
  tools: string[]
}

export interface CanvasTaskNode {
  description: string
  expectedOutput: string
  assignedAgent?: string
}

export type CanvasNodeType = 'agentNode' | 'taskNode'
```

### Imports exactos

```typescript
// AgentNode.tsx
import { Handle, Position, type NodeProps } from 'reactflow'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Bot } from 'lucide-react'

// TaskNode.tsx
import { Handle, Position, type NodeProps } from 'reactflow'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ClipboardList } from 'lucide-react'

// CrewCanvas.tsx
import { useCallback, useRef, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  ReactFlowProvider,
  type ReactFlowInstance,
} from 'reactflow'
import { AgentNode } from '@/components/builder/nodes/AgentNode'
import { TaskNode } from '@/components/builder/nodes/TaskNode'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { generateCrewPy } from '@/lib/crewCodeGen'
import { Download, Play, Code, Share2 } from 'lucide-react'
```

### Patrones de código

1. **ReactFlow custom node:** `NodeProps` generic con `data`. `Handle` con `Position.Top`/`Bottom`/`Left`/`Right`. `type` definido en `nodeTypes` map.
2. **ReactFlow state:** `useNodesState([])`, `useEdgesState([])`. `onConnect` con `addEdge`. `onDrop` con `reactFlowInstance.screenToFlowPosition()`.
3. **API calls:** `api.get()` para fetch, `api.post()` para mutations. Mismo patrón que `AgentForm` y `AgentPlayground`.
4. **Toast notifications:** `sonner` `toast.success()` / `toast.error()`.
5. **Dynamic import SSR:** `dynamic(() => import('...'), { ssr: false })` para ReactFlow.
6. **Dialog overlay:** `@radix-ui/react-dialog` via shadcn `Dialog` para preview code + export summary.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes usados

| Endpoint | Método | Uso en Canvas | Archivo |
|---|---|---|---|
| `GET /agents/by-role/{role}` | GET | Cargar config de agente desde catálogo (sidebar) | `agents.py:104-124` |
| `POST /agents/{role}/run` | POST | Ejecutar agente individual (Run All) | `agents.py:251-320` |
| `GET /tasks/{task_id}` | GET | Polling resultado ejecución | `tasks.py` |
| `POST /api/bundles/export` | POST | Exportar crew como ZIP | `bundles.py:199-253` |
| `GET /api/tools/available` | GET | Mostrar tools disponibles en badges de nodo | `tools.py:46-63` |

### Gaps de backend

**GAP-1: Sin endpoint para ejecutar crew multi-agente**

`POST /flows/{flow_type}/run` existe pero NO hay `crew_runner` flow registrado. Los flows registrados son: `generic_flow`, `success_test_flow`, `fail_test_flow`.

**Resolución MVP:** Ejecutar agentes individualmente vía `POST /agents/{role}/run`. Cada agente recibe su task como `input_data.task_description`. No hay sincronización entre agentes (sin dependencias). Botón "Run All" ejecuta secuencial y muestra resultados individuales.

**Resolución Post-MVP:** Crear `dynamic_crew_flow` en backend que acepte `{ agents: AgentCreate[], tasks: TaskDefinition[] }` y construya un `Crew(agents=[...], tasks=[...], process=Process.sequential)`.

**GAP-2: Export no preserva tasks/edges**

`ExportBundleRequest` solo tiene `agents` y `skills`. No incluye `tasks` ni `edges`.

**Resolución MVP:** Exportar solo agentes del canvas como `AgentExportItem[]`. Tasks/edges se pierden. Info mostrada en dialog export: "Tasks and connections are not included in the exported bundle (bundle-schema-v2.md limitation)."

### Flujo de ejecución

```
Canvas → "Run All" click
  → POST /agents/{role_1}/run { input_data: { task_description: task_1.description } }
    → polling GET /tasks/{task_id_1} cada 2s
  → POST /agents/{role_2}/run { input_data: { task_description: task_2.description } }
    → polling GET /tasks/{task_id_2} cada 2s
  → ...
  → Mostrar resultados en panel (ej: tabs por agente)
```

### Flujo de exportación

```
Canvas → "Export" click
  → canvasToExportPayload(nodes)
    → POST /api/bundles/export { agents: AgentExportItem[], skills: [] }
      → respuesta: ZIP blob
        → descarga browser (saveAs)
```

### Error handling

| Error | Backend response | Frontend handling |
|---|---|---|
| Agente no encontrado | 404 `"Agent '{role}' not found"` | Toast error + badge rojo en nodo |
| Ejecución falla | task status='failed' con error | Mensaje en panel resultados + badge error |
| Export sin agentes | 422 `agents: min_length=1` | Validación frontend: deshabilitar botón si 0 agentes |
| Export sin goal/backstory | 422 `soul_json.goal required` | Validación frontend: toast "Add goal to agent {role}" |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
DB (agent_catalog)
  ↓ GET /agents/by-role/{role}
Sidebar (lista agentes arrastrables)
  ↓ HTML5 drag
Canvas ReactFlow (agentes + tareas + edges)
  ↓ botón "Run All"
POST /agents/{role}/run × N agentes
  ↓ polling GET /tasks/{id}
Panel de resultados (tabs por agente)
  ↓ botón "Export"
POST /api/bundles/export
  ↓ ZIP download
Archivo .zip (bundle-schema-v2.md compatible)
  ↓ POST /api/bundles/import
DB agent_catalog (agentes importados)
```

### Validación de coherencia

- **Data ↔ Code:** Los nodos en canvas reflejan `agent_catalog` (role, goal, backstory, tools). Al ejecutar, se pasan a `BaseCrew` que los carga desde DB. Consistente.
- **Code ↔ Backend:** `POST /agents/{role}/run` ya existe. Solo falta multi-agente — MVP ejecuta secuencial. Sin nuevo endpoint requerido en MVP.
- **Backend ↔ Frontend:** `api.get()`/`api.post()` ya configurado con auth JWT + X-Org-ID. Mismo patrón que AgentForm/AgentPlayground. Consistente.
- **MVP coherencia:** El usuario puede arrastrar agentes existentes del catálogo al canvas, asignarles tareas, conectar, ejecutar individualmente, y exportar agentes como bundle. El valor principal es la visualización y organización de crews.

### Gaps UX

1. **Sin persistencia del canvas:** Al recargar la página, el canvas se resetea. Post-MVP: guardar `nodes` + `edges` en `localStorage` o DB.
2. **Sin multi-agente real:** Ejecución secuencial individual. Post-MVP: `dynamic_crew_flow` con dependencias.
3. **Export pierde tasks:** Bundle v2 no modela tareas. Post-MVP: extender bundle schema v3 con `tasks` + `edges`.
4. **Sin undo/redo:** Post-MVP: implementar history stack.

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap crew visualize`

- **Qué automatiza:** Crear crews visualmente desde CLI generando un snapshot JSON del canvas que se puede compartir, versionar, y re-cargar. Evita que el usuario tenga que re-ensamblar el crew cada vez que recarga la página.
- **Tipo:** CLI command
- **Cómo se usa:**
```bash
# Exportar crew a JSON (desde el canvas, vía botón "Copy as JSON")
fap crew visualize --load crew-snapshot.json

# Guardar snapshot en DB
fap crew save --name "my-crew" --file crew-snapshot.json --org-id org_abc
```
- **Impacto para el usuario final:** El usuario no re-arma el crew desde cero cada sesión. Puede compartir snapshots con otros miembros de la org vía git.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

#### Herramienta Propuesta: `crew template` (frontend-only)

- **Qué automatiza:** Pre-cargar crews predefinidos en el canvas (ej: "Research → Review → Publish" o "Analyze → Report"). Similar a TemplatePicker pero para crews completos.
- **Tipo:** Template preset (array JSON de nodes + edges)
- **Cómo se usa:** Botón "Crew Templates" en CrewCanvas → dropdown con 3-4 presets → click → canvas poblado automáticamente.
- **Impacto para el usuario final:** No empieza desde canvas vacío. Templates de flujos comunes.
- **Prioridad:** Integrado en Tarea 2 (CrewCanvas).

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se requieren cambios de schema. Canvas state es local.
✅ [CODE] `AgentNode.tsx` renderiza role + tools badges con Handle Top/Bottom
✅ [CODE] `TaskNode.tsx` renderiza description + expectedOutput con Handle Left/Right
✅ [CODE] `CrewCanvas.tsx` tiene sidebar con agentes arrastrables + ReactFlow canvas + nodeTypes registrados
✅ [CODE] `generateCrewPy(nodes, edges)` produce código Python CrewAI válido
✅ [CODE] `canvasToExportPayload(nodes)` produce `ExportBundleRequest` válido
✅ [BACKEND] `POST /agents/{role}/run` usado para Run All (existente, sin cambios)
✅ [BACKEND] `POST /api/bundles/export` usado para Export (existente, sin cambios)
✅ [FULLSTACK] Drag & drop de agente desde sidebar → canvas crea AgentNode
✅ [FULLSTACK] Conexiones entre nodos (agent→task) visibles como edges
✅ [FULLSTACK] Botón "Export as Crew" descarga ZIP con agentes del canvas
✅ [FULLSTACK] Botón "Preview Code" muestra código Python generado en dialog
✅ [FULLSTACK] Botón "Run All" ejecuta cada agente secuencialmente con polling
✅ [FULLSTACK] Canvas tiene MiniMap + Controls (zoom) funcionales
✅ [FULLSTACK] Sidebar agentes cargados desde `agent_catalog` vía API real
✅ [DX] `fap crew visualize` CLI exporta/importa snapshots de crew
✅ [DX] Crew templates predefinidos cargan canvas con 1 click
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ReactFlow SSR crash | Alta | ReactFlow usa `window`/`document` nativos. SSR sin `dynamic import` rompe el build. | `dynamic(() => import('...'), { ssr: false })` ya usado en `BuilderCanvas.tsx:6-29`. Mantener patrón. |
| DnD HTML5 inconsistente entre browsers | Media | Firefox vs Chrome manejan `dataTransfer` diferente. Tipos MIME pueden no coincidir. | Usar `dataTransfer.setData('text/plain', type)` + fallback. Probar en Chrome + Firefox + Edge. |
| Ejecución secuencial lenta | Media | Run All ejecuta agentes uno por uno. Con 5 agentes y 30s cada uno = 150s total. | Mostrar progreso por agente (progress bar). Ejecución paralela vía `Promise.all` si no hay dependencias. |
| Memoria canvas con muchos nodos | Baja | 20+ nodos ReactFlow puede degradar rendimiento. | ReactFlow maneja 500+ nodos virtualizados. No preocupante para MVP (< 20 nodos). |
| Export sin tasks frustrante | Media | Usuario espera que el crew completo (agentes + tareas) se exporte. Solo agentes van al ZIP. | Tooltip "Tasks and connections not exported" visible en dialog export. Botón "Copy as JSON" incluye tasks + edges. Post-MVP: bundle v3. |
| Sin persistencia → pérdida de trabajo | Alta | Recargar página = canvas vacío. Usuario pierde crew ensamblado. | Implementar Tarea 0 (`fap crew save`) + botón "Save Crew" que guarda en localStorage. Autosave cada 30s. |
| Collisión de roles al exportar | Media | Si el canvas tiene 2 agentes con mismo role, `ExportBundleRequest` los duplica. El bundle resultante tiene agentes duplicados. | Validar roles únicos en canvas. Si hay duplicados, mostrar warning. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: `fap crew` CLI** | `src/cli/commands/crew.py` | `crew_app = typer.Typer()` con subcomandos: `crew visualize --load FILE`, `crew save --name NAME --file FILE --org-id ID` | `src/cli/commands/templates_seed.py` — Typer sub-app + Rich output | DX | Media | 1.5h | Ninguna | → verificar: `fap crew --help` ejecuta sin errores |
| 0b | **DX: `scripts/crew_snapshot.py` helper** | `scripts/crew_snapshot.py` | `def dump_snapshot(org_id, crew_name, nodes, edges) -> str` | `scripts/bundle_validator.py` — script standalone | DX | Baja | 0.5h | Tarea 0 | → verificar: `python scripts/crew_snapshot.py --help` ejecuta |
| 1 | **Crear `AgentNode.tsx`** | `dashboard/components/builder/nodes/AgentNode.tsx` | `export function AgentNode({ data }: NodeProps<{ role: string; goal: string; tools: string[]; model?: string }>)` → renderiza Card + Handle (Top target, Bottom source) + tools badges | ReactFlow docs: custom node pattern. [`reactflow.dev/examples/nodes/custom-node`] | CODE | Baja | 1h | Ninguna | → verificar: `npm run lint` sin errores. Importable desde `App.tsx` test. |
| 2 | **Crear `TaskNode.tsx`** | `dashboard/components/builder/nodes/TaskNode.tsx` | `export function TaskNode({ data }: NodeProps<{ description: string; expectedOutput: string; assignedAgent?: string }>)` → renderiza Card + Handle (Left target, Right source) + assignedAgent badge | Mismo patrón que AgentNode | CODE | Baja | 0.75h | Ninguna | → verificar: `npm run lint` sin errores. |
| 3 | **Crear `CrewCanvas.tsx`** | `dashboard/components/builder/CrewCanvas.tsx` | `export function CrewCanvas()` → sidebar izquierda (ScrollArea con agentes draggables) + ReactFlow canvas central (nodeTypes: {agentNode, taskNode}) + toolbar (Export, Run All, Preview Code, Save, Templates). State: `useNodesState([])`, `useEdgesState([])`. DnD: `onDragOver`, `onDrop` con `screenToFlowPosition()`. `onConnect` con `addEdge`. | ReactFlow DnD example: [`reactflow.dev/examples/interaction/drag-and-drop`] + `BuilderCanvas.tsx` dynamic import pattern | CODE | Alta | 4h | Tareas 1, 2 | → verificar: Ruta `/builder` renderiza canvas con sidebar + toolbar. `npm run lint` sin errores. |
| 4 | **Crear `crewCodeGen.ts`** | `dashboard/lib/crewCodeGen.ts` | `export function generateCrewPy(nodes: Node[], edges: Edge[]): string` → genera string Python con `Agent(...)`, `Task(...)`, `Crew(...)`, `crew.kickoff()` | Función pura, sin deps externas. Pattern: `TemplatePicker.tsx` — string generation puro. | CODE | Media | 1.5h | Tareas 1, 2 | → verificar: `console.log(generateCrewPy([], []))` produce código Python sintácticamente válido (paste en Python REPL). |
| 5 | **Crear `canvasUtils.ts`** | `dashboard/lib/canvasUtils.ts` | `export function canvasToExportPayload(nodes: Node[]): { agents: AgentExportItem[] }` — convierte agentNode data ↔ `AgentExportItem`. `export function nodesToSnapshot(nodes, edges): string` — JSON.stringify para persistencia. | Sin patrón referencia directo. Funciones puras. | CODE | Baja | 1h | Tareas 1, 2 | → verificar: `canvasToExportPayload([agentNode])` produce objeto con estructura `{ agents: [{ role, soul_json, ... }] }`. |
| 6 | **Crear `CrewTemplates.ts`** | `dashboard/lib/crewTemplates.ts` | `export const CREW_TEMPLATES: { name, description, nodes, edges, category }[]` — 4 presets: "Research Pipeline", "Code Review Crew", "Content Creation", "Data Analysis" | `dashboard/lib/constants.ts` — constantes exportadas. Patrón `TEMPLATE_CATEGORIES`. | CODE | Baja | 0.75h | Tareas 1, 2 | → verificar: `CREW_TEMPLATES.length >= 4`. Cada template tiene nodes válidos con posiciones únicas. |
| 7 | **Reemplazar `BuilderCanvas.tsx`** | `dashboard/components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas()` → wrapper dynamic import de `CrewCanvas` con `ssr: false` + loading skeleton. | Mismo archivo, reemplazar contenido. Mantener `dynamic(() => import('...'), { ssr: false, loading: () => <Skeleton /> })`. | CODE | Baja | 0.25h | Tarea 3 | → verificar: Build Next.js no rompe en SSR. `npm run build` sin errores. |
| 8 | **Actualizar `BuilderLayout.tsx`** | `dashboard/components/builder/BuilderLayout.tsx` | Agregar tabs "Agent Form" y "Crew Canvas" con `@radix-ui/react-tabs`. Tab "Crew Canvas" → `<CrewCanvas />`. Tab "Agent Form" → `<AgentForm />` existente. | `dashboard/components/ui/tabs.tsx` — Tabs + TabsContent + TabsTrigger. Patrón: `AnalyticalAssistantChat.tsx` si usa tabs. | FULLSTACK | Media | 1h | Tarea 7 | → verificar: Builder page tiene 2 tabs funcionales. Cambiar entre tabs preserva estado. |
| 9 | **Actualizar `types.ts`** | `dashboard/lib/types.ts` | Agregar `CanvasAgentNode`, `CanvasTaskNode`, `CanvasNodeType` interfaces. | Mismo archivo, seguir estilo existente. | CODE | Baja | 0.25h | Tareas 1, 2 | → verificar: TypeScript compila. `npm run lint` sin errores de tipo. |
| 10 | **Validar flujo end-to-end** | — | Flujo completo: Open `/builder` → Crew Canvas tab → Drag agent from sidebar → Add task node → Connect → Export → Download ZIP → Preview Code → Run All → Verify results. | — | FULLSTACK | Baja | 1h | Tareas 1-9 | → verificar: Todos los criterios §5 pasan. No errores en consola del browser. |

**Tiempo total estimado:** 13 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Bundle schema v3:** Agregar `tasks` y `edges` al `manifest.json` para exportar crews completos (no solo agentes).
- **`dynamic_crew_flow`:** Flow multi-agente que toma `{ agents, tasks, process }` y ejecuta `Crew(agents=[...], tasks=[...], process=...)` con dependencias reales.
- **Persistencia canvas en DB:** Guardar `nodes` + `edges` en tabla `crew_canvases(org_id, name, snapshot JSONB)` para sesiones multi-día.
- **Canvas collaboration:** Multi-usuario vía Supabase Realtime editando el mismo canvas.
- **ToolNode:** Nodo de tool como ciudadano de primera clase (cuando tools sean ejecutables independientes).
- **Undo/Redo:** History stack con Ctrl+Z / Ctrl+Y.
- **Validation engine visual:** Resaltar nodos con errores (agente sin task, task sin agente, ciclo). Reglas configurables.
