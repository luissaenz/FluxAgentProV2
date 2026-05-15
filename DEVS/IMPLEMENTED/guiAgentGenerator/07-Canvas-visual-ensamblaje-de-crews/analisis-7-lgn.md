# Análisis Técnico — Paso 07: Canvas visual — ensamblaje de crews

**Agente:** lgn  
**Paso:** 7  
**Objetivo:** Implementar canvas ReactFlow con nodos drag-and-drop para ensamblar crews visualmente

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `BuilderCanvas.tsx` existe | ✅ | Sí | `dashboard/components/builder/BuilderCanvas.tsx:6-46` |
| 2 | ReactFlow instalado | ⚠️ | Ingresar en package.json | `dashboard/components/builder/BuilderCanvas.tsx:3` import dynamic reactflow |
| 3 | `agent_catalog` tabla | ✅ | Sí | `supabase/migrations/004_agent_catalog.sql:6-17` |
| 4 | `GET /agents/by-role/{role}` | ✅ | Sí | `src/api/routes/agents.py:104-124` |
| 5 | `POST /agents/{role}/run` | ✅ | Sí | `src/api/routes/agents.py:251-320` |
| 6 | `GET /tasks/{task_id}` | ✅ | Sí | `src/api/routes/tasks.py:69-91` |
| 7 | `POST /flows/{flow_type}/run` | ✅ | Sí | `src/api/routes/flows.py:142-186` |
| 8 | `TemplatePicker` component | ✅ | Sí | `dashboard/components/builder/TemplatePicker.tsx` |
| 9 | `AgentForm` con `allowedTools` | ✅ | Sí | `dashboard/components/builder/AgentForm.tsx:36-42` |
| 10 | `BuilderLayout` integra canvas | ✅ | Sí | `dashboard/components/builder/BuilderLayout.tsx:72` |
| 11 | `PROVIDER_MODELS` constant | ✅ | Sí | `dashboard/lib/constants.ts:20-25` |
| 12 | `bundle-schema-v2.md` formato | ✅ | Sí | `docs/bundle-schema-v2.md` |

**Discrepancias detectadas:**
- `BuilderCanvas.tsx` es placeholder (líneas 13-17: `nodes=[]`, `edges=[]`). Requiere full impl.
- No existe `agent_templates` tabla aún (plan Paso 03, pendiente).
- No hay endpoint `/api/tasks/available` para tareas draggables.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas involucradas:**
- `agent_catalog` (existente): almacena agentes creados
  - Columnas: `id`, `org_id`, `role`, `soul_json`, `allowed_tools`, `max_iter`, `is_active`
  - RLS: `tenant_isolation` (org_id::text = app.org_id())
  - Índice: `idx_agent_catalog_org_role` on (org_id, role) WHERE is_active

**Cambios de schema necesarios:**
- Ningún nuevo esquema para Paso 07 (usa tablas existentes)
- `tasks` tabla usada para polling ejecución crew

**RLS aplicado:**
- `agent_catalog`: lectura/escritura por org_id
- `tasks`: lectura por org_id (implícito vía middleware)

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes a crear:

**1. `AgentNode.tsx` — Nodo visual para agente**
```typescript
interface AgentNodeProps {
  id: string
  role: string
  goal: string
  tools: string[]
  data: { soul_json: Record<string, any> }
}
```
Patrón: Seguir estructura de nodos ReactFlow custom (`dashboard/components/builder/nodes/`)

**2. `TaskNode.tsx` — Nodo visual para tarea**
```typescript
interface TaskNodeProps {
  id: string
  description: string
  expected_output: string
  agent_role?: string
}
```

**3. `ToolNode.tsx` — Nodo visual para herramienta**
```typescript
interface ToolNodeProps {
  id: string
  name: string
  source: 'local' | 'mcp'
}
```

**4. `CrewCanvas.tsx` — Canvas completo**
- Sidebar draggables: agentes de `agent_catalog`, tareas predefinidas
- Estado: `nodes`, `edges` arrays
- Handlers: `onNodesChange`, `onEdgesChange`, `onConnect`
- Validación: agentes sin tareas → warning visual

**Patrones existentes:**
- `BuilderCanvas.tsx`: import dinámico reactflow con SSR false
- `BuilderLayout.tsx`: grid 60%/40% layout
- `AgentForm.tsx`: Zod schema validation

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints disponibles para consumo:

**1. `GET /agents/by-role/{role}`**
- Auth: require_org_id
- Response: agente del catálogo con `soul_json`, `allowed_tools`

**2. `POST /flows/{flow_type}/run`**
- Request: `{ input_data: Dict }`
- Response: `{ task_id, correlation_id, status: "accepted" }`
- Background execution

**3. `GET /tasks/{task_id}`**
- Response: `{ status, result, tokens_used, error }`
- Polling para resultados

### Flujo de datos:
1. Canvas → serializar grafo a JSON bundle-schema-v2
2. Export → `POST /api/bundles/export` (existe en `bundles.py`)
3. Run → `POST /flows/{flow_type}/run` con payload bundle

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

**Flujo end-to-end:**
```
Sidebar (agentes) → Drag → Canvas (ReactFlow) → Connect (edges) → Export → ZIP bundle → Run via flows
```

**DX & Tooling:**
### Herramienta Propuesta: `crew-validator`
- **Qué automatiza:** Validación de integridad del crew antes de exportar (agentes sin conexión, tareas sin agentes asignados)
- **Tipo:** script CLI
- **Cómo se usa:** `python scripts/crew_validator.py --canvas-state <json_file>`
- **Impacto:** Evita errores de exportación, feedback inmediato al usuario

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | [DATA] AgentNode muestra role + tools | Visual inspección |
| 2 | [CODE] CrewCanvas tiene drag-drop funcionando | `data-testid="crew-canvas"` |
| 3 | [BACKEND] Export genera JSON bundle válido | `POST /api/bundles/export` 200 |
| 4 | [FULLSTACK] Run Crew ejecuta vía `POST /flows/{id}/run` | task.status = "completed" |
| 5 | [DX] crew-validator detecta crew inválido | Exit code 1 |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ReactFlow SSR crash | Alta | Canvas en SSR | dynamic import con `ssr: false` |
| Estado canvas inconsistente | Media | Race conditions drag-drop | Immutable updates, useCallback |
| Bundle export incorrecto | Media | Serialización manual | Validar contra bundle-schema-v2 |
| Memoria leak en nodos grandes | Baja | Muchos nodos (>100) | Memoización, react-window |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Verificación |
|---|---|---|---|---|---|---|---|---|
| 0 | DX & Tooling | `scripts/crew_validator.py` | `def validate(canvas_state: dict) -> ValidationResult` | — | DX | Baja | 0.5h | → verificar: `python scripts/crew_validator.py --help` |
| 1 | AgentNode | `dashboard/components/builder/nodes/AgentNode.tsx` | `function AgentNode({ id, data }: NodeProps)` | `BuilderCanvas.tsx` pattern | CODE | Media | 1h | → verificar: renderiza sin errores |
| 2 | TaskNode | `dashboard/components/builder/nodes/TaskNode.tsx` | `function TaskNode({ id, data }: NodeProps)` | AgentNode.tsx | CODE | Media | 1h | → verificar: muestra descripción |
| 3 | ToolNode | `dashboard/components/builder/nodes/ToolNode.tsx` | `function ToolNode({ id, data }: NodeProps)` | AgentNode.tsx | CODE | Baja | 0.5h | → verificar: muestra nombre tool |
| 4 | CrewCanvas | `dashboard/components/builder/CrewCanvas.tsx` | Estado completo con handlers | `BuilderCanvas.tsx` + reactflow docs | CODE | Alta | 2h | → verificar: drag-drop funcional |
| 5 | Export handler | `CrewCanvas.tsx` exportFn | `function exportToBundle(): BundleExport` | `bundle_schemas.py` | BACKEND | Media | 1h | → verificar: JSON válido schema v2 |
| 6 | Run handler | `CrewCanvas.tsx` runFn | `function runCrew(bundle: BundleExport)` | `flows.py` | BACKEND | Media | 1h | → verificar: `POST /flows/` → completed |
| 7 | Integración | `BuilderCanvas.tsx` reemplaza placeholder | Import CrewCanvas | `BuilderCanvas.tsx` actual | FULLSTACK | Baja | 0.5h | → verificar: canvas visible en /builder |

**Tiempo total estimado:** 7 horas

---

## 🔮 Roadmap (NO implementar)

- Optimización: virtualización de nodos para crews grandes
- Mejora: auto-layout con dagre/d3-hierarchy
- Feature: crew templates guardados en localStorage