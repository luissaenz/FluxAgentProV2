# 🏛️ Análisis UNIFICADO — Paso 07: Canvas visual — ensamblaje de crews

> **Fase:** guiAgentGenerator | **Paso:** 07 | **Fecha:** 2026-05-15
> **Agentes evaluados:** step, glm5.1, dsp, ring, qwen3.6, hy3, mm2.5, lgn

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **step** | ✅ 27/30 | 7 (D-01 a D-07) | ✅ `fap crew` CLI (save/load/export) | ✅ | **4.9** |
| **glm5.1** | ✅ 25/25 | 5 (D1-D5) | ✅ `fap crew export` + `fap crew validate` | ✅ | **4.8** |
| **dsp** | ✅ 30/30 | 7 (D1-D7) | ✅ `fap crew visualize` + crew templates | ✅ | **4.7** |
| **ring** | ✅ 19/19 | 9 (D1-D9) | ✅ `fap canvas export` + `fap canvas scaffold` | ✅ | **4.5** |
| **qwen3.6** | ✅ 18/18 | 4 (D1-D4) | ✅ `fap crew validate` + `fap crew export` | ✅ | **4.3** |
| **hy3** | ✅ 16/16 | 3 | ✅ `create-flow-node` script | ❌ DX débil (generador boilerplate) | **2.5** |
| **mm2.5** | ✅ 14/14 | **0** ❌ (falso negativo) | ❌ Debug Panel inline (componente React, no CLI) | ❌ Pasó por alto discrepancias críticas | **2.5** |
| **lgn** | ✅ 12/12 | 3 | ❌ `crew-validator` standalone (sin framework) | ❌ Sin esquemas DB, sin tipos, sin endpoints | **2.0** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectada por | Verificada contra código | Resolución |
|---|---|---|---|---|
| D-01 | **Sin librería drag-and-drop.** El plan asume sidebar con items arrastrables pero `@dnd-kit/core`, `react-dnd` no están en `package.json`. | dsp, step, hy3, qwen3.6 | ✅ `dashboard/package.json` — sin deps DnD | Usar **HTML5 DnD nativo**: `draggable="true"`, `dataTransfer.setData('application/reactflow', type)`, `onDragOver`/`onDrop` en CrewCanvas. ReactFlow v11 lo soporta. **0 deps nuevas.** |
| D-02 | **Sin flow "crew" en FlowRegistry.** Plan dice "Run Crew vía `POST /flows/{flow_type}/run`" pero solo existen `generic_flow`, `success_test_flow`, `fail_test_flow`. No hay flow multi-agente. | dsp, step, hy3, ring, qwen3.6, glm5.1 | ✅ `src/flows/registry.py:370` — 3 flows registrados | **MVP:** "Run All" ejecuta cada agente secuencialmente vía `POST /agents/{role}/run` individual. Sin dependencias entre agentes. **Post-MVP:** `crew_runner_flow` con `@register_flow`. |
| D-03 | **`ExportBundleRequest` no incluye `tasks` ni `edges`.** Solo `agents: List[AgentExportItem]` + `skills: Optional[List[SkillExportItem]]`. Bundle schema v2 no modela relaciones agent↔task. | dsp, step, glm5.1, ring, mm2.5 | ✅ `src/services/bundle_schemas.py:111-116` — sin campos tasks/edges | Exportar solo agentes del canvas como `AgentExportItem[]`. Warning en dialog: "Tasks and connections not exported (bundle-schema-v2.md limitation). Use Copy as JSON for complete graph." |
| D-04 | **No existe `GET /agents` endpoint.** Solo existen `GET /agents/by-role/{role}` y `POST /agents`. El sidebar necesita listar todos los agentes de la org por tipo. | qwen3.6, glm5.1, mm2.5, step | ✅ `src/api/routes/agents.py` — sin handler GET lista | Crear endpoint `GET /agents` con `Depends(require_org_id)`, `TenantClient`, retorna `ListAgentsResponse` con `agents: List[AgentListItem]`. Query `?active_only=true`. **Bloqueante para sidebar.** |
| D-05 | **No existe endpoint para persistir `workflow_template` desde canvas.** El canvas necesita guardar la definición del crew en DB para persistencia y ejecución. | glm5.1, ring | ✅ `src/api/routes/workflows.py` — archivo ya existe pero sin endpoint POST | Crear endpoint `POST /api/workflows` en `workflows.py`. Input: `{name, flow_type, definition, status}`. `TenantClient` + `require_org_id`. Retorna `201 Created` con `{id, flow_type, status}`. |
| D-06 | **No existe generador de código Python.** Plan pide "Vista previa de código Python generado" pero `crewCodeGen.ts` no existe. | dsp, step, glm5.1, ring, hy3 | ✅ `dashboard/lib/` — sin `crewCodeGen.ts` | Crear `dashboard/lib/crewCodeGen.ts` — función pura `generateCrewPy(nodes: Node[], edges: Edge[]): string`. Genera `Agent()`, `Task()`, `Crew()`, `Process.sequential`, `crew.kickoff()`. 0 deps externas. |
| D-07 | **Custom nodes ReactFlow no existen.** Directorio `nodes/` vacío. `AgentNode.tsx`, `TaskNode.tsx` no creados. | dsp, step, ring, hy3, lgn, mm2.5, qwen3.6 | ✅ `dashboard/components/builder/nodes/` — no existe | Crear `AgentNode.tsx` (Handle Top/Bottom, Card con role + goal + tools badges) y `TaskNode.tsx` (Handle Left/Right, Card con description + expectedOutput). Patrón `reactflow.dev/examples/nodes/custom-node`. |
| D-08 | **`BuilderCanvas.tsx` es placeholder vacío.** `nodes=[]`, `edges=[]`, mensaje "Placeholder for Step 07". Sin sidebar, sin DnD, sin conexiones. | ring, step, qwen3.6, dsp, glm5.1 | ✅ `dashboard/components/builder/BuilderCanvas.tsx:34-45` | Reemplazar wrapper con `dynamic import` de `CrewCanvas`. `CrewCanvas` es el canvas completo con ReactFlow + sidebar arrastrable + toolbar + controles. |
| D-09 | **Sin persistencia del canvas.** Recargar página = canvas vacío. Usuario pierde crew ensamblado. | dsp, step, ring, qwen3.6 | ✅ N/A — funcionalidad faltante | **MVP:** botón "Save Crew" → `localStorage.setItem(canvasState)`. Autosave cada 30s. `fap crew snapshot save` guarda como JSON en disco. **Post-MVP:** tabla `crew_canvases`. |
| D-10 | **ToolNode como nodo separado es redundante.** Plan pide ToolNode pero tools son atributo del agente (campo `allowed_tools`), no entidad independiente. | dsp | ✅ `agent_catalog.allowed_tools TEXT[]` — tools asignadas al agente | **No crear ToolNode separado.** Mostrar tools como badges/chips dentro de `AgentNode`. Redundante tener nodo independiente para atributos de agente. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Implementar canvas ReactFlow con nodos drag-and-drop para ensamblar crews visualmente. El usuario arrastra agentes y tareas, los conecta via edges, y puede exportar el crew como bundle ZIP o ejecutar agentes individualmente para probar.

