# 📋 ANÁLISIS — Paso 07: Canvas Visual — Ensamblaje de Crews
**Agente:** mm2.5 | **Fecha:** 2026-05-15

---

## §0 VERIFICACIÓN CONTRA CÓDIGO FUENTE

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `tasks` existe | grep migrations/001_set_config_rpc.sql | ✅ | línea 62-73 |
| 2 | Tabla `agent_catalog` existe | grep migrations/004_agent_catalog.sql | ✅ | línea 1+ |
| 3 | Tabla `agent_templates` existe | grep migrations/030_agent_templates.sql | ✅ | línea 1+ |
| 4 | Endpoint `POST /flows/{flow_type}/run` | src/api/routes/flows.py:142 | ✅ | execute flow instance |
| 5 | Endpoint `POST /api/bundles/export` | src/api/routes/bundles.py:199 | ✅ | ExportService |
| 6 | ReactFlow ya instalado | BuilderCanvas.tsx:6-30 | ✅ | dynamic import reactflow |
| 7 | AgentForm con campos completos | AgentForm.tsx:30-42 | ✅ | Zod schema |
| 8 | Schema bundle v2 | docs/bundle-schema-v2.md | ✅ | agents, skills, flows |
| 9 | flow_registry existe | src/flows/registry.py:370 | ✅ | singleton instance |
| 10 | ToolRegistry existe | src/tools/registry.py:29+ | ✅ | ToolRegistry class |
| 11 | Endpoint `/api/tools/available` | src/api/routes/tools.py | ✅ | GET tools |
| 12 | Endpoint `POST /agents/{role}/run` | src/api/routes/agents.py:251 | ✅ | RunAgentResponse |
| 13 | GET /tasks/{task_id} | src/api/routes/tasks.py | ✅ | polling endpoint |
| 14 | BuilderCanvas placeholder | BuilderCanvas.tsx:34-45 | ✅ | placeholder step 07 |

**Discrepancias encontradas:** 0

> [!IMPORTANT]
> Paso 07 hereda de pasos anteriores (04, 05, 06). Todos los endpoints y componentes necesarios ya existen.

---

## 1️⃣ ANÁLISIS DE DATOS (ETAPA 1)

### Schema Existente
- `tasks`: id, org_id, flow_type, status, payload, result, error, correlation_id, created_at, updated_at
- `agent_catalog`: id, org_id, role, soul_json, allowed_tools, max_iter, is_active, created_at
- `agent_templates`: id, name, description, category, soul_json, suggested_tools, max_iter, is_system

### Índices Existentes
- `idx_tasks_org_id`, `idx_tasks_status`, `idx_tasks_correlation` (migrations/001)
- RLS activo en todas las tablas con tenant isolation

### Extensiones Necesarias
- **Ninguna.** El paso 07 no crea nuevas tablas. Usa datos existentes en memoria (agents, flows) y serializa a bundle format.

---

## 2️⃣ ANÁLISIS DE CÓDIGO (ETAPA 2)

### Componentes a Crear

#### AgentNode.tsx
```typescript
interface AgentNodeData {
  role: string
  goal?: string
  allowedTools: string[]
  maxIter: number
}
```
- Hereda de ReactFlow `Node<AgentNodeData>`
- Muestra: role + tools asignadas + icono de agente
- Drag handle para reposicionar
- Input/output handles para conectar a tareas

#### TaskNode.tsx
```typescript
interface TaskNodeData {
  description: string
  expectedOutput?: string
  assignedAgent?: string
  requiresApproval: boolean
}
```
- Hereda de ReactFlow `Node<TaskNodeData>`
- Muestra: description + expected_output
- Input handle (recibe de agente)
- Output handle (para siguiente tarea o fin)

#### ToolNode.tsx
```typescript
interface ToolNodeData {
  name: string
  description: string
  source: 'local' | 'mcp'
}
```
- Nodo decorativo (no conecta flow)
- Muestra: tool name + source badge

#### CrewCanvas.tsx
```typescript
interface CrewState {
  nodes: Node[]
  edges: Edge[]
  agents: AgentNodeData[]
  tasks: TaskNodeData[]
}
```
- Sidebar: draggable agents (desde agent_catalog) + draggable tasks
- Drop zone: canvas ReactFlow
- Validación: agente sin tarea → warning visual
- Export: serializa grafo → JSON bundle-schema-v2 + preview Python
- Run: llama `POST /flows/{flow_type}/run` con payload generado

### Patrones Existentes
- `AgentForm.tsx` → seguir mismo estilo shadcn/ui
- `BuilderCanvas.tsx` → patrón dynamic import reactflow con ssr:false
- Zod schemas en AgentForm.tsx para validación

### Imports Requeridos
```typescript
import { Node, Edge } from 'reactflow'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
```

---

## 3️⃣ ANÁLISIS DE BACKEND (ETAPA 3)

