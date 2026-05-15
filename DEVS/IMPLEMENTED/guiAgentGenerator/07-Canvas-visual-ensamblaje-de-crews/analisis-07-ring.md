# 🧠 Análisis Técnico — Paso 07: Canvas visual — ensamblaje de crews

> **Agente:** ring  
> **Fecha:** 2026-05-15  
> **Proyecto:** FluxAgentPro-v2  
> **Fase:** guiAgentGenerator  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | `grep` en `supabase/migrations/` | ✅ | `030_agent_templates.sql:10` |
| 2 | Endpoint `GET /api/tools/available` existe | `src/api/routes/tools.py:46` | ✅ | Implementado, con filtros `source` y `category` |
| 3 | Endpoint `POST /api/bundles/export` existe | `src/api/routes/bundles.py:199` | ✅ | Handler + validación goal/backstory |
| 4 | Endpoint `GET /api/templates` existe | `src/api/routes/templates.py:54` | ✅ | Lista + filtro `?category=`, sin auth |
| 5 | Endpoint `GET /api/templates/{id}` existe | `src/api/routes/templates.py:70` | ✅ | Detalle con `soul_json`, 404 si no existe |
| 6 | Endpoint `GET /flows/available` existe | `src/api/routes/flows.py:76` | ✅ | Lista flows registrados con categorías |
| 7 | Endpoint `GET /flows/hierarchy` existe | `src/api/routes/flows.py:113` | ✅ | Jerarquía + dependencias + validación |
| 8 | Endpoint `POST /flows/{flow_type}/run` existe | `src/api/routes/flows.py:142` | ✅ | Ejecuta flow con `background_tasks` |
| 9 | Endpoint `POST /agents/{role}/run` existe | `src/api/routes/agents.py:251` | ✅ | Ejecuta agente individual, retorna task_id |
| 10 | Tabla `agent_catalog` con RLS | `supabase/migrations/004_agent_catalog.sql` | ✅ | RLS tenant_isolation vía `app.org_id` |
| 11 | Tabla `workflow_templates` existe | `supabase/migrations/006_workflow_templates.sql` | ✅ | Tabla con `definition` JSONB, `flow_type` único |
| 12 | Componente `BuilderCanvas.tsx` existe | `dashboard/components/builder/BuilderCanvas.tsx` | ✅ | **Placeholder vacío** — sin nodos, sin edges |
| 13 | Componente `AgentForm.tsx` existe | `dashboard/components/builder/AgentForm.tsx` | ✅ | 11 campos, react-hook-form + zod |
| 14 | Componente `AgentPlayground.tsx` existe | `dashboard/components/builder/AgentPlayground.tsx` | ✅ | Chat con polling 2s a `GET /tasks/{task_id}` |
| 15 | Componente `TemplatePicker.tsx` existe | `dashboard/components/builder/TemplatePicker.tsx` | ✅ | Grid + búsqueda + filtro categoría |
| 16 | `reactflow` v11 instalado | `dashboard/package.json` | ✅ | No `@xyflow/react` v12 |
| 17 | Router `templates` en `main.py` | `src/api/main.py:113` | ✅ | `app.include_router(templates_router)` |
| 18 | Router `tools` en `main.py` | `src/api/main.py:114` | ✅ | `app.include_router(tools_router)` |
| 19 | Nav sidebar "Builder" | `dashboard/components/nav-main.tsx:50` | ✅ | `{ title: 'Builder', url: '/builder', icon: Wand2 }` |

**Discrepancias encontradas:**

