# Análisis Paso 7 — hy3 (Caveman Ultra)

## §0 Verif Código

| # | Elemento | Verif | Estado | Evidencia |
|---|---|---|---|---|
| 1 | AgentNode.tsx (crear) | ls nodes/ | ✅ No existe | glob no match |
| 2 | TaskNode.tsx (crear) | ls nodes/ | ✅ No existe | glob no match |
| 3 | ToolNode.tsx (crear) | ls nodes/ | ✅ No existe | glob no match |
| 4 | CrewCanvas.tsx (crear) | ls builder/ | ✅ No existe | BuilderCanvas sí, Crew no |
| 5 | reactflow dep | cat package.json | ✅ v11.11.4 | dashboard/package.json:41 |
| 6 | POST /flows/{ft}/run | cat flows.py | ✅ Existe | flows.py:142 |
| 7 | BuilderLayout.tsx | ls builder/ | ✅ Existe | glob match |
| 8 | BuilderCanvas (placeholder) | cat BuilderCanvas.tsx | ✅ Step07 placeholder | line39 |
| 9 | bundle-schema-v2.md | ls docs/ | ✅ Existe | docs/ |
| 10 | flow_registry | cat registry.py | ✅ Singleton | registry.py:370 |
| 11 | ReactFlow dynamic import | cat BuilderCanvas.tsx | ✅ SSR off | line6 |
| 12 | reactflow CSS | cat BuilderCanvas.tsx | ✅ Import line32 | line32 |
| 13 | RunFlowRequest | cat flows.py | ✅ input_data dict | line55 |
| 14 | Discrepancia: Run Crew → 1 flow_type | plan vs flows.py | ❌ Crew multi-agent, endpoint 1 flow_type | plan:168 vs flows.py:142 |
| 15 | Discrepancia: Vista previa Python | plan vs codebase | ❌ No generador código | plan:166 vs grep no match |
| 16 | Discrepancia: Export JSON | plan vs bundle-schema | ✅ Compatible | bundle-schema:62-179 |

### Discrepancies
1. Run Crew → flow_type. Crew multi-agent, endpoint 1 flow_type. → Definir flow_type "crew_run" acepte agents[] + tasks[] en input_data.
2. Vista previa Python. No existe. → Añadir tarea crear fn grafo → Python CrewAI code.
3. Export JSON → bundle-schema. Compatible.

---

## §1 Datos (ETAPA 1)
Step7 frontend solo. No tablas, no migraciones. ✅ 0 data changes.

---

## §2 Code (ETAPA 2)
- Nuevos: AgentNode.tsx, TaskNode.tsx, ToolNode.tsx, CrewCanvas.tsx.
- Patrón ref: BuilderCanvas.tsx (ReactFlow init), BuilderLayout.tsx (shadcn/ui + lucide).
- Interfaces:
  - AgentNodeProps: { data: { role: str, tools: str[] }, selected: bool }
  - TaskNodeProps: { data: { desc: str, expectedOut: str }, selected: bool }
  - ToolNodeProps: { data: { name: str, desc: str }, selected: bool }
  - CrewCanvasProps: { agents: AgentFormData[], tasks: TaskData[], onExport: (json) => void, onRun: (input) => void }
- Mod: BuilderLayout.tsx → import CrewCanvas en lugar de BuilderCanvas.

---

## §3 Backend (ETAPA 3)
- Endpoint usado: POST /flows/{ft}/run ✅.
- Falta: flow_type "crew_run" para multi-agent. → Crear crew_run flow en src/flows/crew_run.py.
- Flujo: CrewCanvas → JSON → input_data.agents[] + input_data.tasks[] → POST /flows/crew_run/run.
- Error: 404 flow no existe, 400 input inválido.

---

## §4 Fullstack+DX (ETAPA 4)
- Flujo: Drag nodes → connect → export JSON → run crew → result.
- Gap: export JSON val, Python preview, crew_run flow.
- **DX Tool: `create-flow-node` script**
  - Automatiza: crear node component (handles, props, styling).
  - Tipo: CLI script.
  - Uso: `python scripts/create_flow_node.py --type agent`
  - Impacto: 0 boilerplate node code.
  - Prioridad: Tarea 0.

---