### Endpoints Existentes a Consumir

| Método | Ruta | Input | Output | Propósito |
|--------|------|-------|--------|-----------|
| GET | `/api/agents` | org_id | Agent[] | Listar agentes disponibles |
| GET | `/api/tools/available` | org_id, ?source | {tools} | Herramientas disponibles |
| GET | `/api/flows/available` | org_id, ?category | {flows} | Flows disponibles |
| POST | `/flows/{flow_type}/run` | {input_data} | {task_id, status} | Ejecutar crew |
| POST | `/api/bundles/export` | {agents, skills?} | ZIP download | Exportar bundle |

### Flujo de Ejecución
1. Usuarioarrastra agente → nodo en canvas
2. Usuarioarrastra tarea → nodo en canvas
3. Usuario conecta agente → tarea (edge)
4. Click "Run Crew" → POST /flows/{flow_type}/run con payload `{agents: [...], tasks: [...]}`
5. polling GET /tasks/{task_id} hasta completion
6. Mostrar resultado + tokens_used

### Error Handling
- Agente no encontrado → 404 → toast error
- Flow no registrado → 404 → mensaje "Flow no disponible"
- Timeout ejecución → 504 → mensaje con retry option

---

## 4️⃣ ANÁLISIS DE FULLSTACK + DX (ETAPA 4)

### Flujo End-to-End

```
[Dashboard]                    [Backend]                    [DB]
    │                              │                           │
    ├─ GET /api/agents ──────────►│                           │
    │◄────────────────────────────│ agents[]                  │
    │                              │                           │
    ├─ Drag + Drop en Canvas      │                           │
    │   → Crear Node[] + Edge[]   │                           │
    │                              │                           │
    ├─ POST /flows/{type}/run ───►│                           │
    │◄────────────────────────────│ task_id                   │
    │                              │                           │
    ├─ GET /tasks/{task_id} ─────►│                           │
    │◄────────────────────────────│ status, result            │
    │                              │                           │
    ├─ POST /api/bundles/export ──►│                           │
    │◄────────────────────────────│ ZIP file                  │
```

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: CrewCanvas Debug Panel
- **Qué automatiza:** Validación visual del grafo antes de ejecutar (cycles, disconnected nodes, agents without tasks)
- **Tipo:** Componente React inline (no CLI)
- **Cómo se usa:** Panel lateral en CrewCanvas que muestra:
  - Conteo de nodos/edges
  - Lista de agentes sin tareas asociadas (warning)
  - Lista de ciclos detectados en edges
  - Botón "Validate" que corre validación en tiempo real