| # | Discrepancia | Severidad | Resolución propuesta |
|---|---|---|---|
| D1 | **`BuilderCanvas.tsx` es placeholder vacío** — ReactFlow sin nodos, sin edges, sin sidebar de arrastre. El plan pide nodos drag-and-drop, conexiones, minimapa y zoom. | **Crítica** | Implementar componentes de nodos, área de drop, sidebar con nodos arrastrables y controles de canvas. |
| D2 | **No existe `CrewCanvas.tsx`** — El plan lo lista como tarea pero no hay archivo. `BuilderCanvas.tsx` sería su equivalente. | Media | Renombrar/expandir `BuilderCanvas.tsx` a `CrewCanvas.tsx` o integrar toda la lógica en `BuilderCanvas.tsx`. |
| D3 | **No existen nodos visuales** (`AgentNode.tsx`, `TaskNode.tsx`, `ToolNode.tsx`) — El plan los lista como tareas pero no hay archivos. | **Crítica** | Crear estos componentes como custom nodes de ReactFlow. |
| D4 | **No existe `sidebar` con nodos arrastrables** — El plan pide una lista de agentes existentes y tareas disponibles en un panel lateral. | **Crítica** | Crear componente Sidebar con lista de agents (de `agent_catalog`) y tasks disponibles. |
| D5 | **No existe botón "Export as Crew"** — El plan pide serializar el grafo a JSON compatible con `bundle-schema-v2.md` + vista previa Python. | Alta | Implementar lógica de serialización del grafo ReactFlow → formato bundle. |
| D6 | **No existe botón "Run Crew"** — El plan pide ejecutar vía `POST /flows/{flow_type}/run`. | Alta | Implementar extracción del grafo → payload flow → POST a endpoint existente. |
| D7 | **El plan dice `POST /flows/{flow_type}/run`** pero para crews generados visualmente no existe un flow_type registrado. Los flows registrados (`architect_flow`, `multi_crew`) son estáticos y codeados. | Media | Decidir si el canvas genera un `workflow_template` nuevo en DB o si la ejecución se delega a otro endpoint. |
| D8 | **`workflow_templates.definition`** almacena el grafo como JSONB. El componente ArchitectFlow ya genera workflows desde NL, pero no hay integración con el canvas visual. | Media | El canvas podría guardar la definición del grafo en `workflow_templates` vía un nuevo endpoint o reutilizar `architect_flow`. |
| D9 | **El plan dice "guarda en `agent_catalog` vía Supabase directo desde frontend" (Paso 04)** pero la corrección D4 ya establece que debe ir por `POST /agents` con TenantClient. Para Paso 07, el plan no especifica endpoint para guardar crews. | Media | Crear endpoint `POST /flows` o `POST /workflow_templates` para persistir la definición del crew desde el canvas. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas involucradas

| Tabla | Relevancia | Operaciones |
|---|---|---|
| `agent_catalog` | Agentes creados que el usuario arrastra al canvas | `SELECT` (catalog + metadata), carga como nodo |
| `agent_metadata` | Display name, avatar, soul_narrative de cada agente | `JOIN` implícito vía `agents.py:157-181` |
| `agent_templates` | Templates del TemplatePicker (ya implementado) | `SELECT *` (público, RLS auth) |
| `workflow_templates` | Guardar definiciones de crews generados en canvas | `INSERT`/`SELECT` (necesita nuevo endpoint) |
| `org_mcp_servers` | Servidores MCP cuyas tools aparecen como nodos Tool | `SELECT` en `tools.py:112-117` |
| `skill_catalog` | Skills disponibles para asociar a nodos Tool | `SELECT` vía `ToolRegistry` |

### Schema gaps detectados

- **`workflow_templates.definition`** ya tiene estructura para steps con `agent_role`, `depends_on`, `requires_approval` — es compatible con lo que el canvas necesita serializar.
- **No existe una tabla `crew_definitions`** ni `canvas_state` — El estado del canvas se puede persistir como `workflow_templates.definition` (JSONB) reutilizando el schema existente.
- **`agent_catalog.allowed_tools`** es `TEXT[]` — suficiente para mostrar en el nodo del agente qué tools tiene asignadas.
- **`workflow_templates.definition`** soporta el grafo: `steps[]` con `agent_role` y `depends_on` son exactamente edges y nodes del canvas.

### Relaciones

```
agent_catalog (org_id, role, soul_json, allowed_tools, max_iter)
    ↓ agent_role
workflow_templates.definition.steps[].agent_role
    ↓ depends_on[]
workflow_templates.definition.steps[] (edges entre steps)
```

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes a crear (el plan los lista pero NO existen)

