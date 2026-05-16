# 🗺️ Contexto de Fase — FluxAgentPro-v2

> **Documento fuente de verdad para todos los agentes.** Verificado contra código real.

---

## 1. Resumen de Fase

**Fase activa:** `guiAgentGenerator` — ⏳ **EN PROGRESO** (8/9 pasos completados)
**Objetivo:** Replicar experiencia de creación visual de agentes (Crew Studio) dentro del dashboard FAP, sobre stack propio (Next.js + ReactFlow + FastAPI + Supabase).

### Pasos en orden

| # | Paso | Estado |
|---|------|--------|
| 1 | Crear endpoint `GET /api/tools/available` | ✅ Completado |
| 2 | Crear endpoint `POST /api/bundles/export` | ✅ Completado |
| 3 | Endpoints CRUD para templates de agentes | ✅ Completado |
| 4 | Builder visual — UI con ReactFlow | ✅ Completado |
| 5 | Template Picker — librería de templates | ✅ Completado |
| 6 | Agent Playground — prueba en tiempo real | ✅ Completado |
| 7 | Canvas visual — ensamblaje de crews | ✅ Completado |
| 8 | ExportDialog + flujo completo de exportación | ✅ Completado |
| 9 | Navegación, breadcrumbs e integración | ❌ **RECHAZADO** |

### Dependencias entre pasos
- Paso 2 requiere Paso 1 (tools list para export)
- Paso 4 requiere Pasos 1-3 (tools + export + templates para builder)
- Paso 6 requiere Paso 4 (AgentForm creado con `onRoleChange`) + `POST /agents/{role}/run` existente
- Paso 7 requiere Paso 4 (AgentForm + BuilderLayout) + `GET /agents` + `POST /bundles/export` existentes
- Paso 8 requiere Paso 2 (`POST /api/bundles/export` existente) + Paso 7 (CrewCanvas con `canvasToExportPayload()`) + Paso 4 (AgentForm con campos completos)
- Paso 9 requiere Pasos 4, 7 y 8 (integración de componentes navegación en rutas existentes)

---

## 2. Estado Actual del Proyecto

> Verificado contra código fuente en `src/` y `supabase/migrations/`.

### ✅ Implementado y funcional