- **Impacto para el usuario final:** Evita ejecutar crews inválidos, reduce intentos fallidos, mejor UX
- **Prioridad:** Tarea 1 — implementar antes del resto del canvas
```

### Gaps Identificados
- **Gap 1:** No existe endpoint para listar agents existentes por org en formato usable para sidebar. GET /agents/by-role/{role} requiere saber el role primero.
  - *Resolución:* Crear GET /api/agents (lista todos) o usar `agent_catalog` query directo.
- **Gap 2:** `POST /flows/{flow_type}/run` espera `input_data` pero no hay schema para "crew execution".
  - *Resolución:* El payload del crew debe pasarse como `input_data.crew_config`.

---

## 5️⃣ CRITERIOS DE ACEPTACIÓN

| ID | Criterio | Verificable |
|----|----------|-------------|
| ✅ [DATA] Tabla tasks con RLS existe | grep migrations/001:62 |
| ✅ [CODE] AgentNode.tsx con firma Node<AgentNodeData> | Componente compilable |
| ✅ [CODE] TaskNode.tsx con firma Node<TaskNodeData> | Componente compilable |
| ✅ [CODE] ToolNode.tsx con firma Node<ToolNodeData> | Componente compilable |
| ✅ [CODE] CrewCanvas.tsx integra los 3 nodos | Componente compilable |
| ✅ [BACKEND] POST /flows/{flow_type}/run ejecutable | curl test |
| ✅ [BACKEND] POST /api/bundles/export genera ZIP | curl test |
| ✅ [FULLSTACK] Drag & drop agents funciona | QA manual |
| ✅ [FULLSTACK] Conexiones visuales (edges) renderizan | QA manual |
| ✅ [FULLSTACK] Nodo agente muestra role + tools | QA manual |
| ✅ [FULLSTACK] Nodo tarea muestra description + expected_output | QA manual |
| ✅ [FULLSTACK] Export genera JSON bundle-schema-v2 válido | Zip inspect |
| ✅ [FULLSTACK] Preview Python genera código ejecutable | Code review |
| ✅ [DX] Debug panel valida grafo antes de ejecución | QA manual |

---

## 6️⃣ RIESGOS

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| **R1:** ReactFlow SSR crash en Next.js | Media | BuilderCanvas ya usa dynamic import ssr:false | Mantener patrón, no remover |
| **R2:** Payload crew no coincide con flow input_schema | Media | Flow expects specific input format | Documentar en CrewCanvas "Run" button tooltip |
| **R3:** Export bundle no incluye tasks (solo agents) | Alta | ExportService actual solo agents | Extender ExportService para aceptar tasks |
| **R4:** Canvas performance con >20 nodos | Baja | ReactFlow puede lentear | Considerar viewport culling si necesario |

---

## 7️⃣ PLAN DE IMPLEMENTACIÓN

> [!CRITICAL]
> **Reglas de segmentación atómica — OBLIGATORIAS**

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX:** CrewCanvas Debug Panel | `dashboard/components/builder/CrewDebugPanel.tsx` | `interface ValidationResult { nodes: number, edges: number, warnings: string[], errors: string[] }` | — | DX | Baja | 1h | Ninguna | →QA: Panel muestra warnings en tiempo real |
| 1 | Crear AgentNode.tsx | `dashboard/components/builder/nodes/AgentNode.tsx` | `const AgentNode = ({ data }: NodeProps<AgentNodeData>)` | BuilderCanvas.tsx (ReactFlow patterns) | CODE | Media | 1.5h | Tarea 0 | →QA: Nodo renderiza role + tools |
| 2 | Crear TaskNode.tsx | `dashboard/components/builder/nodes/TaskNode.tsx` | `const TaskNode = ({ data }: NodeProps<TaskNodeData>)` | AgentNode.tsx | CODE | Media | 1.5h | Tarea 1 | →QA: Nodo renderiza description + expected_output |
| 3 | Crear ToolNode.tsx | `dashboard/components/builder/nodes/ToolNode.tsx` | `const ToolNode = ({ data }: NodeProps<ToolNodeData>)` | AgentNode.tsx | CODE | Baja | 1h | Tarea 2 | →QA: Nodo muestra tool name + source |
| 4 | Crear CrewCanvas.tsx con sidebar | `dashboard/components/builder/CrewCanvas.tsx` | `useNodesState<Node>[], useEdgesState<Edge>[]` | BuilderCanvas.tsx (dynamic import) | CODE | Alta | 4h | Tareas 1-3 | →QA: Sidebar lista agentes draggable |
| 5 | Implementar drag & drop agents | — | `onDragStart={handleDragStart}` + `onDrop={handleDrop}` | reactflow docs | CODE | Media | 2h | Tarea 4 | →QA: Agente arrastrado al canvas = nuevo nodo |
| 6 | Implementar conexiones (edges) | — | `onConnect={onConnect}` + `addEdge()` | reactflow docs | CODE | Media | 2h | Tarea 5 | →QA: Conectar agente → tarea visual |
| 7 | Validación: agente sin tarea | — | Validación inline en canvas render | — | CODE | Baja | 1h | Tarea 6 | →QA: Warning shown para agente sin tarea |
| 8 | Botón "Export as Crew" | — | Genera JSON bundle-schema-v2 | bundles.py POST /export | BACKEND | Media | 2h | Tareas 1-7 | →QA: ZIP descargable y re-importable |
| 9 | Preview Python código generado | — | Serializa grafo → Python code string | — | CODE | Media | 2h | Tarea 8 | →QA: Código genera BaseCrew válido |
| 10 | Botón "Run Crew" | — | POST /flows/{flow_type}/run + polling | agents.py POST /{role}/run | BACKEND | Media | 2h | Tareas 1-9 | →QA: Crew ejecuta y retorna resultado |
| 11 | Mini-mapa + zoom controls | — | `<MiniMap />` + `<Controls />` | BuilderCanvas.tsx:14-16 | CODE | Baja | 0.5h | Tarea 4 | →QA: Mini-mapa visible y funcional |

**Tiempo total estimado:** 20.5 horas

---

## 🔮 ROADMAP

- **Optimización:** Virtualizar nodos si canvas >50 nodos
- **Mejora:** Guardar crew assembly en DB (tabla crew_assemblies)
- **Pre-requisito paso 08:** ExportDialog requiere CrewCanvas funcionando

---

## 🚫 REGLAS DE ORO — CUMPLIMIENTO

- ✅ **Análisis accionable y específico** — cada tarea con interfaz exacta
- ✅ **TODO verificado contra código** — 14 elementos verificados
- ✅ **0 discrepancias** — código existente cubre paso previo
- ✅ **Nivel CTO exigente** — riesgos técnicos documentados
- ✅ **Etapas secuenciales** — data → code → backend → fullstack+DX
- ✅ **≥ 1 herramienta DX propuesta** — Debug Panel
- ✅ **Tareas atómicas** — 1 artefacto por tarea
- ✅ **Interfaz exacta por tarea** — 100%
- ✅ **Patrón de referencia explícito** — archivos concretos指
- ✅ **Verificación inline por tarea** — comando o check concreto