| Archivo | Responsabilidad | Patrón a seguir |
|---|---|---|
| `dashboard/components/builder/nodes/AgentNode.tsx` | Nodo visual que muestra `role` + `tools` asignadas | Patrón custom node de ReactFlow v11. Similar a `MessageBubble` en estructura (componente funcional con props tipadas). |
| `dashboard/components/builder/nodes/TaskNode.tsx` | Nodo visual que muestra `description` + `expected_output` | Mismo patrón que `AgentNode` pero sin datos reales aún (tasks son conceptuales en el canvas). |
| `dashboard/components/builder/nodes/ToolNode.tsx` | Nodo visual para herramientas (local/MCP) | Mismo patrón. Datos vienen de `GET /api/tools/available`. |
| `dashboard/components/builder/CrewCanvas.tsx` | Canvas completo con sidebar, drop area, conexiones, controles | Reemplazar/expandir `BuilderCanvas.tsx`. Seguir el layout de `BuilderLayout.tsx` (split 60/40). |

### Archivos a modificar

| Archivo | Cambio necesario |
|---|---|
| `dashboard/components/builder/BuilderCanvas.tsx` | Convertir de placeholder a canvas funcional con ReactFlow + sidebar. O bien, `CrewCanvas.tsx` reemplaza a `BuilderCanvas.tsx`. |
| `dashboard/components/builder/BuilderLayout.tsx` | Integrar `CrewCanvas` (o `BuilderCanvas` actualizado) en el layout. Actualmente renderiza `<BuilderCanvas />` sin props. |
| `dashboard/components/nav-main.tsx` | Ya tiene entrada "Builder" en `defaultNavItems[5]` (línea 50). **No necesita cambios.** |
| `src/api/routes/workflow_templates.py` | **Nuevo archivo** — Endpoint `POST /api/workflow_templates` para persistir la definición del crew desde el canvas. Análogo a `POST /agents` pero para grafo de flujo. |
| `src/api/main.py` | Registrar nuevo router `workflow_templates_router` (si se crea nuevo archivo de rutas). |

### Patrones de código a replicar

**1. Custom Node en ReactFlow v11:**
```tsx
// Patrón: reactflow v11 — custom node via nodeTypes
// Referencia: BuilderCanvas.tsx ya importa ReactFlow dinámicamente
const nodeTypes = {
  agentNode: AgentNode,
  taskNode: TaskNode,
  toolNode: ToolNode,
};
// En ReactFlow: <ReactFlow nodeTypes={nodeTypes} nodes={nodes} edges={edges} />
```

**2. Data fetching (useQuery):**
```tsx
// Patrón de AgentForm.tsx:124-128
const { data: toolsResponse, isLoading } = useQuery({
  queryKey: ['tools-available', orgId],
  queryFn: () => api.get('/api/tools/available'),
  enabled: !!orgId,
});
```

**3. Serialización de grafo a JSON bundle:**
```ts
// Patrón de export_service.py:42-50 — mapear objetos a dict
// Patrón de bundle_schemas.py:102-108 — AgentExportItem
// El canvas debe serializar a formato compatible con BundleManifest
```

**4. Auth en llamadas API:**
```ts
// Patrón de api.ts:19-23 — headers con Bearer + X-Org-ID
// fapFetch ya maneja session y org_id automáticamente
```

### Imports esperados

| Archivo | Imports |
|---|---|
| `AgentNode.tsx` | `reactflow` NodeComponent API, `LucideIcon` (Bot), tipos de `AgentFormData` |
| `TaskNode.tsx` | `reactflow` NodeComponent API, `LucideIcon` (ClipboardList) |
| `ToolNode.tsx` | `reactflow` NodeComponent API, `LucideIcon` (Wrench), datos de `ToolInfo` |
| `CrewCanvas.tsx` | `reactflow` (ReactFlow, Background, Controls, MiniMap, addEdge, useNodesState, useEdgesState), `useQuery`, `api`, `useCurrentOrg` |
| `workflow_templates.py` | `APIRouter`, `Depends`, `BaseModel`, `get_service_client`/`get_tenant_client`, `require_org_id` |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes relevantes para Paso 07

