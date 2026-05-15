# 🧠 Análisis Técnico — Paso 07: Canvas visual — ensamblaje de crews

> **Agente:** glm5.1 | **Paso:** 07 | **Fase:** guiAgentGenerator

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---------|-------------|--------|-----------|
| 1 | `reactflow` v11 instalado | `cat dashboard/package.json` → `"reactflow": "^11.11.4"` | ✅ VERIFICADO | `package.json` dependencia existente |
| 2 | `BuilderCanvas.tsx` existe con placeholder | `ls dashboard/components/builder/BuilderCanvas.tsx` | ✅ VERIFICADO | Archivo existe, línea 39: `"Placeholder for Step 07"` |
| 3 | ReactFlow dynamic import con `ssr: false` | `BuilderCanvas.tsx:6-30` | ✅ VERIFICADO | `dynamic(() => import('reactflow')..., { ssr: false })` |
| 4 | `BuilderLayout.tsx` usa `BuilderCanvas` como hijo | `BuilderLayout.tsx:5,72` | ✅ VERIFICADO | Import + render en grid 60/40 |
| 5 | `AgentForm.tsx` exporta `AgentFormData` type | `AgentForm.tsx:44` | ✅ VERIFICADO | `export type AgentFormData = z.infer<typeof agentFormSchema>` |
| 6 | `POST /agents` endpoint existe (create/upsert agente) | `agents.py:51-101` | ✅ VERIFICADO | `create_agent()` con `TenantClient` + RLS |
| 7 | `GET /api/tools/available` endpoint existe | `tools.py:46-63` | ✅ VERIFICADO | Retorna `ToolsListResponse` con `ToolInfo[]` |
| 8 | `GET /api/templates` endpoint existe | `templates.py:54-67` | ✅ VERIFICADO | Lista + filtro `?category=` |
| 9 | `POST /api/bundles/export` endpoint existe | `bundles.py:199-253` | ✅ VERIFICADO | `ExportBundleRequest` → ZIP bytes |
| 10 | `ExportBundleRequest` schema en `bundle_schemas.py:111-116` | Pydantic con `agents: List[AgentExportItem]`, `skills: Optional[List[SkillExportItem]]` | ✅ VERIFICADO | Compatible con exportar crews |
| 11 | `POST /flows/{flow_type}/run` endpoint existe | `flows.py:142-186` | ✅ VERIFICADO | Retorna `task_id` + `status: "accepted"`, background task |
| 12 | `GET /tasks/{task_id}` endpoint existe | `tasks.py:69-91` | ✅ VERIFICADO | Polling con `verify_org_membership` |
| 13 | `AgentFormData` tiene 11 campos (role, goal, backstory, llmProvider, llmModel, allowedTools, maxIter, verbose, reasoning, injectDate, memory) | `AgentForm.tsx:30-42` | ✅ VERIFICADO | Zod schema completo |
| 14 | `ProviderModels` mapa estático en `constants.ts:20-25` | 4 providers × ≥2 modelos | ✅ VERIFICADO | `PROVIDER_MODELS` constante |
| 15 | `agent_catalog` tabla con RLS `tenant_isolation` | Migración `004_agent_catalog.sql:6-23` | ✅ VERIFICADO | `org_id`, `role`, `soul_json`, `allowed_tools`, `max_iter` |
| 16 | `workflow_templates` tabla con `definition` JSONB | Migración `006_workflow_templates.sql:6-44` | ✅ VERIFICADO | `definition` JSONB con `steps`, `agents`, `approval_rules` |
| 17 | `FlowInfo` type en frontend | `types.ts:241-248` | ✅ VERIFICADO | `flow_type`, `name`, `description`, `input_schema`, `depends_on`, `category` |
| 18 | `FlowsListResponse` type en frontend | `types.ts:250-252` | ✅ VERIFICADO | `{ flows: FlowInfo[] }` |
| 19 | `api.get()` / `api.post()` helper en `api.ts` | `api.ts:54-77` | ✅ VERIFICADO | `fapFetch` wrapper con auth + org headers |
| 20 | `GET /flows/available` endpoint retorna flows con `input_schema` | `flows.py:76-110` | ✅ VERIFICADO | `FlowInfo` incluye `input_schema: Optional[Dict]` |
| 21 | Zustand NO está instalado | `grep zustand dashboard/package.json` → no encontrado | ❌ DISCREPANCIA | ReactFlow necesita state manager para nodos/edges. Zustand es la opción recomendada por ReactFlow v11 |
| 22 | `@xyflow/react` NO está instalado (v12) | `grep xyflow dashboard/package.json` → no encontrado | ✅ VERIFICADO | Correcto — se usa `reactflow` v11 |
| 23 | `useCurrentOrg` hook existe | `dashboard/hooks/useCurrentOrg.ts` | ✅ VERIFICADO | Retorna `{ orgId }` para TenantClient |
| 24 | `ToolMultiSelect.tsx` componente existe | `dashboard/components/builder/ToolMultiSelect.tsx` | ✅ VERIFICADO | Checkboxes + búsqueda + badges por source |
| 25 | `TemplatePicker.tsx` componente existe | `dashboard/components/builder/TemplatePicker.tsx` | ✅ VERIFICADO | Grid cards + búsqueda + filtro categoría |