**Correcciones críticas al plan original:**
- El plan asume drag-and-drop con librería externa → se usa HTML5 DnD nativo (sin deps nuevas).
- El plan asume que existe un flow "crew" registrado → MVP ejecuta agentes secuencialmente vía `POST /agents/{role}/run`. No hay flow multi-agente en esta fase.
- El plan pide "Export as Crew → JSON compatible con bundle-schema-v2" → bundle v2 solo exporta agentes, no tasks/edges. Se exporta solo agentes con warning.
- El plan pide "ToolNode" separado → suprimido. Tools son badges dentro de AgentNode.
- El plan pide "Run Crew vía `POST /flows/{flow_type}/run`" → sin flow crew, se ejecuta agente por agente.

**Herramienta DX seleccionada:** `fap crew` — CLI unificada con subcomandos `save`, `load`, `export`, `validate`. Fusión de propuestas de step, glm5.1, qwen3.6, dsp. Es **Tarea 0** y el implementador DEBE usarla para el resto del paso.

**Tiempo total estimado:** ~13 horas.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path
1. Usuario abre `/builder` → BuilderLayout con tabs "Agent Form" / "Crew Canvas"
2. Usuario selecciona tab "Crew Canvas" → CrewCanvas con sidebar izquierda (agentes arrastrables) + canvas central ReactFlow
3. Sidebar carga agentes desde `GET /agents` (mostrando role, goal truncado, tools count)
4. Usuario arrastra agente desde sidebar al canvas → se crea `AgentNode` con Card (role + tools badges)
5. Usuario crea tarea inline (botón "Add Task" en toolbar) → se crea `TaskNode` con description + expected output
6. Usuario conecta agente → tarea arrastrando del Handle bottom de AgentNode al Handle left de TaskNode → edge animado visible
7. Usuario hace clic "Run All" → cada agente ejecuta secuencialmente vía `POST /agents/{role}/run` + polling
8. Resultados visibles en panel de resultados (tab por agente: status, tokens, response)
9. Usuario hace clic "Export as Crew" → serializa agentes del canvas → `POST /api/bundles/export` → ZIP descargable
10. Usuario hace clic "Save Crew" → persiste canvas como snapshot en localStorage + opción download JSON

### Edge Cases MVP
- **0 agentes en sidebar:** Mostrar EmptyState "No agents yet. Create one in Agent Form first." con link a tab "Agent Form".
- **0 agentes en canvas al exportar:** Botón Export deshabilitado. Tooltip "Add at least one agent to export."
- **Agente duplicado (mismo role) en canvas:** Warning badge + botón Export deshabilitado. Toast "Duplicate roles detected. Each agent must have a unique role."
- **Agente sin tareas conectadas:** Borde amarillo (`border-yellow-500`) + badge "Unassigned" en AgentNode.
- **Tarea sin agente asignado:** Campo `assignedAgent` vacío mostrado como "—" en TaskNode.
- **Conexión inválida (task→agent, tool→anything):** `onConnect` rechaza con `return false`. No se crea edge.
- **Ejecución falla (agente no encontrado, timeout):** Polling detecta `status: failed` → badge rojo + mensaje de error en panel resultados.
- **Timeout 120s en ejecución:** Stop polling. Toast "Agent execution timed out." Resultados parciales visibles.
- **Export sin goal/backstory en algún agente:** Validación Pydantic en backend retorna 422. Frontend muestra campos faltantes con borde rojo antes de exportar.
- **Canvas vacío al refrescar:** `localStorage` check en mount. Si existe snapshot → cargar. Si no → canvas vacío.

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### A. `dashboard/components/builder/nodes/AgentNode.tsx` (CREACIÓN)
- **Ruta:** `dashboard/components/builder/nodes/AgentNode.tsx`
- **Tipo:** Creación
- **Firma:** `export function AgentNode({ data }: NodeProps<{ role: string; goal: string; tools: string[]; model?: string }>)`
- **Descripción:** Nodo ReactFlow custom para agente. Renderiza Card con role (CardTitle), goal truncado (line-clamp-2), tools badges (max 3 visibles + "+N" remainder). Handle Top (`type="target" position={Position.Top}`), Handle Bottom (`type="source" position={Position.Bottom}`). Tooltip con role+goal+tools completos.
- **Imports:** `reactflow` (Handle, Position, NodeProps), `shadcn/ui` (Card, Badge, Tooltip), `lucide-react` (Bot)
- **Patrón:** `reactflow.dev/examples/nodes/custom-node`

```tsx
// FIRMA CONSOLIDADA
export function AgentNode({
  data,
}: NodeProps<{
  role: string
  goal: string
  tools: string[]
  model?: string
}>)
```