| Endpoint | Método | Archivo | Uso en Paso 07 |
|---|---|---|---|
| `GET /api/tools/available` | GET | `src/api/routes/tools.py:46` | Cargar ToolNodes en sidebar |
| `GET /api/templates` | GET | `src/api/routes/templates.py:54` | Cargar templates en TemplatePicker |
| `GET /api/templates/{id}` | GET | `src/api/routes/templates.py:70` | Detalle de template (soul_json) |
| `GET /flows/available` | GET | `src/api/routes/flows.py:76` | Listar flows registrados |
| `GET /flows/hierarchy` | GET | `src/api/routes/flows.py:113` | Obtener dependencias entre flows |
| `POST /flows/{flow_type}/run` | POST | `src/api/routes/flows.py:142` | Ejecutar un flow existente |
| `POST /agents/{role}/run` | POST | `src/api/routes/agents.py:251` | Ejecutar un agente individual |
| `POST /agents` | POST | `src/api/routes/agents.py:51` | Crear/upsert agente |

### Endpoints que FALTAN para completar Paso 07

| Endpoint | Necesario | Justificación |
|---|---|---|
| `POST /api/workflow_templates` | **Sí** | Persistir la definición del crew generado en el canvas (grafo serializado como `definition` JSONB en tabla `workflow_templates`). Sin esto, el canvas es solo visual y no persistente. |
| `GET /api/workflow_templates` | **Recomendado** | Listar crews guardados previamente para cargarlos en el canvas. |
| `POST /flows/{flow_type}/run` con `definition` en body | **Incertidumbre** | Actualmente el endpoint `run_flow` solo acepta `input_data` y `callback_url`. Para ejecutar un crew generado visualmente, podría necesitarse enviar la `definition` inline o que el flow_type apunte a un `DynamicWorkflow` cargado desde DB. |

### Contratos de endpoints existentes (verificados)

**`POST /flows/{flow_type}/run`** — `src/api/routes/flows.py:142-186`:
```
Request:  { input_data: Dict, callback_url?: str }
Response: { task_id: str, correlation_id: str, status: str }
Headers:  X-Org-ID (require_org_id)
```

**`POST /agents/{role}/run`** — `src/api/routes/agents.py:251-320`:
```
Request:  { input_data: { message: str } }
Response: { task_id: str, status: str }
Auth:     verify_org_membership (JWT + membership)
```

### Servicio de ejecución de flows

`Execute_flow_instance` en `src/api/routes/webhooks.py` (referenciado en `flows.py:174-180`) maneja la ejecución asíncrona de flows. `BaseFlow` en `src/flows/base_flow.py` define el lifecycle: `validate_input → create_task_record → start → _run_crew`.

`DynamicWorkflow` en `src/flows/dynamic_flow.py` permite instanciar flows desde JSON almacenado en `workflow_templates.definition`. Esto es la clave: el canvas puede guardar la definición y luego ejecutarla como un `DynamicWorkflow`.

---

## 4️⃣ Análisis Fullstack + DX (ETAPA 4)

### Flujo completo esperado (end-to-end)

```
[Sidebar: nodos disponibles]
    ↓ drag & drop
[Canvas: área de drop]
    ↓ conexiones (edges)
[Grafo: agent → task → agent]
    ↓ "Export as Crew"
[Serialización → JSON compatible con bundle-schema-v2.md]
    ↓ POST /api/workflow_templates (nuevo endpoint)
[Persistencia en workflow_templates.definition]
    ↓ "Run Crew"
[POST /flows/{flow_type}/run con definition]
    ↓ DynamicWorkflow carga definition desde DB
[Ejecución asíncrona → task_id → polling GET /tasks/{task_id}]
    ↓ resultado
[AgentPlayground muestra resultado]
```

### Gaps y fricciones detectados