| Componente | Archivo | Línea | Notas |
|---|---|---|---|
| Endpoint `GET /api/tools/available` | `src/api/routes/tools.py:46-63` | Handler + modelos Pydantic | Retorna `ToolsListResponse` con `ToolInfo[]` |
| Router registrado en API | `src/api/main.py:31,114` | Import + `include_router` | No en `__init__.py` (corrección D4) |
| ToolRegistry singleton | `src/tools/registry.py:272` | `tool_registry = ToolRegistry()` | `list_tools()` + `get_metadata()` |
| MCPPool singleton | `src/tools/mcp_pool.py:42-56` | `get()` classmethod | Circuit breaker + retry exponential |
| Auth middleware `require_org_id` | `src/api/middleware.py:66` | FastAPI Depends | Extrae `X-Org-ID` header |
| CLI `fap tools list` | `src/cli/commands/tools_list.py:29-64` | Typer sub-app `tools` | `--org-id`, `--source`, `--json` |
| CLI registro `app.add_typer(tools, ...)` | `src/cli/main.py:35,56` | Import + registro | Sub-comando `tools list` |
| Flujo warmup + health checks | `src/api/main.py:48-77` | lifespan handler | warmup_all_active_tenants() + run_health_checks() |
| Tool register decorator | `src/tools/registry.py:276-287` | `@register_tool(...)` | Uso en `src/tools/builtin` |
| MCP server query | `src/tools/mcp_pool.py:122-131` | `get_service_client()` | `.table("org_mcp_servers").select("*")` |
| Endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py:199-210` | Handler + validación goal/backstory | `Depends(require_org_id)` |
| `ExportService` orquestador | `src/services/export_service.py:21-66` | `export(payload) -> tuple[bytes, str]` | Reutiliza `BundleManager.create_bundle()` |
| Modelos export Pydantic | `src/services/bundle_schemas.py:102-116` | `AgentExportItem`, `ExportBundleRequest`, `SkillExportItem` | Validación campo por campo con Pydantic |
| CLI `fap bundle export` | `src/cli/commands/bundle_export.py:34-135` | Typer command `bundle export` | Dogfooding: usa `ExportService` |
| CLI registro `app.add_typer(bundle_app, ...)` | `src/cli/main.py:15,73` | Import + registro `bundle` sub-app | Sub-comando `bundle export` |
| Script helper `bundle_validator.py` | `scripts/bundle_validator.py` | Validar estructura ZIP exportado | Opcional, no bloqueante |
| Tests unitarios export | `tests/unit/test_bundle_export.py` | 7 tests: validación, generación, edge cases | 7/7 pasan |
| Tests integración round-trip | `tests/integration/test_bundle_export_roundtrip.py` | 3 tests: process_zip, mock import, estructura | 3/3 pasan |
| Tabla `agent_templates` | `supabase/migrations/030_agent_templates.sql:10-21` | Global sin `org_id`, RLS SELECT auth, ALL service_role | Índice parcial `UNIQUE(name) WHERE is_system=TRUE` |
| Endpoint `GET /api/templates` | `src/api/routes/templates.py:54-67` | Lista + filtro `?category=` + `count` | Sin `require_org_id` |
| Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | Detalle con `soul_json`, 404 si no existe | `maybe_single()` |
| Modelos Pydantic templates | `src/api/routes/templates.py:25-51` | `TemplateInfo`, `TemplateListResponse`, `TemplateDetailResponse` | Consistente con `tools.py` |
| CLI `fap templates seed` | `src/cli/commands/templates_seed.py:140-220` | Seed 8 system templates + `--dry-run` + `--reset` | Check-then-insert idempotente |
| CLI registro `templates` sub-app | `src/cli/main.py:33,58` | Import + `add_typer(templates_app, name="templates")` | Sub-comando `templates seed` |
| Tests unitarios templates | `tests/unit/test_templates.py` | 7 tests: list, filter, detail, 404, auth, soul_json | 7/7 pasan |
| Endpoint `POST /agents` | `src/api/routes/agents.py:51-92` | `AgentCreate` + `AgentResponse` + upsert logic | `require_org_id` + `TenantClient` (corrección D4 RLS) |
| CLI `fap agent create` | `src/cli/commands/agent_create.py:30-134` | Typer `agent` sub-app | `--role`, `--goal`, `--backstory`, `--tools`, `--dry-run`, `--org-id`, LLM flags |
| CLI registro `agent` sub-app | `src/cli/main.py:14,77` | Import + `add_typer(agent_app, name="agent")` | Sub-comando `agent create` |
| Página `/builder` | `dashboard/app/(app)/builder/page.tsx` | Entry page `'use client'` | Orquesta `BuilderLayout` |
| `BuilderLayout` component | `dashboard/components/builder/BuilderLayout.tsx` | Split 60/40 responsive | `lg:grid-cols-[60%_40%]`, stack vertical mobile |
| `AgentForm` component | `dashboard/components/builder/AgentForm.tsx` | 11 campos: react-hook-form + zodResolver | useQuery `GET /api/tools/available`, `POST /agents` |
| `BuilderCanvas` component | `dashboard/components/builder/BuilderCanvas.tsx` | ReactFlow vacío `dynamic import ssr:false` | Placeholder Paso 07 |
| `ToolMultiSelect` component | `dashboard/components/builder/ToolMultiSelect.tsx` | Checkboxes + búsqueda + badges por source | Custom sin deps extra |
| Sidebar "Builder" entry | `dashboard/components/nav-main.tsx:50` | `{ title: 'Builder', url: '/builder', icon: Wand2 }` | Añadido a `defaultNavItems` |
| Constante `PROVIDER_MODELS` | `dashboard/lib/constants.ts:16-21` | Mapa estático con 4 providers | groq, openai, anthropic, openrouter |
| Deps frontend `reactflow` v11 | `dashboard/package.json` | ReactFlow v11 para builder canvas | No @xyflow/react v12 (rename) |
| Deps frontend `zod` | `dashboard/package.json` | Validación Zod en AgentForm | `@hookform/resolvers` ya instalado (v5.2.2) |
| `TemplatePicker` component | `dashboard/components/builder/TemplatePicker.tsx` | Grid cards + búsqueda + filtro categoría + "Use Template" | useQuery `GET /api/templates`, 4 estados (loading/error/empty/data) |
| `TemplatePicker` integrado en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Dialog modal + botón "Templates" + orquestación template→AgentForm | `mapTemplateToFormValues()` con mapeo defensivo + fallbacks |
| AgentForm: prop `templateData` | `dashboard/components/builder/AgentForm.tsx:53,99-107` | `useEffect` + `reset(templateData)` para aplicar template post-montaje | Sin `forwardRef` (corrección L53) |
| Constante `TEMPLATE_CATEGORIES` | `dashboard/lib/constants.ts:16` | `['Research', 'Development', 'Support', 'General'] as const` | Usada por TemplatePicker para chips de filtro |
| CLI `fap templates use` | `src/cli/commands/templates_use.py` | Crear agente desde template vía CLI | `--org-id`, `--role`, `--goal`, `--backstory`, `--tools`, `--max-iter`, `--dry-run`. Dogfooding: valida mapeo template→agent |
| CLI registro `templates use` | `src/cli/main.py:35,61` | `templates_app.command("use")(use_template)` | Sub-comando `templates use` |
| LoadingSpinner en botón TemplatePicker | `TemplatePicker.tsx:224-225` | `<LoadingSpinner size="sm" />` durante fetch de detalle | Consistente con AgentForm |
| `AgentPlayground` component | `dashboard/components/builder/AgentPlayground.tsx` | Chat panel: POST `/agents/{role}/run` + polling `GET /tasks/{task_id}` | Timeout 120s, `MessageBubble` subcomponent, `formatResult()` polimórfico |
| `MessageBubble` subcomponent | `AgentPlayground.tsx:227-269` | Render user/assistant/error bubbles con tokens badge | Truncate >2000 chars con `Collapsible` |
| Sheet `AgentPlayground` integrado en `BuilderLayout` | `BuilderLayout.tsx:8,51,78-86,118-128` | Botón "Playground" + Sheet `side="right"` `w-full sm:max-w-md` | `disabled={!currentRole}` hasta que AgentForm tenga role |
| `AgentForm.onRoleChange` prop | `AgentForm.tsx:51,116-117` | `watch('role')` + `useEffect` → callback al padre | Dispara cada keystroke (mejora pendiente: debounce) |
| `Task` interface extendida con `tokens_used` | `dashboard/lib/types.ts:8` | `tokens_used: number` + `approval_required?`, `approval_status?`, `approval_payload?` | Corrección D4 del FINAL |
| CLI `fap agent run` | `src/cli/commands/agent_run.py` | Typer command: POST `/agents/{role}/run` + polling `GET /tasks/{task_id}` | `--role`, `--message`, `--org-id`, `--watch`, `--timeout` |
| CLI registro `agent run` | `src/cli/main.py:15,81` | `agent_app.command("run")(run_agent)` | Sub-comando `agent run` |
| Tests unitarios `agent_run` | `tests/unit/test_agent_run.py` | 3 tests: success, role_not_found, connection_error | 3/3 pasan |
| `CrewCanvas` component | `dashboard/components/builder/CrewCanvas.tsx:74` | Canvas ReactFlow v11 con sidebar Agent Palette + Run Results | HTML5 native DnD (sin librería externa), autosave localStorage 30s, 4 templates preset |
| `AgentNode` custom ReactFlow node | `dashboard/components/builder/nodes/AgentNode.tsx:22` | Nodo visual con role + goal truncado + tools badges (max 3) + model label | `memo()` para rendimiento, Tooltip Radix UI para tools completas |
| `TaskNode` custom ReactFlow node | `dashboard/components/builder/nodes/TaskNode.tsx:15` | Nodo visual con description + expectedOutput + assignedAgent badge | `memo()` para rendimiento |
| `canvasToExportPayload()` | `dashboard/lib/canvasUtils.ts:36-44` | Convierte agentNodes → `{ agents: AgentExportItem[] }` para export | Export agents-only (tasks/edges excluidos por limitación bundle-schema-v2) |
| `nodesToSnapshot()` / `snapshotToNodes()` | `dashboard/lib/canvasUtils.ts:46-103` | Serializa/deserializa grafo completo (nodes+edges+metadata) ↔ JSON | `CrewGraph` formato canónico |
| `generateCrewPy()` | `dashboard/lib/crewCodeGen.ts:3-80` | Genera código Python ejecutable (crewai Agent+Task+Crew+Process.sequential) | Vista previa de código en diálogo modal |
| `CREW_TEMPLATES` | `dashboard/lib/crewTemplates.ts:12-167` | 4 templates preset: Research Pipeline, Code Review, Content Creation, Data Analysis | Nodos + edges predefinidos con posiciones |
| `BuilderCanvas` reimplementado | `dashboard/components/builder/BuilderCanvas.tsx` | Wrapper `dynamic(() => import('@/components/builder/CrewCanvas'), { ssr: false })` | Reemplaza placeholder vacío del Paso 04 |
| `BuilderLayout` tabs | `dashboard/components/builder/BuilderLayout.tsx:55,72-83,105-127` | `TabsList` con "Agent Form" y "Crew Canvas" | `@radix-ui/react-tabs` ya instalado |
| Endpoint `POST /workflows` | `src/api/routes/workflows.py:108-147` | Crea `workflow_template` desde definición de canvas | `WorkflowCreate` + `TenantClient` RLS, 409 si flow_type duplicado |
| Endpoint `GET /workflows/` | `src/api/routes/workflows.py:46-66` | Lista workflows activos con filtro `?status=` | `WorkflowSummary` |
| Endpoint `GET /workflows/{flow_type}` | `src/api/routes/workflows.py:69-88` | Obtiene workflow por flow_type | — |
| Endpoint `DELETE /workflows/{flow_type}` | `src/api/routes/workflows.py:91-105` | Soft-delete (is_active=false, status=archived) | — |
| CLI `fap crew save` | `src/cli/commands/crew.py:157-216` | Guarda agentes desde API como crew JSON | `--name`, `--org-id`, `--output` |
| CLI `fap crew load` | `src/cli/commands/crew.py:219-268` | Carga y muestra crew JSON con Rich Table | `--file` |
| CLI `fap crew export` | `src/cli/commands/crew.py:271-341` | Exporta agentes como bundle ZIP vía ExportService | `--name`, `--roles`. Usa `get_service_client()` (service_role) |
| CLI `fap crew validate` | `src/cli/commands/crew.py:344-377` | Valida estructura JSON de crew graph | `_validate_crew_graph()` con detección de ciclos DFS |
| CLI `fap crew scaffold` | `src/cli/commands/crew.py:379-422` | Crea crew desde preset template | `--preset` (4 valores) |
| CLI registro `crew` sub-app | `src/cli/main.py:20,81` | `add_typer(crew_app, name="crew")` | Sub-comandos: save, load, export, validate, scaffold |
| Canvas types | `dashboard/lib/types.ts:254-289` | `CanvasAgentNode`, `CanvasTaskNode`, `CrewGraphNode`, `CrewGraphEdge`, `CrewGraph` | Formato canónico de serialización |
| Deps `reactflow` v11 existente | `dashboard/package.json` | ReactFlow v11 para crew canvas | Sin librería DnD externa (HTML5 native) |
| Tests unitarios canvas serialize | `tests/unit/test_canvas_serialize.py` | 7 tests: payload, code gen (single agent, empty canvas, multi agent+task) | 7/7 pasan (usando `_generate_py()` mirror Python de `generateCrewPy` TypeScript) |
| Tests unitarios crew endpoints | `tests/unit/test_crew_endpoints.py` | 8 tests: list agents, create workflow, duplicate 409, validación crew graph | 8/8 pasan |
| `ExportDialog` component | `dashboard/components/builder/ExportDialog.tsx:1-322` | Diálogo modal unificado para export ZIP desde AgentForm (1 agente) y CrewCanvas (N agentes) | 5 estados: summary/exporting/success/error/empty. Validación `max_length=15`. Warning LLM config + tasks not exported en crew-canvas |
| `fapDownload()` helper | `dashboard/lib/api.ts:54-94` | Descarga binaria (ZIP) autenticada con JWT + X-Org-ID headers | Retorna Response sin parsear para `.blob()`. No modifica `fapFetch` existente |
| `Checkbox` shadcn/ui | `dashboard/components/ui/checkbox.tsx:1-27` | Componente Checkbox con Radix primitives + cva + cn | `@radix-ui/react-checkbox` ya instalado como dep transitiva |
| Tipos export | `dashboard/lib/types.ts:291-307` | `AgentExportItem`, `SkillExportItem`, `ExportBundleRequest` | Tipado fuerte del payload de exportación |
| Botón Export en AgentForm | `dashboard/components/builder/AgentForm.tsx:385-393,203-222` | Botón "Export" junto a Save Agent + `buildSingleAgentPayload()` | Disabled sin role/goal/backstory. Incluye LLM config completa |
| CrewCanvas refactorizado para ExportDialog | `dashboard/components/builder/CrewCanvas.tsx:83,207-235,573-580` | Eliminados `confirmExport()`, `handleCopyJSON()`, Dialog inline. Usa `<ExportDialog>` con `useMemo` para exportPayload + fullGraphJson | `handleSaveCrew` preservado (línea 307) |
| `fap bundle validate-payload` CLI | `src/cli/commands/bundle_validate_payload.py:1-149` | Valida payload JSON contra ExportBundleRequest sin llamar endpoint | `--file`, `--stdin`, `--json`. Output Rich: schema status, agentes, skills, warnings |
| Registro CLI validate-payload | `src/cli/main.py:18,82` | `bundle_app.command("validate-payload")(validate_payload)` | Sub-comando `bundle validate-payload` |
| `BuilderErrorBoundary` component | `dashboard/components/builder/BuilderErrorBoundary.tsx` | Class component para capturar errores de ReactFlow | Aísla fallos del canvas sin romper el layout |
| `BuilderBreadcrumb` component | `dashboard/components/builder/BuilderBreadcrumb.tsx` | Breadcrumbs contextuales para el Builder | Muestra Dashboard > Builder > Agent Form/Crew Canvas |
| Convención Next.js (loading/error) | `dashboard/app/(app)/builder/` | Archivos `loading.tsx` y `error.tsx` | Skeletons y manejo de errores a nivel de ruta |
| `validate_builder_nav.py` script | `scripts/validate_builder_nav.py` | Valida integridad estructural de la navegación | 11 checks automáticos de archivos y dead code |

### ⚠️ Parcialmente implementado

| Componente | Archivo | Problema | Notas |
|---|---|---|---|
| Sincronización Breadcrumb | `BuilderBreadcrumb.tsx` | Prop `activeTab` hardcoded en `page.tsx` | No refleja cambios de pestaña en `BuilderLayout` |

### ✅ Archivado — Paso 1..8
(Ver `DEVS/IMPLEMENTED/guiAgentGenerator/` para histórico completo)

### ✅ Archivado — Paso 9

| Archivos | Destino |
|---|---|
| `analisis-FINAL.md`, `analisis-*.md` (4 análisis), `validacion.md`, `eval_models.html` | `DEVS/IMPLEMENTED/guiAgentGenerator/09-Navegacion-breadcrumbs-e-integracion/` |

### 📝 Correcciones al plan aplicadas

| ID | Corrección | Código |
|---|---|---|
| D1 | `ToolMetadata` sin `category` → derivar de `tags[0]`. NO modificar dataclass. | `tools.py:87` — `meta.tags[0] if meta.tags else "general"` |
| D2 | MCP no tiene `list_all_tools()` → iterar `org_mcp_servers` + `asyncio.gather()` | `tools.py:109-146` |
| D3 | Timeout <500ms irreal con MCP → local <500ms, MCP timeout 5s, degradado graceful | `tools.py:124` — `timeout=5`, catch exceptions |
| D4 | Router en `main.py`, NO en `__init__.py` | `main.py:31,114` |
| D5 | `list_tools()` retorna solo nombres → `get_metadata()` por cada uno | `tools.py:75-78` |

#### Paso 09 — Navegación, breadcrumbs e integración

| ID | Corrección | Código |
|---|---|---|
| D1 | Eliminar `navMain` dead code en `app-sidebar.tsx` | `app-sidebar.tsx` — array local eliminado. |
| D2 | Breadcrumbs basados en tabs (sin sub-rutas físicas) | `BuilderBreadcrumb.tsx` — recibe `activeTab` prop. |
| D3 | SSOT Navigation usando `defaultNavItems` | `nav-main.tsx` — centraliza la navegación. |

---

## 3. Contratos Técnicos Vigentes

### Stack detectado
- **Backend:** Python ≥3.12 + FastAPI (Pydantic v2)
- **Frontend:** TypeScript + Next.js (`dashboard/`)
- **DB:** Supabase (PostgreSQL) vía `supabase` Python client
- **Auth:** PyJWT (ES256/HS256 via JWKS middleware)
- **Package manager:** `uv` (backend), `npm` (frontend)

### Modelos de datos (de migraciones reales)
- `organizations(id UUID, name TEXT, created_at TIMESTAMPTZ)`
- `org_members(id UUID, org_id UUID REFERENCES organizations, user_id UUID, role TEXT)`
- `agent_catalog(id UUID, org_id UUID, role TEXT, goal TEXT, backstory TEXT, ...)` — con RLS tenant_isolation
- `org_mcp_servers(id UUID, org_id UUID, name TEXT, command TEXT, args JSONB, secret_name TEXT, is_active BOOLEAN)`
- `skill_catalog(id UUID, org_id UUID, name TEXT, code_source TEXT, ...)`
- `agent_templates(id UUID, name TEXT NOT NULL, description TEXT, category TEXT NOT NULL, soul_json JSONB, suggested_tools TEXT[], max_iter INTEGER, is_system BOOLEAN, ...)`

### Endpoints / APIs (rutas reales)
| Ruta | Archivo | Método | Auth |
|---|---|---|---|
| `/api/tools/available` | `src/api/routes/tools.py` | GET | `require_org_id` |
| `/api/templates` | `src/api/routes/templates.py` | GET | None |
| `/api/bundles/export` | `src/api/routes/bundles.py` | POST | `require_org_id` |
| `/agents` | `src/api/routes/agents.py` | POST | `require_org_id` |
| `/workflows` | `src/api/routes/workflows.py` | POST | `require_org_id` |

### Patrones de código en uso

**1. Patrón Error Boundary (Frontend)**
```tsx
// dashboard/components/builder/BuilderErrorBoundary.tsx
export class BuilderErrorBoundary extends Component<Props, State> {
  // Captura errores de renderizado en ReactFlow
}
```
Aísla el canvas de ReactFlow para que fallos en la librería no rompan toda la página del builder.

**2. Patrón Convention Files (Next.js)**
```
dashboard/app/(app)/builder/
├── loading.tsx  // Skeleton state
└── error.tsx    // Route level error boundary
```

**3. Patrón SSOT Navigation**
```tsx
// dashboard/components/nav-main.tsx
export const defaultNavItems: NavItem[] = [...]
```

---

## 4. Decisiones de Arquitectura Tomadas

| Decisión | Detalle | Verificación |
|---|---|---|
| Breadcrumbs Reactivos | Sincronizados con el estado de las pestañas (`Tabs`), no con rutas físicas. | `BuilderBreadcrumb.tsx` |
| Error Boundary de Clase | Necesario ya que los componentes funcionales no soportan `componentDidCatch`. | `BuilderErrorBoundary.tsx` |
| Dogfooding Tooling | El implementador debe usar `validate_builder_nav.py` para verificar integridad. | `scripts/validate_builder_nav.py` |

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Decisiones Tomadas | Notas |
|---|---|---|---|---|---|
| 01..08 | ✅ Completados | (Ver histórico) | (Ver histórico) | (Ver histórico) | — |
| 09-Navegacion-breadcrumbs-integracion | ❌ **RECHAZADO** | `DEVS/IMPLEMENTED/guiAgentGenerator/09-Navegacion-breadcrumbs-e-integracion/` | `57a75de` | Breadcrumbs estáticos, dead code eliminado | Rechazado por fallo en sincronización de tabs con breadcrumb. |

---

## 6. Criterios Generales de Aceptación MVP

- ✅ Happy path funciona end-to-end
- ✅ Errores manejados sin crash
- ✅ Datos persistidos correctamente
- ✅ Código ejecuta sin errores de compilación
- ✅ **Herramienta DX:** `scripts/validate_builder_nav.py` valida 11 puntos de integridad estructural.
- ❌ **PENDIENTE:** Sincronización dinámica de Breadcrumbs con el estado de las tabs.