#### B. `dashboard/components/builder/nodes/TaskNode.tsx` (CREACIÓN)
- **Ruta:** `dashboard/components/builder/nodes/TaskNode.tsx`
- **Tipo:** Creación
- **Firma:** `export function TaskNode({ data }: NodeProps<{ description: string; expectedOutput: string; assignedAgent?: string }>)`
- **Descripción:** Nodo ReactFlow custom para tarea. Renderiza Card con description (título), expectedOutput (truncado line-clamp-1), badge del agente asignado. Handle Left (`type="target" position={Position.Left}`), Handle Right (`type="source" position={Position.Right}`).
- **Imports:** `reactflow` (Handle, Position, NodeProps), `shadcn/ui` (Card, CardContent, CardHeader, CardTitle, Badge), `lucide-react` (ClipboardList)
- **Patrón:** Mismo que AgentNode

```tsx
export function TaskNode({
  data,
}: NodeProps<{
  description: string
  expectedOutput: string
  assignedAgent?: string
}>)
```

#### C. `dashboard/components/builder/CrewCanvas.tsx` (CREACIÓN)
- **Ruta:** `dashboard/components/builder/CrewCanvas.tsx`
- **Tipo:** Creación
- **Firma:** `export function CrewCanvas()`
- **State:** `useNodesState([])`, `useEdgesState([])`, `useState` para `sidebarAgents`, `running`, `runResults`
- **Descripción:** Canvas ReactFlow completo. Sidebar izquierda con ScrollArea de agentes arrastrables (HTML5 DnD nativo). Canvas central con ReactFlow + Background + Controls + MiniMap. Toolbar con botones: "Add Task", "Export as Crew", "Run All", "Preview Code", "Save Crew", "Crew Templates" (presets). DnD: `onDragOver` (`e.preventDefault()`), `onDrop` (`screenToFlowPosition()` + `addNodes`). Edges: `onConnect` con `addEdge` + validación (agent→task ✅, task→task ✅, resto ❌). Validación visual: agentes sin edges de salida → borde amarillo. `nodeTypes = { agentNode: AgentNode, taskNode: TaskNode }` definido como constante fuera del componente.
- **Imports:** `reactflow` (ReactFlow, Background, Controls, MiniMap, addEdge, useNodesState, useEdgesState, ReactFlowProvider, etc.), `@tanstack/react-query` (useQuery), `@/lib/api`, `@/lib/crewCodeGen`, `@/lib/canvasUtils`, `@/lib/crewTemplates`, `sonner` (toast), `shadcn/ui` (Button, Separator, ScrollArea, Dialog), `lucide-react` (Download, Play, Code, Share2)
- **Patrón:** `reactflow.dev/examples/interaction/drag-and-drop` + `BuilderCanvas.tsx` dynamic import pattern

```tsx
export function CrewCanvas()
// Internal state:
//   nodes, setNodes, onNodesChange = useNodesState([])
//   edges, setEdges, onEdgesChange = useEdgesState([])
//   sidebarAgents: AgentListItem[]
//   running: boolean
//   runResults: Record<string, { status, result, error, tokens_used }>
// Internal functions:
//   fetchAgents() → useQuery GET /agents
//   onConnect(params: Connection) → addEdge({ ...params, animated: true })
//   onDragOver(e: DragEvent) → e.preventDefault()
//   onDrop(e: DragEvent) → screenToFlowPosition → addNodes
//   serializeGraph() → CrewGraph
//   validateGraph() → { valid: boolean, warnings: string[] }
//   handleExport() → canvasToExportPayload → POST /api/bundles/export → download ZIP
//   handleRunAll() → for each agentNode → POST /agents/{role}/run → polling
//   handlePreviewCode() → generateCrewPy() → Dialog
//   handleSaveCrew() → nodesToSnapshot() → localStorage + download JSON
//   handleLoadTemplate(template) → setNodes + setEdges from CREW_TEMPLATES
```

#### D. `dashboard/lib/crewCodeGen.ts` (CREACIÓN)
- **Ruta:** `dashboard/lib/crewCodeGen.ts`
- **Tipo:** Creación
- **Firma:** `export function generateCrewPy(nodes: Node[], edges: Edge[]): string`
- **Descripción:** Función pura. Itera nodes tipo `agentNode` → genera `Agent(role=, goal=, backstory=, allow_code_execution=False)`. Itera nodes tipo `taskNode` → genera `Task(description=, expected_output=, agent=agent_X)`. Mapea edges agent→task para asignar `agent=` en cada Task. Genera `Crew(agents=[...], tasks=[...], process=Process.sequential)` + `crew.kickoff()`. 0 deps externas. Determinista.
- **Patrón:** `scripts/seed_system_bundles.py` — generación de código Python como string

#### E. `dashboard/lib/canvasUtils.ts` (CREACIÓN)
- **Ruta:** `dashboard/lib/canvasUtils.ts`
- **Tipo:** Creación
- **Firmas:**
  - `export function canvasToExportPayload(nodes: Node[]): { agents: AgentExportItem[] }`
  - `export function nodesToSnapshot(nodes: Node[], edges: Edge[]): string`
  - `export function snapshotToNodes(snapshot: string): { nodes: Node[]; edges: Edge[] }`
- **Descripción:** Funciones puras de serialización. `canvasToExportPayload` mapea AgentNode data → `AgentExportItem` (role, soul_json={goal,backstory,...}, allowed_tools, max_iter). `nodesToSnapshot` → `JSON.stringify({nodes, edges})`. `snapshotToNodes` → `JSON.parse()` + validación básica de campos requeridos. Testeable sin React.
- **Patrón:** `src/services/bundle_schemas.py` — mapeo de entidades a payloads HTTP