| # | Gap | Impacto | Resolución |
|---|---|---|---|
| G1 | **No hay forma de persistir el grafo del canvas** | El usuario arma un crew, cierra la pestaña y lo pierde | Crear `POST /api/workflow_templates` y cargar en `workflow_templates.definition` |
| G2 | **`BuilderCanvas.tsx` no tiene funcionalidad de arrastre** | El Paso 07 del plan es inutilizable hoy | Implementar `useNodesState`, `useEdgesState`, `onConnect`, `nodeTypes` de ReactFlow v11 |
| G3 | **No existe `onConnect` handler** | No se pueden crear edges entre nodos | Implementar en `CrewCanvas.tsx` con `addEdge` de ReactFlow |
| G4 | **El plan dice "Export genera código Python equivalente (vista previa)"** | Esto requiere generar código Python a partir del grafo, que es un generador de código completo | Posible implementación: mapear grafo a estructura `BaseFlow` con `@register_flow`. Referencia: `architect_flow.py` genera `WorkflowDefinition`. |
| G5 | **AgentPlayground usa `role` como string para URL** | Para ejecutar un crew (múltiples agents), se necesita un `flow_type`, no un `role` | El botón "Run Crew" debe navegar a nivel flow, no agent. Usar `POST /flows/{flow_type}/run` donde `flow_type` es el nombre del crew guardado. |
| G6 | **No hay botón "Save Draft" en el canvas** | El usuario no puede guardar progreso parcial | Agregar botón que haga `POST /api/workflow_templates` con `status: 'draft'` |
| G7 | **Mini-mapa y zoom controls** | El plan los pide explícitamente | ReactFlow v11 ya incluye `<MiniMap />` y `<Controls />` — ya están importados en `BuilderCanvas.tsx` (línea 9) pero no renderizados dentro del componente dinámico. |

### Prueba de re-importación (round-trip)

El plan Paso 07 dice: "Export genera JSON compatible con `bundle-schema-v2.md`". Verificar que:
- `BundleManifest` en `src/services/bundle_schemas.py:22-42` soporta `bundle_info` + `hashes`.
- `BundleManager.create_bundle()` en `src/services/bundle_manager.py:197-245` genera ZIP con `agents/*.json` + `flows/*.json` + `skills/*.py`.
- `ImportService` en `src/services/import_service.py` ya procesa bundles y crea agents/flows en DB.
- **Round-trip funcional:** La exportación del canvas debería generar un bundle que `POST /api/bundles/import` pueda importar.

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap canvas export`

```
### Herramienta Propuesta: fap canvas export
- **Qué automatiza:** Serializa el grafo del canvas ReactFlow a un bundle ZIP 
  compatible con bundle-schema-v2.md, sin necesidad de abrir el diálogo de exportación 
  en el frontend.
- **Tipo:** CLI command (Typer sub-app)
- **Cómo se usa:** 
  fap canvas export --workflow-id <uuid> --output my-crew.zip --org-id <uuid>
  
  # O desde JSON local:
  fap canvas export --definition-file crew.json --output my-crew.zip
- **Impacto para el usuario final:** 
  El desarrollador puede exportar un crew diseñado en el canvas directamente 
  desde la terminal, sin interactuar con la UI. Útil para CI/CD, automatización 
  de despliegue de crews, y scripting de pruebas.
- **Prioridad:** Tarea 0 — implementar después del endpoint de persistencia 
  (POST /api/workflow_templates), antes que la UI de exportación.
```

#### Herramienta Propuesta: `fap canvas scaffold`

```
### Herramienta Propuesta: fap canvas scaffold
- **Qué automatiza:** Genera un archivo JSON inicial de definición de crew 
  (con un AgentNode + un Task + conexión) para arrancar rápido en el canvas.
- **Tipo:** CLI command (Typer sub-app)
- **Cómo se usa:** 
  fap canvas scaffold --name "my-crew" --agents analyst,reviewer \
    --output crew-template.json
  
  Esto genera un JSON con la estructura de steps + agents compatible 
  con workflow_templates.definition y con el formato de BundleManifest.
- **Impacto para el usuario final:** 
  Elimina la necesidad de armar el grafo desde cero. El usuario genera 
  el scaffold, lo edita si necesita, y luego lo importa en el canvas.
- **Prioridad:** Media — complementa el scaffold de agent individual 
  ya existente (`fap agent create`).