**Discrepancias encontradas:**

1. **D1: Zustand NO instalado** — ReactFlow v11 recomienda `zustand` para manejo de estado de nodos/edges. Actualmente no está en `package.json`. El canvas necesita un store para nodos, edges, y metadatos de crew. **Resolución:** Instalar `zustand` como dependencia nueva. No es breaking change. Se creará `dashboard/lib/stores/crew-store.ts` con el store centralizado.

2. **D2: Plan pide "TaskNode" pero `tasks` en contexto del builder son Tasks de CrewAI, no `tasks` DB** — El plan dice "TaskNode" para representar tareas del crew (description + expected_output), pero la tabla `tasks` en Supabase es para tracking de ejecución. Las "tasks" en CrewAI son `Task(description=, expected_output=, agent=)`. El grafo del canvas necesita distinguir entre "task de crew" (nodo visual) y "task de ejecución" (registro DB). **Resolución:** En el canvas, `TaskNode` representa una tarea de crew con `description` y `expected_output`. Serializa dentro de `workflow_templates.definition.steps[]`. No confundir con tabla `tasks`.

3. **D3: Plan pide "Export as Crew → JSON compatible con bundle-schema-v2" pero el schema actual espera `agents/*.json` + `manifest.json`** — `BundleManager.create_bundle()` accepta `agents: List[Dict]` + `flows: List[Dict]` + `skills: Dict[str,str]`. Un "crew" en FAP es un conjunto de agentes + tareas (= workflow_template). El JSON exportado debe mapear nodos-agentes a `agents[]` y nodos-tareas a `flows[].definition.steps[]`. **Resolución:** El botón "Export as Crew" llamará `POST /api/bundles/export` con `agents` derivados de los nodos-agente del canvas. Las tareas del crew se serializan como un `workflow_template.definition` incrustado en `flows[]`. El Python preview es post-MVP.

4. **D4: Plan pide "Run Crew → POST /flows/{flow_type}/run" pero esto requiere que el workflow_template ya exista en DB** — No hay endpoint para crear un `workflow_template` desde el frontend. El canvas necesitaría un paso intermedio: crear el template en DB, luego ejecutarlo. **Resolución:** Crear endpoint `POST /api/workflows` (o extender `workflows.py`) para guardar el template antes de ejecutar. Alternativa: "Run Crew" primero guarda el template, luego ejecuta `POST /flows/{flow_type}/run`. La segunda opción es MVP: el canvas serializa el grafo, guarda como `workflow_template`, y ejecuta el flow.