#### F. `dashboard/lib/crewTemplates.ts` (CREACIÓN)
- **Ruta:** `dashboard/lib/crewTemplates.ts`
- **Tipo:** Creación
- **Firma:** `export const CREW_TEMPLATES: CrewTemplate[]`
- **Descripción:** Array con 4 presets de crews predefinidos: `research-pipeline` (Researcher→Search→Writer), `code-review-crew` (Reviewer→Analyze→Report), `content-creation` (Writer→SEO→Editor), `data-analysis` (Analyst→Parse→Visualize). Cada preset: `id`, `name`, `description`, `category`, `nodes: Node[]`, `edges: Edge[]`.
- **Patrón:** `dashboard/lib/constants.ts` — constantes exportadas (TEMPLATE_CATEGORIES)

#### G. `src/api/routes/agents.py` (MODIFICACIÓN)
- **Ruta:** `src/api/routes/agents.py`
- **Tipo:** Modificación (añadir handler)
- **Firma:** `async def list_agents(org_id: str = Depends(require_org_id), active_only: bool = Query(True)) -> ListAgentsResponse`
- **Descripción:** Nuevo endpoint `GET /agents`. Query con `TenantClient` a `.table('agent_catalog').select('*').eq('org_id', org_id)`. Filtro opcional `?active_only=true` → `.eq('is_active', True)`. Retorna `ListAgentsResponse(agents: List[AgentListItem])` donde `AgentListItem` tiene `id: str, role: str, goal: str, backstory: str, allowed_tools: list[str], max_iter: int`.
- **Patrón:** `flows.py:76-110` (`list_available_flows`) + `agents.py:51-92` (`create_agent` con TenantClient)
- **Registro router:** Confirmar que `agents.router` está en `src/api/main.py`. El router ya está registrado (línea 27 import + línea 115 include_router según phase-state.md).

#### H. `src/api/routes/workflows.py` (MODIFICACIÓN)
- **Ruta:** `src/api/routes/workflows.py`
- **Tipo:** Modificación (añadir handler)
- **Firma:** `async def create_workflow(payload: WorkflowCreate, org_id: str = Depends(require_org_id)) -> WorkflowResponse`
- **Descripción:** Nuevo endpoint `POST /api/workflows`. Input: `WorkflowCreate = { name: str, flow_type: str, definition: Dict[str, Any], status: str = "draft" }`. Persiste en tabla `workflow_templates` existente vía `TenantClient`. Retorna `201 Created` con `{ id: UUID, flow_type: str, status: str }`. Validar UNIQUE constraint en `(org_id, flow_type)` → 409 Conflict si duplicado.
- **Patrón:** `agents.py:51-92` (`create_agent` con TenantClient + upser/c check)
- **Registro router:** Asegurar que `workflows.router` está registrado en `src/api/main.py`.

#### I. `dashboard/components/builder/BuilderCanvas.tsx` (MODIFICACIÓN)
- **Ruta:** `dashboard/components/builder/BuilderCanvas.tsx`
- **Tipo:** Modificación (reemplazar placeholder)
- **Descripción:** Reemplazar placeholder actual (`nodes=[]`, `edges=[]`, mensaje "Placeholder for Step 07") con wrapper dynamic import de `CrewCanvas`:
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
- **Patrón:** Mismo archivo, mantener patrón `dynamic(() => import(...), { ssr: false })`

#### J. `dashboard/components/builder/BuilderLayout.tsx` (MODIFICACIÓN)
- **Ruta:** `dashboard/components/builder/BuilderLayout.tsx`
- **Tipo:** Modificación (añadir tabs)
- **Descripción:** Agregar `Tabs` (`@radix-ui/react-tabs` ya instalado v1.1.2) con 2 tabs: "Agent Form" (existente, `<AgentForm />`) y "Crew Canvas" (`<BuilderCanvas />` que ahora importa `CrewCanvas`). Layout: `TabsList` con `TabsTrigger`, `TabsContent` con `flex-1` para cada panel.
- **Patrón:** `dashboard/app/(app)/agents/[id]/page.tsx:130-136` — Tabs + TabsContent pattern

#### K. `dashboard/lib/types.ts` (MODIFICACIÓN)
- **Ruta:** `dashboard/lib/types.ts`
- **Tipo:** Modificación (añadir interfaces)
- **Descripción:** Agregar al final del archivo:
```typescript
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

export interface CrewGraphNode {
  id: string
  type: CanvasNodeType
  data: Record<string, unknown>
  position: { x: number; y: number }
}

export interface CrewGraphEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

export interface CrewGraph {
  nodes: CrewGraphNode[]
  edges: CrewGraphEdge[]
  metadata: { name: string; createdAt: string }
}
```

### Conexiones válidas en el canvas

| Source | Target | Válida | Razón |
|:---|:---|:---|:---|
| AgentNode (Bottom) | TaskNode (Left) | ✅ | Asignación de tarea a agente |
| TaskNode (Right) | TaskNode (Left) | ✅ | Secuencia de tareas |
| TaskNode (Left) | AgentNode (Top) | ❌ | No soportado (agente no recibe de tarea) |
| Tool → Anything | — | ❌ | ToolNode no existe en MVP (tools son badges en AgentNode) |
| AgentNode → AgentNode | — | ❌ | Sin conexión directa entre agentes |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap crew
- **Qué automatiza:** Gestión completa de crews desde terminal: guardar snapshots del canvas como JSON versionable, cargar crews previamente guardados, exportar agentes como bundle ZIP, y validar estructura de grafo crew. Elimina trabajo manual de re-ensamblar crews desde canvas cada sesión.
- **Tipo:** CLI (Typer sub-app)
- **Ubicación:** src/cli/commands/crew.py + registro en src/cli/main.py
- **Cómo se usa:**
  # Guardar snapshot del canvas
  fap crew save --name "research-crew" --org-id <uuid> --output crew.json

  # Cargar snapshot (para reabrir crew en canvas)
  fap crew load --file crew.json --org-id <uuid>

  # Exportar crew como bundle ZIP (sin abrir dashboard)
  fap crew export --name "my-crew" --roles "researcher,writer" --org-id <uuid> --output crew.zip

  # Validar JSON de crew (agentes sin tareas, roles duplicados, ciclos)
  fap crew validate --file crew.json

  # Crear desde template
  fap crew scaffold --preset research-pipeline --org-id <uuid> --output crew.json