```

---

## 5️⃣ Criterios de Aceptación

Lista binaria verificable para Paso 07:

```
✅ [DATA] Tabla workflow_templates existe con columna definition JSONB (mig 006)
✅ [DATA] Tabla agent_catalog con datos de prueba (seed + tests)
✅ [DATA] Tabla agent_templates con 8 system templates (mig 030 + seed)
✅ [CODE] AgentNode.tsx renderiza role + lista de tools asignadas
✅ [CODE] TaskNode.tsx renderiza description + expected_output
✅ [CODE] ToolNode.tsx renderiza nombre + categoría + source badge
✅ [CODE] CrewCanvas.tsx tiene ReactFlow con nodeTypes, onConnect, sidebar draggable
✅ [CODE] Sidebar muestra agents de agent_catalog + tasks disponibles
✅ [CODE] Los nodos se pueden arrastrar desde sidebar al canvas
✅ [CODE] Las conexiones (edges) se pueden crear entre nodos
✅ [CODE] MiniMap y Controls son visibles en el canvas
✅ [CODE] Zoom in/out funciona (Controls de ReactFlow)
✅ [BACKEND] POST /api/workflow_templates persiste definición del grafo
✅ [BACKEND] POST /api/workflow_templates valida payload (min 1 agent, al menos 1 edge)
✅ [BACKEND] GET /api/workflow_templates lista crews guardados
✅ [BACKEND] POST /flows/{flow_type}/run ejecuta crew guardado (DynamicWorkflow)
✅ [FULLSTACK] "Export as Crew" genera JSON compatible con bundle-schema-v2.md 
✅ [FULLSTACK] Vista previa de Python generada desde el grafo
✅ [FULLSTACK] "Run Crew" ejecuta vía POST /flows/{flow_type}/run y muestra resultado en AgentPlayground
✅ [FULLSTACK] Guardar crew persiste el grafo y permite recargarlo
✅ [DX] `fap canvas export` ejecuta sin errores y genera ZIP válido
✅ [DX] `fap canvas scaffold` genera JSON válido compatible con el canvas
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ReactFlow v11 tiene API diferente a v12; la migración futura puede romper nodos custom | Media | `reactflow` v11 en `package.json`; v12 cambió API drásticamente | Documentar versión pinneada. Usar `import('reactflow')` dynamic como ya se hace en `BuilderCanvas.tsx`. Plan de migración post-MVP. |
| La serialización del grafo a bundle no es trivial — el formato de `workflow_templates.definition` difiere del formato `agents/*` + `flows/*` de bundles | Alta | `workflow_templates.definition` usa schema de steps con `agent_role`, mientras bundles usan `AgentExportItem` con `role` + `soul_json` | Crear mapper explícito `GrafoCanvas → BundleManifest` + `GrafoCanvas → WorkflowDefinition`. Tests unitarios para el mapper. |
| Ejecutar un crew dinámico requiere que `flow_type` esté registrado | Alta | `run_flow` en `flows.py:153` verifica `flow_registry.has(flow_type)`. Un crew nuevo del canvas no estará en el registry. | Usar `DynamicWorkflow` — `FlowRegistry._load_from_db()` ya soporta cargar desde `workflow_templates` si no está en memoria. Verificar que `POST /flows/{flow_type}/run` con un flow_type de workflow_template funciona. |
| El sidebar de nodos necesita cargar todos los agents de la org — potencialmente muchos | Media | `agent_catalog` puede tener decenas/hundreds de agents por org | Paginación o búsqueda en el sidebar. Caching local con React Query. |
| Sin validación visual de ciclos en el grafo | Media | El usuario podría crear dependencias circulares entre nodos | Implementar validación de DAG antes de export/ejecutar. `FlowRegistry.detect_cycles()` existe pero opera en flows registrados, no en grafo del canvas. |
| La eliminación de `BuilderCanvas.tsx` como placeholder puede romper imports existentes | Baja | Otros componentes importan `BuilderCanvas` | Verificar todos los imports de `BuilderCanvas` antes de refactorizar. Si `CrewCanvas` es nuevo nombre, actualizar imports en `BuilderLayout.tsx`. |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica — OBLIGATORIAS:**
> - Una tarea = un artefacto
> - Interfaz completa en cada tarea
> - Patrón de referencia explícito
> - Verificación inline

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: `fap canvas scaffold` CLI** | `src/cli/commands/canvas_scaffold.py` | `def scaffold(name: str, agents: list[str], output: str)` → archivo JSON | `src/cli/commands/agent_create.py` — mismo patrón Typer + Rich table | DX | Media | 2h | Ninguna | → verificar: `fap canvas scaffold --name test --agents analyst --output /tmp/test.json` genera JSON válido |
| 1 | **Crear nodo AgentNode** | `dashboard/components/builder/nodes/AgentNode.tsx` | `(props: NodeProps & { data: { role: string; tools: string[]; llmProvider?: string } }) => JSX.Element` | ReactFlow v11 custom node — `Handle` para conexiones, estilo shadcn Card | CODE | Media | 2h | Ninguna | → verificar: nodo renderiza en Storybook/canvas con datos mock |
| 2 | **Crear nodo TaskNode** | `dashboard/components/builder/nodes/TaskNode.tsx` | `(props: NodeProps & { data: { description: string; expectedOutput: string } }) => JSX.Element` | Mismo patrón que AgentNode, estilo diferenciado (borde dashed) | CODE | Media | 1.5h | Ninguna | → verificar: renderiza con datos mock |
| 3 | **Crear nodo ToolNode** | `dashboard/components/builder/nodes/ToolNode.tsx` | `(props: NodeProps & { data: { name: string; source: 'local' \| 'mcp'; category: string } }) => JSX.Element` | Mismo patrón, badge de source (local=blue, mcp=green) | CODE | Baja | 1h | Ninguna | → verificar: renderiza con datos mock |
| 4 | **Crear Sidebar nodos** | `dashboard/components/builder/CanvasSidebar.tsx` | `({ agents: AgentInfo[]; tools: ToolInfo[]; onDragNode: (type: string, data: any) => void }) => JSX.Element` | Custom drag con `useDrag` HTML5 o ReactFlow `react-flow-renderer`. Lista con búsqueda. | CODE | Media | 3h | Tarea 1-3 | → verificar: arrastrar nodo desde sidebar al canvas crea nodo nuevo |
| 5 | **Convertir BuilderCanvas → CrewCanvas** | `dashboard/components/builder/BuilderCanvas.tsx` → `CrewCanvas.tsx` | `({ workflowId?: string; onSave: (definition: WorkflowDefinition) => void }) => JSX.Element` | ReactFlow v11: `useNodesState`, `useEdgesState`, `onConnect`, `addEdge`, `MiniMap`, `Controls`. Ref: `BuilderCanvas.tsx` existente (placeholder). | CODE | Alta | 5h | Tareas 1-4 | → verificar: canvas renderiza, drag funciona, edges funcionan, minimapa visible, zoom funciona |
| 6 | **Crear endpoint `POST /api/workflow_templates`** | `src/api/routes/workflow_templates.py` | Input: `{ name: str, definition: dict, status?: 'draft'\|'active' }` → Output: `{ id: str, flow_type: str }`. Auth: `require_org_id`. | `src/api/routes/agents.py:51-92` — mismo patrón handler + service. Persistir en tabla `workflow_templates` existente. | BACKEND | Media | 2h | Ninguna | → verificar: `POST /api/workflow_templates` retorna 201 con id |
| 7 | **Crear endpoint `GET /api/workflow_templates`** | `src/api/routes/workflow_templates.py` (añadir) | Query params: `?status=draft` → Output: `{ templates: [...] }`. Auth: `require_org_id`. | `src/api/routes/templates.py:54-67` — sin auth extra, RLS basta. | BACKEND | Baja | 1h | Tarea 6 | → verificar: GET retorna lista de workflow_templates de la org |
| 8 | **Integrar CrewCanvas en BuilderLayout** | `dashboard/components/builder/BuilderLayout.tsx` | Reemplazar `<BuilderCanvas />` por `<CrewCanvas />` con props de callbacks | `BuilderLayout.tsx` actual — reemplazar import y props | CODE | Baja | 0.5h | Tarea 5 | → verificar: canvas funcional aparece en ruta /builder |
| 9 | **Botón "Export as Crew" en CrewCanvas** | `dashboard/components/builder/CrewCanvas.tsx` (feature) | Serializa nodos+edges → `WorkflowDefinition` JSON + genera ZIP vía `POST /api/bundles/export` o client-side | `src/services/export_service.py` — mapear `ExportBundleRequest`. `src/services/bundle_schemas.py` — `AgentExportItem`, `BundleManifest`. | FULLSTACK | Alta | 4h | Tareas 1-5, backend | → verificar: export genera JSON compatible con bundle-schema-v2.md (validar con `bundle_validator.py`) |
| 10 | **Vista previa de código Python** | `dashboard/components/builder/CrewCanvas.tsx` (feature) + `src/utils/crew_to_python.py` (nuevo) | `def generate_python(workflow_def: dict) -> str` → código Python ejecutable | `scripts/seed_system_bundles.py` — cómo se genera código Python para flows | FULLSTACK | Alta | 3h | Tarea 9 | → verificar: output es Python sintácticamente válido que usa `BaseFlow` + `@register_flow` |
| 11 | **Botón "Run Crew" en CrewCanvas** | `dashboard/components/builder/CrewCanvas.tsx` (feature) | POST a `/flows/{flow_type}/run` o `/flows/dynamic/run` con definition en body. Polling a `GET /tasks/{task_id}` | `AgentPlayground.tsx:66-101` — mismo patrón `useMutation` + `useQuery` polling. `src/api/routes/flows.py:142` — endpoint existente. | FULLSTACK | Alta | 3h | Tareas 5, 9, backend | → verificar: ejecuta crew, polling muestra resultado en AgentPlayground |
| 12 | **Botón "Save Draft" en CrewCanvas** | `dashboard/components/builder/CrewCanvas.tsx` (feature) | PUT a `/api/workflow_templates/{id}` con definition actualizada | `src/api/routes/workflow_templates.py` (extensión tarea 6) | FULLSTACK | Media | 1.5h | Tareas 5, 6, 8 | → verificar: recarga página y el grafo persiste |
| 13 | **Validación de DAG (sin ciclos)** | `dashboard/components/builder/CrewCanvas.tsx` (feature) | Validar en `onConnect` que no cree ciclo. Mostrar warning visual. | `src/flows/registry.py:152-191` — `detect_cycles()` como referencia algorítmica | CODE | Media | 2h | Tarea 5 | → verificar: intentar crear ciclo muestra error visual |
| 14 | **Tests unitarios: serialización grafo → bundle** | `tests/unit/test_canvas_export.py` (nuevo) | Tests para mapper de grafo → bundle JSON | `tests/unit/test_bundle_export.py` — patrones de test unitario Pydantic | CODE | Media | 2h | Tarea 9 | → verificar: `uv run pytest tests/unit/test_canvas_export.py -v` pasa |
| 15 | **DX: `fap canvas export` CLI** | `src/cli/commands/canvas_export.py` (nuevo) + registro en `src/cli/main.py` | `fap canvas export --workflow-id <id> --output <file.zip>` | `src/cli/commands/bundle_export.py` — mismo patrón Typer + ExportService | DX | Media | 2h | Tareas 6, 9 | → verificar: `fap canvas export --help` funciona, exporta ZIP válido |