5. **D5: `getNodeTypes` y custom nodes necesitan registro en ReactFlow** — ReactFlow v11 requiere pasar `nodeTypes` como prop al `<ReactFlow>` component. Los custom nodes (`AgentNode`, `TaskNode`, `ToolNode`) deben definirse вне del render cycle (useMemo o fuera del componente) para evitar re-renders. **Resolución:** Definir `nodeTypes` como constante fuera del componente. No usar `useState` para nodeTypes.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas (directa o indirectamente)

- **`agent_catalog`** — Lectura para poblar sidebar de agentes existentes. Schema: `id UUID, org_id UUID, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INT, is_active BOOLEAN`. RLS: `tenant_isolation`. UNIQUE `(org_id, role)`.
- **`workflow_templates`** — Escritura al guardar/ejecutar crew. Schema: `id UUID, org_id UUID, name TEXT, flow_type TEXT, definition JSONB, version INT, status TEXT, is_active BOOLEAN`. RLS: `tenant_isolation`. UNIQUE por `flow_type` (global con migration 0026 → UNIQUE por org).
- **`tasks`** — Escritura indirecta vía `POST /flows/{flow_type}/run`. Schema: `id UUID, org_id UUID, flow_type TEXT, status TEXT, result JSONB, error TEXT, tokens_used INT, correlation_id TEXT`. RLS: `tenant_isolation`.

### Cambios de schema necesarios

- **NINGUNO.** Toda la data persiste en tablas existentes. El canvas es una representación visual en memoria (React state + zustand store) que se serializa al guardar.

### Integridad referencial

- `workflow_templates.org_id` → `organizations.id` (FK existente)
- `agent_catalog.org_id` → `organizations.id` (FK existente)
- Canvas serializa referencias a agentes por `role` (string), no por `id` (UUID). Consistente con `BaseCrew(org_id, role=role)`.

### RLS policies aplicables

- `agent_catalog_tenant_isolation` — Solo lectura de agentes propios. Canvas usa `GET /agents/by-role/{role}` o `TenantClient` para cargar sidebar.
- `workflow_templates`相同 policy. `POST /api/workflows` usará `TenantClient` para escritura.

### Índices necesarios

- Ya existen: `idx_agent_catalog_org_role` en `(org_id, role) WHERE is_active = TRUE`
- Ya existen: `idx_workflow_templates_org_active` en `(org_id) WHERE is_active = TRUE`

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos

#### `dashboard/components/builder/nodes/AgentNode.tsx`
- **Firma:** `function AgentNode({ data, id }: NodeProps<AgentNodeData>)`
- **Tipo:** `AgentNodeData = { role: string; goal: string; allowedTools: string[]; llmProvider: string; llmModel: string; maxIter: number }`
- **Comportamiento:** Muestra card con role, goal truncado, badges de tools, icono de provider. Handle de salida (source) para conectar a TaskNode. Color de borde por provider (groq=verde, openai=azul, anthropic=naranja, openrouter=violeta).
- **Patrón:** ReactFlow custom node con `Handle` component. Seguir patrón de ReactFlow v11 docs.

#### `dashboard/components/builder/nodes/TaskNode.tsx`
- **Firma:** `function TaskNode({ data, id }: NodeProps<TaskNodeData>)`
- **Tipo:** `TaskNodeData = { description: string; expectedOutput: string; assignedAgent?: string }`
- **Comportamiento:** Muestra card con description, expected_output truncado. Handles de entrada (target) desde AgentNode y de salida (source) hacia ToolNode. Badge de agente asignado si existe.

#### `dashboard/components/builder/nodes/ToolNode.tsx`
- **Firma:** `function ToolNode({ data, id }: NodeProps<ToolNodeData>)`
- **Tipo:** `ToolNodeData = { name: string; source: 'local' | 'mcp'; description: string }`
- **Comportamiento:** Muestra chip con nombre de tool, badge de source. Handle de entrada (target) desde TaskNode. Color por source (local=azul, mcp=púrpura).