- **Impacto para el usuario final:** No rearma el canvas manualmente cada día. Versiona crews en git. Valida crews antes de deploy. Brinda workflows CI/CD-ready sin UI.
- **El implementador DEBE usarla** para validar export y snapshots durante el resto del paso.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **ReactFlow v11 con HTML5 DnD nativo.** No instalar `@dnd-kit/core` ni `react-dnd`. ReactFlow v11 ya soporta DnD nativo con `draggable`, `dataTransfer`, `onDragOver`/`onDrop`. `reactflow` v11.11.4 ya está en `dashboard/package.json:41`. Justificación: 0 deps nuevas. Patrón documentado en `reactflow.dev/examples/interaction/drag-and-drop`.

2. **Sin Zustand ni Redux para estado del canvas.** Usar hooks nativos de ReactFlow (`useNodesState`, `useEdgesState`) + `useState` local. Zustand NO está instalado en el proyecto y no es necesario para MVP con <20 nodos. Justificación: el proyecto no tiene global state manager. Mantener simplicidad. Post-MVP: migrar a Zustand si el canvas escala >50 nodos.

3. **Corrección al plan: ToolNode suprimido.** El plan pide `ToolNode.tsx` como nodo separado pero tools son atributo del agente (campo `agent_catalog.allowed_tools`). Crear nodo tool independiente duplica información creando una jerarquía artificial. Las tools se muestran como badges dentro de `AgentNode`. Justificación: el dato canónico es `allowed_tools` en `agent_catalog`. ToolNode añadiría complejidad sin valor funcional en MVP.

4. **Corrección al plan: Ejecución secuencial individual, no flow crew.** El plan dice "Run Crew → `POST /flows/{flow_type}/run`" pero no existe flow multi-agente. MVP: "Run All" ejecuta cada agente individualmente vía `POST /agents/{role}/run` con polling. Justificación: `POST /agents/{role}/run` ya existe y `BaseCrew` carga agente desde DB. Ejecución secuencial = experiencia funcional equivalente. Post-MVP: `crew_runner_flow`.

5. **Corrección al plan: Export solo agentes, no tasks/edges.** El plan dice "Export as Crew → JSON compatible con bundle-schema-v2.md" pero bundle-schema-v2 no modela tasks ni edges. Se exportan solo agentes del canvas como `AgentExportItem[]`. Las tasks/edges se preservan vía "Copy as JSON" (incluye grafo completo). Botón "Export as Crew" muestra warning dialog. Justificación: `ExportBundleRequest` en `bundle_schemas.py:111-116` solo tiene `agents` + `skills`. Post-MVP: bundle v3 con `tasks` + `edges`.

6. **Corrección al plan: `GET /agents` endpoint necesario.** El plan asume que los agentes se pueden listar para el sidebar pero solo existe `GET /agents/by-role/{role}`. Se crea `GET /agents` con `require_org_id` + `TenantClient`. Justificación: RLS requiere `app.org_id` seteado por middleware backend (corrección D4 de Paso 04 en `phase-state.md`). NO se puede hacer query directa desde frontend browser client.

7. **Corrección al plan: `POST /api/workflows` endpoint necesario.** El plan no menciona persistencia del workflow generado en canvas. Para que "Run Crew" funcione y el canvas tenga persistencia, se necesita guardar `workflow_templates.definition`. Se crea endpoint que persiste en tabla `workflow_templates` existente. Justificación: `DynamicWorkflow` en `src/flows/dynamic_flow.py` ya carga definiciones desde DB. Post-MVP: `crew_runner_flow` usará `POST /api/workflows` para registrar crews visuales.

8. **Persistencia del canvas en localStorage para MVP.** Sin tabla `crew_canvases` nueva. `nodesToSnapshot()` + `snapshotToNodes()` serializan/deserializan el estado. Botón "Save Crew" persiste + autosave cada 30s. Justificación: evitar migración de DB nueva en este paso. `workflow_templates.definition` ya cubre la forma canónica. localStorage = conveniencia de sesión.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Tabla agent_catalog existe con columnas role, soul_json, allowed_tools, max_iter (mig 004)
✅ [DATA] Tabla workflow_templates existe con flow_type, definition JSONB (mig 006)
✅ [DATA] Tabla tasks existe para polling de ejecución (mig 001)
✅ [DATA] Sin cambios de schema requeridos. Canvas state es local + persistencia en workflow_templates
✅ [CODE] AgentNode.tsx renderiza con role (title) + goal (truncado) + tools badges (max 3) + Handle Top/Bottom
✅ [CODE] TaskNode.tsx renderiza con description + expectedOutput + assignedAgent badge + Handle Left/Right
✅ [CODE] CrewCanvas.tsx tiene sidebar izquierda con agentes arrastrables + ReactFlow canvas central
✅ [CODE] HTML5 Drag & Drop de agente desde sidebar → canvas crea AgentNode en posición drop
✅ [CODE] Conexiones (edges) entre nodos visibles con animación (connect agent→task, task→task)
✅ [CODE] Validación de conexiones: onConnect rechaza inválidas (task→agent, tool→anything)
✅ [CODE] generateCrewPy(nodes, edges) produce código Python CrewAI sintácticamente válido
✅ [CODE] canvasToExportPayload(nodes) produce { agents: AgentExportItem[] } compatible con ExportBundleRequest
✅ [CODE] nodesToSnapshot(nodes, edges) produce JSON.stringify guardable en localStorage
✅ [CODE] CREW_TEMPLATES con ≥4 presets (research, code-review, content, data-analysis)
✅ [CODE] npm run lint sin errores (frontend)
✅ [BACKEND] GET /agents endpoint retorna lista de agentes de la org (filtro ?active_only=true)
✅ [BACKEND] GET /agents usa require_org_id + TenantClient para RLS
✅ [BACKEND] POST /api/workflows endpoint crea workflow_template con TenentClient + 201 Created
✅ [BACKEND] POST /agents/{role}/run usado para Run All (existente, sin cambios)
✅ [BACKEND] POST /api/bundles/export usado para Export as Crew (existente, sin cambios)
✅ [BACKEND] GET /tasks/{task_id} usado para polling (existente, sin cambios)
✅ [BACKEND] uv run ruff check src/ sin errores
✅ [FULLSTACK] Ruta /builder carga sin errores SSR (ReactFlow dynamic import)
✅ [FULLSTACK] Tabs "Agent Form" / "Crew Canvas" en BuilderLayout funcionales
✅ [FULLSTACK] Drag & drop de agente desde sidebar → canvas crea AgentNode visible con datos correctos
✅ [FULLSTACK] Conexión visual entre nodos (edges) visibles al conectar Handle Bottom agent → Handle Left task
✅ [FULLSTACK] Botón "Preview Code" muestra código Python en Dialog (generateCrewPy output)
✅ [FULLSTACK] Botón "Run All" ejecuta cada agente secuencialmente con polling y muestra resultados (status, tokens)
✅ [FULLSTACK] Botón "Export as Crew" descarga ZIP con agentes del canvas (warning dialog: tasks/edges no exportados)
✅ [FULLSTACK] Botón "Save Crew" persiste snapshot en localStorage + descarga JSON opcional
✅ [FULLSTACK] Botón "Crew Templates" carga preset que pobla canvas con nodos+edges predefinidos
✅ [FULLSTACK] Canvas tiene MiniMap + Controls (zoom in/out/fit) funcionales
✅ [FULLSTACK] Agente sin tareas conectadas muestra warning visual (borde amarillo)
✅ [FULLSTACK] Roles duplicados en canvas → botón Export deshabilitado + toast error
✅ [DX] fap crew save/load ejecutan sin errores y persisten/cargan crew JSON
✅ [DX] fap crew export ejecuta sin errores y genera ZIP válido desde CLI
✅ [DX] fap crew validate detecta agentes sin tareas, roles duplicados, y ciclos en grafo
✅ [DX] fap crew scaffold --preset genera JSON válido con estructura CrewGraph