## §5 Criterios Aceptación
- [DATA] ✅ No DB changes.
- [CODE] ✅ AgentNode.tsx existe con props correctas.
- [CODE] ✅ TaskNode.tsx existe con props correctas.
- [CODE] ✅ ToolNode.tsx existe con props correctas.
- [CODE] ✅ CrewCanvas.tsx existe con sidebar, drop, edges.
- [BACKEND] ✅ POST /flows/crew_run/run acepta crew input.
- [FULLSTACK] ✅ Drag & drop nodes funciona.
- [FULLSTACK] ✅ Export JSON compatible bundle-schema-v2.
- [FULLSTACK] ✅ Vista previa Python generada.
- [DX] ✅ `create-flow-node` script ejecuta sin errores.

---

## §6 Riesgos
| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ReactFlow performance | Media | Muchos nodes/connections | Usar `onlyRenderVisibleElements` prop |
| Export JSON inválido | Alta | Grafo mal formado | Validar contra bundle-schema-v2 antes export |
| Crew run falla | Alta | Multi-agent no soportado | Crear crew_run flow dedicado |
| SSR ReactFlow | Media | Next.js SSR | Dynamic import con `ssr:false` (ya usado) |
| Python preview no coincide | Media | Plantilla desactualizada | Usar bundle-schema-v2 como fuente de verdad |

---

## §7 Plan Implementación (Atomic Tasks)
| # | Tarea | Artefacto | Interfaz Exacta | Patrón Ref | Etapa | Complejidad | Tiempo | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX: create-flow-node script | scripts/create_flow_node.py | `def main(type: str, name: str) -> None` | scripts/seed_system_bundles.py | DX | Media | 1h | Ninguna | → `python scripts/create_flow_node.py --help` ok |
| 1 | Crear AgentNode.tsx | dashboard/components/builder/nodes/AgentNode.tsx | Props: { data: { role: str, tools: str[] }, selected: bool } | BuilderCanvas.tsx | CODE | Baja | 0.5h | Tarea 0 | → importable, renderiza sin error |
| 2 | Crear TaskNode.tsx | dashboard/components/builder/nodes/TaskNode.tsx | Props: { data: { desc: str, expectedOut: str }, selected: bool } | AgentNode.tsx | CODE | Baja | 0.5h | Tarea 0 | → importable, renderiza |
| 3 | Crear ToolNode.tsx | dashboard/components/builder/nodes/ToolNode.tsx | Props: { data: { name: str, desc: str }, selected: bool } | AgentNode.tsx | CODE | Baja | 0.5h | Tarea 0 | → importable, renderiza |
| 4 | Crear CrewCanvas.tsx | dashboard/components/builder/CrewCanvas.tsx | Props: { agents: AgentFormData[], tasks: TaskData[], onExport: (json) => void, onRun: (input) => void } | BuilderCanvas.tsx | CODE | Alta | 2h | Tareas 1-3 | → drag nodes, connect edges ok |
| 5 | Modificar BuilderLayout.tsx | dashboard/components/builder/BuilderLayout.tsx | Import CrewCanvas en lugar de BuilderCanvas | BuilderLayout.tsx actual | CODE | Baja | 0.5h | Tarea 4 | → /builder carga CrewCanvas |
| 6 | Crear crew_run flow | src/flows/crew_run.py | `class CrewRunFlow(BaseFlow):` + metadata category="crew" | src/flows/example_flow.py | BACKEND | Media | 1h | Ninguna | → POST /flows/crew_run/run acepta input |
| 7 | Implementar export JSON fn | dashboard/lib/exportCrew.ts | `export function exportCrewToJSON(nodes: Node[], edges: Edge[]) -> BundleSchema` | bundle-schema-v2.md | FULLSTACK | Media | 1h | Tarea 4 | → export JSON valida contra schema |
| 8 | Implementar Python preview fn | dashboard/lib/genPythonCrew.ts | `export function genPythonCrew(nodes: Node[], edges: Edge[]) -> string` | bundle-schema-v2.md flows | FULLSTACK | Media | 1h | Tarea 7 | → preview muestra código Python |
| 9 | Integrar Run Crew button | CrewCanvas.tsx | Llama POST /flows/crew_run/run con input_data | flows.py run_flow | FULLSTACK | Baja | 0.5h | Tarea 6 | → click Run ejecuta flow |

**Tiempo total: 8h**