#### `dashboard/components/builder/CrewCanvas.tsx`
- **Firma:** `function CrewCanvas({ agents, onExport, onRun }: CrewCanvasProps)`
- **Tipo:** `CrewCanvasProps = { agents: AgentFormData[]; onExport: (crewData: CrewData) => void; onRun: (flowType: string) => void }`
- **Comportamiento:** Canvas ReactFlow completo con:
  - Sidebar izquierdo: agentes existentes + tareas + tools disponibles
  - Área central: drop zone para arrastrar nodos
  - Toolbar: Export as Crew + Run Crew + zoom controls + minimap
  - Validación visual: agentes sin tareas = warning border
- **Patrón:** Reemplaza `BuilderCanvas.tsx` actual (placeholder). Usa zustand store para nodos/edges.

#### `dashboard/lib/stores/crew-store.ts`
- **Firma:** `function useCrewStore(): CrewStore`
- **Tipo:** Store zustand con `nodes: Node[]`, `edges: Edge[]`, `selectedNodeId: string | null`, `onNodesChange`, `onEdgesChange`, `onConnect`, `addNode`, `removeNode`, `updateNodeData`, `serialize` (→ JSON compatible con bundle-schema-v2), `deserialize` (← JSON → nodos/edges)
- **Patrón:** Zustand store con `immer` middleware para inmutabilidad. Seguir patrón recomendado de ReactFlow v11.

### Componentes modificados

#### `dashboard/components/builder/BuilderLayout.tsx`
- **Cambio:** Importar `CrewCanvas` en lugar de `BuilderCanvas`. Pasar `agents` list (desde `GET /agents` o desde el formulario) y callbacks `onExport`/`onRun`.
- **Patrón existente:** `BuilderLayout.tsx:72` ya renderiza `<BuilderCanvas />` — reemplazar por `<CrewCanvas />` cuando el canvas esté listo.

#### `dashboard/components/builder/BuilderCanvas.tsx`
- **Cambio:** Deprecar o vaciar. El componente pasa a ser ORQUESTADOR: si el usuario está en modo "single agent", mostrar AgentForm solo; si está en modo "crew", mostrar CrewCanvas. MVP: reemplazar directamente por CrewCanvas.

### Imports exactos

```typescript
// AgentNode.tsx
import { Handle, Position, type NodeProps } from 'reactflow'

// CrewCanvas.tsx
import ReactFlow, { Controls, MiniMap, Background, type Node, type Edge, type Connection } from 'reactflow'
import 'reactflow/dist/style.css'
import { useCrewStore } from '@/lib/stores/crew-store'

// crew-store.ts
import { create } from 'zustand'
import { type Node, type Edge } from 'reactflow'
```

### Modularidad

- **AgentNode, TaskNode, ToolNode** → Componentes puros, sin estado propio. Reciben data vía `NodeProps.data`.
- **CrewCanvas** → Orquestador del canvas. Consume store zustand. No maneja lógica de negocio — delega a callbacks `onExport` / `onRun`.
- **crew-store** → Estado centralizado. Serialización/deserialización aislada del componente.

### Calidad

- ReactFlow v11 handles → re-renders eficientes si nodeTypes se definen fuera del render cycle.
- Zustand evita prop drilling. Store accesible desde cualquier componente inside `<ReactFlowProvider>`.
- Validación visual: nodos desconectados rogados con borde amarillo.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes consumidos por el canvas

| Endpoint | Método | Auth | Uso en canvas |
|----------|--------|------|----------------|
| `GET /api/tools/available` | GET | `require_org_id` | Poblar ToolNode sidebar |
| `GET /api/templates` | GET | None | Poblar templates sidebar (ya integrado) |
| `GET /agents/by-role/{role}` | GET | `require_org_id` | Cargar config de agente existente |
| `GET /flows/available` | GET | `require_org_id` | Listar flows disponibles (sidebar de flows) |
| `POST /flows/{flow_type}/run` | POST | `require_org_id` | Ejecutar crew armado |
| `GET /tasks/{task_id}` | GET | `verify_org_membership` | Polling de resultado del run |
| `POST /agents` | POST | `require_org_id` | Guardar agente creado en canvas |
| `POST /api/bundles/export` | POST | `require_org_id` | Exportar crew como ZIP |