Funcionales:
- [ ] Drag & drop agentes desde sidebar al canvas
- [ ] Crear tareas inline y conectar a agentes
- [ ] Ejecutar agentes individualmente desde canvas
- [ ] Exportar crew como ZIP descargable
- [ ] Previsualizar código Python generado desde el grafo
- [ ] Guardar y cargar snapshots del canvas (localStorage + download JSON)
- [ ] Cargar presets de crews predefinidos

Técnicos:
- [ ] ReactFlow canvas con nodeTypes, onConnect, DnD HTML5
- [ ] Sidebar con agentes desde API real (GET /agents)
- [ ] Polling con TanStack Query para resultados de ejecución
- [ ] Validación visual en tiempo real (agentes sin tareas, roles duplicados)
- [ ] Serialización grafo ↔ payloads HTTP (ExportBundleRequest, CrewGraph)
- [ ] Generación de código Python CrewAI desde grafo
- [ ] Dynamic import ReactFlow con ssr: false (sin crash)
- [ ] Tabs Agent Form / Crew Canvas en BuilderLayout
```

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap crew` CLI — subcomandos `save`, `load`, `export`, `validate`, `scaffold`. Archivo: `src/cli/commands/crew.py` + registro en `src/cli/main.py` | Media | 1.5h | Ninguna | `uv run fap crew --help` ejecuta sin errores. `crew export --help`, `crew validate --help`, `crew save --help` funcionales |
| 1 | **Endpoint `GET /agents`:** Añadir `list_agents()` en `src/api/routes/agents.py`. Query `TenantClient` con `?active_only=true`. Retorna `ListAgentsResponse` con `AgentListItem[]` | Baja | 0.5h | Tarea 0 | `curl /agents` con `X-Org-ID` header retorna 200 + array |
| 2 | **Endpoint `POST /api/workflows`:** Añadir `create_workflow()` en `src/api/routes/workflows.py`. `WorkflowCreate` Pydantic model + `TenantClient` insert en `workflow_templates`. 201 si éxito, 409 si duplicado | Media | 1.5h | Tarea 0 | `curl -X POST /api/workflows` con payload válido retorna 201 + `{id, flow_type, status}` |
| 3 | **Crear `AgentNode.tsx`:** `dashboard/components/builder/nodes/AgentNode.tsx`. Card con role + goal trunc + tools badges + Handles Top/Bottom. Import de `reactflow` Handle, Position, NodeProps | Baja | 1h | Ninguna | `npm run lint` sin errores. Importable desde CrewCanvas. Render visual correcto con mock data |
| 4 | **Crear `TaskNode.tsx`:** `dashboard/components/builder/nodes/TaskNode.tsx`. Card con description + expectedOutput + assignedAgent badge + Handles Left/Right. Mismo patrón AgentNode | Baja | 0.75h | Ninguna | `npm run lint` sin errores. Render visual correcto con mock data |
| 5 | **Crear `crewCodeGen.ts` + `canvasUtils.ts` + `crewTemplates.ts`:** 3 archivos en `dashboard/lib/`. Funciones puras: generación Python, serialización canvas ↔ payloads, 4 presets de crews | Media | 2h | Ninguna | `generateCrewPy(sampleNodes, sampleEdges)` → código Python válido (test en REPL). `canvasToExportPayload` produce `{agents: AgentExportItem[]}`. `CREW_TEMPLATES.length >= 4` |
| 6 | **Crear `CrewCanvas.tsx`:** `dashboard/components/builder/CrewCanvas.tsx`. Canvas completo con ReactFlow + sidebar arrastrable + toolbar (Export, Run All, Preview Code, Save Crew, Templates) + DnD HTML5 + validación onConnect + validación visual (warning agentes sin tareas) | Alta | 4h | Tareas 3, 4, 5 | `npm run lint` sin errores. Canvas renderiza drag-drop funcional. Edges visibles. MiniMap/Controls funcionales |
| 7 | **Reemplazar `BuilderCanvas.tsx` + actualizar `BuilderLayout.tsx`:** BuilderCanvas wrapper dynamic import de CrewCanvas. BuilderLayout añade Tabs "Agent Form" / "Crew Canvas" | Media | 1h | Tarea 6 | `npm run build` sin errores SSR. Ruta `/builder` muestra tabs funcionales. Cambiar a "Crew Canvas" muestra CrewCanvas sin crash |
| 8 | **Actualizar `types.ts`:** Añadir interfaces `CanvasAgentNode`, `CanvasTaskNode`, `CanvasNodeType`, `CrewGraphNode`, `CrewGraphEdge`, `CrewGraph` | Baja | 0.25h | Ninguna | TypeScript compila. `npm run lint` sin errores de tipo |
| 9 | **Integrar handlers Export / Run All / Preview Code / Save en CrewCanvas:** Conectar botones: Export → `canvasToExportPayload` + `POST /api/bundles/export` + descarga ZIP; Run All → `POST /agents/{role}/run` secuencial + polling; Preview Code → `generateCrewPy` en Dialog; Save Crew → `nodesToSnapshot` + localStorage + download JSON | Fullstack | 2h | Tareas 1, 2, 5, 6 | Botón Export descarga ZIP. Botón Run All ejecuta agentes y muestra resultados. Botón Preview Code muestra código Python. Botón Save persiste en localStorage |
| 10 | **Tests unitarios:** `tests/unit/test_crew_endpoints.py` (GET /agents, POST /api/workflows, fap crew validate). `tests/unit/test_canvas_serialize.py` (canvasToExportPayload produce estructura válida) | Media | 1.5h | Tareas 1, 2, 5 | `uv run pytest tests/unit/test_crew_endpoints.py -v` pasa. `uv run pytest tests/unit/test_canvas_serialize.py -v` pasa |
| 11 | **Validar flujo end-to-end:** Open `/builder` → Crew Canvas tab → Drag agent → Add task → Connect → Preview Code → Export → Run All → Verify results | Fullstack | 0.5h | Todas las anteriores | Todos los criterios §5 pasan. Sin errores en consola browser. `npm run lint` backend + frontend limpios |
| | **TOTAL** | | **~16h** | | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling (`fap crew` CLI).** Implementador DEBE ejecutarla primero y usar la herramienta resultante para validar el resto del paso (dogfooding obligatorio). Usar `fap crew validate` para testear snapshots de canvas antes de exportar.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ReactFlow SSR crash en Next.js | Alta | ReactFlow usa `window`/`document` nativos. SSR sin `dynamic import` rompe el build | `BuilderCanvas.tsx` ya usa `dynamic(() => import(...), { ssr: false })`. CrewCanvas envuelto en `ReactFlowProvider`. Mantener patrón |
| `GET /agents` endpoint no existe → sidebar vacío | Alta | Plan asume listado de agentes pero solo existe GET by-role | Crear endpoint como Tarea 1 (bloqueante). Sin este endpoint, sidebar no carga y drag-drop no funciona |
| Sin persistencia → pérdida de trabajo al refrescar | Alta | Canvas state es local. Recargar = canvas vacío | Botón "Save Crew" + autosave cada 30s vía localStorage. `fap crew save` para persistencia en disco. Post-MVP: tabla `crew_canvases` |
| Export sin tasks frustra expectativa del usuario | Media | Usuario espera crew completo (agentes+tareas) en ZIP. Solo agentes van al ZIP | Dialog warning: "Tasks and connections not exported (bundle-schema-v2.md limitation)". Botón "Copy as JSON" sí incluye grafo completo. Roadmap: bundle v3 |
| Ejecución secuencial lenta (>120s con 4 agentes) | Media | "Run All" ejecuta agentes 1×1. 4 agentes × 30s = 120s | Barra de progreso por agente. Ejecución paralela vía `Promise.all` si agentes no tienen dependencias |
| HTML5 DnD incompatibilidad cross-browser | Media | Firefox vs Chrome manejan `dataTransfer` diferente. Tipos MIME pueden no coincidir | Usar `text/plain` como MIME first + fallback `application/json`. Probar en Chrome + Firefox + Edge |
| `flow_type` UNIQUE constraint → 409 en POST /api/workflows repetido | Media | Colisión cuando usuario guarda crew con mismo nombre | Generar `flow_type` idempotente: `crew_{name}_{timestamp}`. Manejar 409 con toast "Crew name already exists. Use a different name." |
| ReactFlow re-renders con custom nodeTypes | Media | Definir `nodeTypes` dentro del componente ReactFlow causa re-mounts | Definir `nodeTypes` como constante fuera del componente: `const nodeTypes = useMemo(() => ({ agentNode: AgentNode, taskNode: TaskNode }), [])` |
| Colisión de roles al exportar | Media | 2 agentes con mismo `role` → ZIP duplicado → executor falla | Validación frontend: detectar roles duplicados → deshabilitar Export + toast "Duplicate roles. Each agent must have unique role." |
| Sin undo/redo → re-trabajo si borra nodo | Media | Borrar nodo accidental = perder datos | Post-MVP: history stack con Ctrl+Z. MVP: confirmación en delete con Dialog "Delete this node?" |
| Memoria / rendimiento con >20 nodos | Baja | ReactFlow virtualiza pero >20 nodos podrían degradarse por DOM | ReactFlow maneja 500+ nodos en práctica. <20 nodos en MVP no es problema. Documentado en roadmap |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | GET /agents lista agentes de org con `active_only=true` | `GET /agents?active_only=true` + `X-Org-ID` header | 200 `{ agents: [...] }`. Solo agentes `is_active=true` de la org |
| TP-2 | GET /agents con org sin agentes | `GET /agents` con org sin datos | 200 `{ agents: [] }` (no 404, no error) |
| TP-3 | POST /api/workflows crea workflow_template | `{ name: "Test Crew", flow_type: "test_crew", definition: { steps: [...], agents: [...] }, status: "draft" }` | 201 `{ id: uuid, flow_type: "test_crew", status: "draft" }` |
| TP-4 | POST /api/workflows con `flow_type` duplicado (misma org) | Flow con mismo `flow_type` ya existente en DB | 409 Conflict con mensaje de error |
| TP-5 | `canvasToExportPayload()` con 1 AgentNode | nodes = `[{ type: 'agentNode', data: { role: 'researcher', goal: 'Research', tools: ['web_search'] } }]` | `{ agents: [{ role: 'researcher', soul_json: { goal: 'Research', backstory: '' }, allowed_tools: ['web_search'], max_iter: 3 }] }` |
| TP-6 | `generateCrewPy()` con 1 agente + 1 tarea | 1 AgentNode + 1 TaskNode + 1 edge | String Python con `from crewai import Agent, Task, Crew, Process`, `agent_0 = Agent(...)`, `task_0 = Task(..., agent=agent_0)`, `crew = Crew(agents=[agent_0], tasks=[task_0], process=Process.sequential)`, `result = crew.kickoff()` |
| TP-7 | `fap crew validate` detecta agente sin tarea | JSON con 1 AgentNode, 0 TaskNodes, 0 edges | Output: warnings "Agent 'researcher' has no assigned tasks" |
| TP-8 | `fap crew validate` detecta rol duplicado | JSON con 2 AgentNodes ambos con `role: "researcher"` | Output: errors "Duplicate role 'researcher' detected" |
| TP-9 | Drag & drop desde sidebar → canvas | Sidebar ítem arrastrado a canvas con `onDrop` | AgentNode creado en posición de drop. `node.type === 'agentNode'`. Datos del sidebar correctos en `node.data` |
| TP-10 | Edge agente→tarea se crea | Connect Handle Bottom (AgentNode) → Handle Left (TaskNode) | Edge visible con `animated: true`, `style: { stroke: '#555' }`. Sin error en consola |