**Tiempo total estimado:** ~34 horas

### Dependencias críticas

```
Tarea 0 (scaffold CLI) ──────────────────────────┐
Tareas 1-3 (nodos) ──────────┐                   │
Tarea 4 (sidebar) ───────────┼── Tarea 5 (canvas) ┼── Tarea 8 (integración)
Tarea 6 (POST workflow) ─────┼────────────────────┼── Tarea 9 (export)
                              │                    │        │
                              └── Tarea 7 (GET)    └── 12 (save) ── 11 (run)
                                                                │
Tarea 10 (Python preview) ─── 9                        13 (DAG validation)
Tarea 14 (tests) ──────────── 9
Tarea 15 (CLI export) ─────── 6 + 9
```

---

## 📊 Resumen de Calidad

| Métrica | Estado |
|---|---|
| `proyecto-config.json` leído | ✅ |
| Elementos verificados (§0) | 19/19 |
| Discrepancias detectadas | 9 (3 críticas, 3 altas, 3 medias) |
| Secciones completadas | 8/8 (0-7) |
| Etapas cubiertas | 4/4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 20 criterios verificables |
| Riesgos identificados | 6 (técnico, integración, futuro) |
| Tareas atómicas (1 artefacto por tarea) | 15/15 = 100% |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia explícito | 100% |
| Verificación inline por tarea | 100% |
| Propuesta DX/Tooling | 2 herramientas concretas |

---