### Endpoint nuevo necesario

#### `POST /api/workflows` — Crear workflow_template desde canvas

- **Ruta:** `POST /api/workflows`
- **Auth:** `Depends(require_org_id)`
- **Input:**
  ```json
  {
    "name": "My Crew",
    "flow_type": "my_crew",
    "definition": {
      "steps": [...],
      "agents": [...],
      "approval_rules": []
    },
    "status": "draft" | "active"
  }
  ```
- **Output:** `201 Created` con `{ id, flow_type, status }`
- **Patrón:** Seguir `agents.py:51-92` — TenantClient + check de duplicados en `flow_type`.
- **Alternativa MVP:** Reutilizar `POST /flows/{flow_type}/run` directamente, sin crear template. El canvas genera `flow_type` dinámicamente. **Problema:** `BaseCrew` espera un `role` existente en `agent_catalog`. No acepta definición inline.
- **Decisión MVP:** "Run Crew" requiere agentes guardados en `agent_catalog` previamente. El canvas:
  1. Guarda cada agente con `POST /agents` (si no existe)
  2. Crea un `workflow_template` con `POST /api/workflows` (nuevo endpoint)
  3. Ejecuta con `POST /flows/{flow_type}/run`

### Flow de datos: Export as Crew

```
Canvas (nodos/edges) → crew-store.serialize() → JSON con:
  - agents: [AgentExportItem, ...]  ← derivado de AgentNode data
  - definition: { steps: [...], agents: [...] }  ← derivado de TaskNode + edges
→ POST /api/bundles/export → ZIP descargable
```

### Flow de datos: Run Crew

```
Canvas (nodos/edges) → Para cada AgentNode:
  1. POST /agents → guarda en agent_catalog
→ crew-store.serializeDefinition() → JSON definition
→ POST /api/workflows → crea workflow_template en DB
→ POST /flows/{flow_type}/run → inicia ejecución async
→ GET /tasks/{task_id} → polling cada 2s
```

### Middleware

- `require_org_id` en todos los endpoints nuevos (consistente con pattern existente).
- `verify_org_membership` para polling de tasks (ya existente).

### Error handling

- Agente sin role → 422 del backend (AgentCreate validation ya rechaza).
- Flow type duplicado → 409 Conflict (UNIQUE constraint en workflow_templates).
- Network error → `toast.error()` con mensaje del backend.
- Agente desconectado (sin tareas) → warning en UI, NO bloquea export.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: DB → Backend → Frontend → UX

1. **Usuario abre Builder** → ` BuilderLayout` carga `CrewCanvas` con sidebar vacío
2. **Usuario arrastra agente desde sidebar** → Drag & Drop sobre canvas → `AgentNode` aparece con data del sidebar
3. **Usuario arrastra tarea** → `TaskNode` aparece
4. **Usuario conecta agente → tarea** → Edge (source → target) se crea
5. **Usuario asigna tools** → Arrastra `ToolNode` o selecciona desde sidebar
6. **Usuario hace clic "Export as Crew"** → `crew-store.serialize()` → `POST /api/bundles/export` → ZIP descargable
7. **Usuario hace clic "Run Crew"** → Guarda agentes → Crea template → `POST /flows/{flow_type}/run` → Polling → Resultado

### Coherencia de decisiones

- **AgentNode data** = `AgentFormData` (mismo schema que `AgentForm.tsx:30-42`). Consistente entre formulario y canvas.
- **Serialización** usa `ExportBundleRequest` del backend (`bundle_schemas.py:111-116`). Round-trip compatible con import.
- **`workflow_templates.definition` JSONB** tiene estructura `{ steps: [...], agents: [...], approval_rules: [] }`. Consistente con migración `006`.

### Gaps

1. **No existe `GET /agents` endpoint (list all)** — El sidebar del canvas necesita listar todos los agentes de la org. Actualmente solo existe `GET /agents/{agent_id}/detail` y `GET /agents/by-role/{role}`. **Resolución:** Crear endpoint `GET /agents` que retorne array de `AgentResponse` filtrado por `org_id`. MVP: alternativa es usar Supabase browser client directo, pero eso rompe RLS (corrección D4). Necesario endpoint backend con `TenantClient`.