**Comando para ejecutar tests:** `uv run pytest tests/unit/test_crew_endpoints.py tests/unit/test_canvas_serialize.py -v`

---

## 🔮 Roadmap (NO implementar ahora)

| Item | Descripción | Prioridad |
|---|---|---|
| `crew_runner_flow` backend | Flow multi-agente con `Crew(agents=[...], tasks=[...], process=...)`. Reemplaza ejecución secuencial frontend | Post-MVP |
| Bundle schema v3 | `ExportBundleRequest` con `tasks` + `edges`. Round-trip completo canvas ↔ bundle ZIP | Post-MVP |
| Persistencia canvas en DB | Tabla `crew_canvases(org_id, name, snapshot JSONB)`. Autosave real + históricos | Post-MVP |
| Undo/Redo en canvas | History stack con Ctrl+Z / Ctrl+Y. Zustand `temporal` middleware | Post-MVP |
| Validación de ciclos en grafo | `flow_registry.detect_cycles()` aplicado a edges del canvas. Warning antes de export/run | Post-MVP |
| Collaborative editing | Supabase Realtime multi-usuario en mismo canvas. WebSockets para sincronización | Post-MVP |
| Auto-layout | Algoritmo DAG / force-directed para organizar nodos automáticamente | Post-MVP |
| `fap crew validate` mejorado | Validación avanzada: detectar tools no registradas, dependencias circulares, missing fields | Post-MVP |
| ToolNode como nodo independiente | Cuando tools sean ejecutables independientes (fuera de contexto de agente) | Post-MVP |
| Migración `reactflow` v11 → `@xyflow/react` v12 | v12 cambió API drásticamente. Evaluar breaking changes antes de migrar | Post-MVP |

---

## 📊 Nota sobre calidad de aportes por análisis

| Agente | Score | Fortalezas | Debilidades |
|:---|:---|:---|:---|
| **step** | 4.9 | 27 verificaciones. 7 discrepancias. Interfaz exacta por tarea. DX concreto (`fap crew` CLI). 4 stages profundamente cubiertos. crewCodeGen con firma completa. | — |
| **glm5.1** | 4.8 | 25 verificaciones. 5 discrepancias. DX dual (`crew export` + `crew validate`). Tablas DB con detalles de schema, índices, RLS | zustand propuesto pero no necesario para MVP |
| **dsp** | 4.7 | 30 verificaciones (récord). Suprimió ToolNode (decisión correcta). crewCodeGen con output de ejemplo. CrewTemplates con 4 presets | DX `fap crew visualize` es UI-acoplado (mejor CLI puro) |
| **ring** | 4.5 | 19 verificaciones. 9 discrepancias (más discrepancias detectadas). 15 tareas en plan. 2 herramientas DX | 34h estimación inflada. Plan demasiado granular (15 tareas) |
| **qwen3.6** | 4.3 | 18 verificaciones. 4 discrepancias. Tabla de conexiones válidas. DX dual (`crew validate` + `crew export`). | "Run Crew" solo preview Python (sin ejecución). Roadmap extenso pero menos tareas core |
| **hy3** | 2.5 | Caveman conciso pero cubre 4 stages. 16 verificaciones | Muy breve (107 líneas). DX es `create-flow-node` (generador boilerplate, no herramienta de usuario). Sin schemas DB, sin tipos, sin detalles de endpoints. Plan 8h subestimado |
| **mm2.5** | 2.5 | 14 verificaciones. `CrewDebugPanel` como DX inline | **0 discrepancias detectadas** (falso negativo crítico: pasó por alto DnD, flow crew, GET /agents, export tasks/edges). DX es componente React, no CLI independiente. Sin análisis de schemas DB. Sin validación de conexiones tipo tabla |
| **lgn** | 2.0 | 12 verificaciones. 3 discrepancias. Plan 7 tareas (7h) ágil | Sin verificación de endpoints nuevos. Sin schemas DB mencionados. Sin tipos de datos. DX es `crew-validator` standalone (sin integrar en CLI FAP). Plan subestimado. Falta análisis de gaps backend críticos |