2. **No existe `POST /api/workflows` endpoint** — Para guardar `workflow_template` desde el canvas. **Resolución:** Crear endpoint en `src/api/routes/workflows.py` (archivo ya existe con 2415 bytes).

3. **`workflow_templates` tiene UNIQUE global por `flow_type`** — Migración 0026 cambió a `UNIQUE(org_id, flow_type)`. **Resolución:** MVP: generar `flow_type` idempotente como `crew_{timestamp}` o permitir al usuario nombrar el crew.

4. **`definition.steps[].agent_role` usa `role` string** — Consistente con `BaseCrew(org_id, role=role)`. Las conexiones AgentNode→TaskNode generan `steps[].agent_role = AgentNode.data.role`.

5. **ReactFlow mini-map provisto por plan** — `BuilderCanvas.tsx:9` ya importa `MiniMap`. `CrewCanvas` debe reutilizar. ✅ Sin gap.

6. **Python preview** — Plan dice "Vista previa de código Python generado". Generar código Python equivalente al grafo es un feature significativo. **Resolución MVP:** Postponer Python preview. Export como JSON (bundle-schema-v2) es el entregable principal. Python preview como blue item en roadmap.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap crew export
- **Qué automatiza:** Exportar crew desde CLI sin abrir el dashboard. Útil para CI/CD y scripts.
- **Tipo:** CLI (Typer sub-app)
- **Cómo se usa:** `fap crew export --org-id ORG_ID --name "Marketing Crew" --agents '["analyst","writer"]' --output marketing_crew.zip`
- **Impacto para el usuario final:** Permite automatizar exportación de crews en pipelines. Elimina paso manual de abrir dashboard → canvas → export.
- **Prioridad:** Tarea 0 — implementar antes que el canvas
```

Alternativa DX adicional:

```
### Herramienta Propuesta: fap crew validate
- **Qué automatiza:** Validar que un JSON de crew (nodos/edges) tiene todos los campos requeridos antes de export o run.
- **Tipo:** CLI (Typer)
- **Cómo se usa:** `fap crew validate --file crew_definition.json`
- **Impacto para el usuario final:** Catch errors de serialización antes de enviar al backend. Ahorra round-trips.
- **Prioridad:** Post-MVP (blue)
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] AgentNode renders con role + goal + tools badges
✅ [CODE] TaskNode renders con description + expected_output + agente asignado
✅ [CODE] ToolNode renders con name + source badge
✅ [CODE] CrewCanvas sidebar muestra agentes existentes arrastrables
✅ [CODE] Drag & drop de nodos al canvas funciona
✅ [CODE] Edges entre nodos (agent → task) se crean correctamente
✅ [CODE] Nodo de agente sin tareas conectadas muestra warning visual
✅ [CODE] "Export as Crew" genera JSON compatible con bundle-schema-v2
✅ [BACKEND] GET /agents endpoint lista agentes de la org
✅ [BACKEND] POST /api/workflows crea workflow_template con definition JSONB
✅ [FULLSTACK] "Run Crew" guarda agentes + crea template + ejecuta flow
✅ [FULLSTACK] Canvas tiene Minimap + zoom controls
✅ [FULLSTACK] zustand store maneja nodos/edges sin prop drilling
✅ [DX] fap crew export ejecuta sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Zustand no instalado → canvas sin state manager | Alta | Dependencia nueva que rompe build si no se instala | Instalar zustand como Tarea 0 antes de cualquier componente canvas |
| ReactFlow v11 nodeTypes se re-define cada render | Alta | Definir nodeTypes dentro del componente causa re-mount infinito | Definir `nodeTypes` como constante fuera del componente o con `useMemo` |
| `POST /api/workflows` endpoint no existe | Alta | Canvas no puede persistir workflow_template antes de run | Crear endpoint como parte del paso (Tarea 4) |
| `GET /agents` (list all) no existe | Alta | Sidebar no puede cargar agentes existentes sin listarlos | Crear endpoint como parte del paso (Tarea 3) |
| `flow_type` UNIQUE constraint genera 409 en "Run Crew" repetido | Media | Usuario hace clic "Run Crew" dos veces con mismo nombre | Generar `flow_type` idempotente o usar v2 incremental |
| Canvas SSR crash (ReactFlow no SSR-safe) | Media | Import estático rope en server component | Dynamic import con `ssr: false` (patrón ya aplicado en `BuilderCanvas.tsx`) |
| Serialización de edges a workflow definition ambigua | Media | Múltiples agentes → una tarea, o una secuencia de agentes | Definir contrato claro: AgentNode→TaskNode edge = `steps[].agent_role`. Tasks secuenciales = orden de edges. |
| Python preview genera mantenimiento continuo | Baja | CrewAI API cambia, sintaxis Python diverge del JSON | Postponer a post-MVP. Blue en roadmap. |
| Performance con >20 nodos en canvas | Baja | ReactFlow re-renderiza todos los nodos en cada change | zustand + memoización por nodo. Probar con 20+ nodos post-MVP. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|------------------|-------|-------------|-------------|--------------|-------------|
| 0 | **DX & Tooling:** `fap crew export` | `src/cli/commands/crew_export.py` | `def export_crew(name: str, agents: list[str], org_id: str, output: str, include_skills: bool): ...` | `src/cli/commands/bundle_export.py:34-135` | DX | Media | 1h | Ninguna | → verificar: `fap crew export --help` ejecuta sin errores |
| 1 | Instalar zustand + crear crew-store | `dashboard/lib/stores/crew-store.ts` | `interface CrewStore { nodes: Node[]; edges: Edge[]; addNode(type, data): void; removeNode(id): void; updateNodeData(id, data): void; onNodesChange(changes): void; onEdgesChange(changes): void; onConnect(connection): void; serialize(): CrewData; deserialize(data: CrewData): void; selectedNodeId: string \| null }` | ReactFlow v11 zustand example (docs) | CODE | Media | 1.5h | Ninguna | → verificar: `npm run build` sin errores TS + store importa desde `@/lib/stores/crew-store` |
| 2 | Crear AgentNode, TaskNode, ToolNode | `dashboard/components/builder/nodes/AgentNode.tsx`, `TaskNode.tsx`, `ToolNode.tsx` | `AgentNode({ data: AgentNodeData, id }: NodeProps<AgentNodeData>)` — `AgentNodeData = { role: string; goal: string; allowedTools: string[]; llmProvider: string; llmModel: string; maxIter: number }` — TaskNodeData = `{ description: string; expectedOutput: string; assignedAgent?: string }` — ToolNodeData = `{ name: string; source: 'local' \| 'mcp'; description: string }` | ReactFlow custom node docs | CODE | Media | 2h | Tarea 1 | → verificar: Render de cada nodo isoladamente con mock data sin crash |
| 3 | Crear `GET /agents` endpoint (list all) | `src/api/routes/agents.py` (extensión) | `async def list_agents(org_id: str = Depends(require_org_id)) -> List[AgentResponse]` — Retorna todos los agentes activos de la org | `src/api/routes/agents.py:51-92` (create_agent pattern) | BACKEND | Baja | 0.5h | Ninguna | → verificar: `GET /agents` retorna array de AgentResponse con org_id filtrado |
| 4 | Crear `POST /api/workflows` endpoint | `src/api/routes/workflows.py` (modificación) | `class WorkflowCreate(BaseModel): name: str; flow_type: str; definition: Dict[str, Any]; status: str = "draft"` — `async def create_workflow(payload: WorkflowCreate, org_id: str = Depends(require_org_id)) -> WorkflowResponse` — Retorna `{ id, flow_type, status }` | `src/api/routes/agents.py:51-92` (TenantClient + upsert pattern) | BACKEND | Media | 1.5h | Ninguna | → verificar: `POST /api/workflows` con payload válido retorna 201 |
| 5 | Crear `CrewCanvas.tsx` completo | `dashboard/components/builder/CrewCanvas.tsx` | `interface CrewCanvasProps { agents: AgentFormData[]; onExport: (data: CrewData) => void; onRun: (flowType: string) => void }` — ReactFlow con sidebar, drop zone, edges, toolbar (Export + Run + Minimap + Controls) | `dashboard/components/builder/BuilderCanvas.tsx` (dynamic import pattern) | CODE | Alta | 3h | Tareas 1, 2, 3 | → verificar: Canvas renderiza con sidebar de agentes + drop funcional + botones Export/Run |
| 6 | Integrar CrewCanvas en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` (modificación) | Reemplazar `<BuilderCanvas />` por `<CrewCanvas agents={agents} onExport={handleExport} onRun={handleRun} />` — Handlers: `handleExport` llama `POST /api/bundles/export`, `handleRun` guarda agentes + crea template + ejecuta flow | `BuilderLayout.tsx:5,72` (import + render current) | FULLSTACK | Media | 1.5h | Tareas 3, 4, 5 | → verificar: Builder page muestra CrewCanvas funcional con formulario lateral |
| 7 | Serialización crew → bundle-schema JSON | `dashboard/lib/stores/crew-store.ts` (extensión método `serialize`) | `serialize(): ExportBundleRequest` — Mapea AgentNodes → `AgentExportItem[]`, TaskNodes → `definition.steps[]`, edges → `definition.steps[].agent_role` | `ExportBundleRequest` en `bundle_schemas.py:111-116` | FULLSTACK | Media | 1.5h | Tarea 1 | → verificar: Crew con 2 agentes + 3 tareas serializa a JSON válido compatible con bundle-schema-v2 |
| 8 | Validación visual (agentes sin tareas) | `dashboard/components/builder/CrewCanvas.tsx` (extensión) | Nodos AgentNode sin edges de salida → borde `border-yellow-500` + ícono ⚠️ + tooltip "Agent without tasks" | ReactFlow edge validation | CODE | Baja | 0.5h | Tarea 5 | → verificar: Agente sin tareas muestra warning visual |
| 9 | Test unitarios backend (GET /agents, POST /workflows) | `tests/unit/test_crew_endpoints.py` | `test_list_agents_returns_array`, `test_list_agents_filters_by_org`, `test_create_workflow_returns_201`, `test_create_workflow_duplicate_flow_type_409` | `tests/unit/test_bundle_export.py` (pattern) | BACKEND | Baja | 1h | Tareas 3, 4 | → verificar: `uv run pytest tests/unit/test_crew_endpoints.py -v` pasa |
| 10 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 5-8 | → verificar: Criterios §5 [FULLSTACK] y [DX] pasan todos |

**Tiempo total estimado:** 11 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Python preview del crew** — Generador de código Python CrewAI equivalente al grafo visual. Post-MVP.
- **Collaborative canvas** — Múltiples usuarios editando en tiempo real. Requiere WebSocket/Cursor.
- **Undo/Redo** — Zustand middleware `temporal` para historial de cambios en canvas.
- **Canvas templates** — Pre-made crew layouts (Research → Analyst → Writer). Usar `agent_templates` como base.
- **Validación de ciclos** — Detectar ciclos en el grafo antes de ejecutar. Usar `flow_registry.detect_cycles()`.
- **`fap crew validate`** — CLI para validar JSON de crew antes de import/export.
- **Zoom-to-fit button** — Auto-ajustar vista al contenido del canvas.

---

## 🚫 Reglas de Oro — Verificación

- ✅ Análisis basado en código fuente real (25+ elementos verificados)
- ✅ 5 discrepancias detectadas y resueltas con resolución concreta
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥1 herramienta DX propuesta (`fap crew export`)
- ✅ Tareas atómicas: 1 artefacto = 1 tarea = interfaz completa = patrón explícito = verificación inline
- ✅ El implementador no decide nada: todas las firmas, tipos y patrones están especificados